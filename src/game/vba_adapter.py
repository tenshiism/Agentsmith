import ctypes
import ctypes.wintypes
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from collections import defaultdict

import mss
from mss.exception import ScreenShotError
import numpy as np
from PIL import Image

from .base import GameAdapter, GameState

_VBA_KEY_MAP = {
    "a": 0x4C,
    "b": 0x4B,
    "start": 0x0D,
    "select": 0x0F,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}

_GB_RAM_RANGES = [
    (0xC000, 0xCFFF),
    (0xFF00, 0xFF7F),
]


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

def _post_key(hwnd: int, vkey: int, key_up: bool):
    ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP if key_up else WM_KEYDOWN, vkey, 0)


class VBAAdapter(GameAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._hwnd: Optional[int] = None
        self._action_names = ["a", "b", "up", "down", "left", "right", "start", "select"]
        self._last_error_time = 0.0

        vba_path = config.get("game", {}).get("vba_path")
        if vba_path:
            self._vba_exe = Path(vba_path)
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            candidates = [
                project_root / "roms" / "GBA" / "VisualBoyAdvance.exe",
            ]
            for c in candidates:
                if c.exists():
                    self._vba_exe = c
                    break
            else:
                raise FileNotFoundError(
                    "VisualBoyAdvance.exe not found. Set game.vba_path in config."
                )

        raw_rom = config["game"]["rom_path"]
        rom_path = Path(raw_rom)
        if not rom_path.is_absolute():
            rom_path = Path(__file__).resolve().parent.parent.parent / rom_path
        self._rom_path = str(rom_path)
        if not Path(self._rom_path).exists():
            raise FileNotFoundError(f"ROM not found: {self._rom_path}")

    def load_rom(self, path: str = "") -> None:
        rom = path or self._rom_path
        self._process = subprocess.Popen(
            [str(self._vba_exe), rom],
        )
        time.sleep(1.5)
        self._hwnd = self._find_vba_window()
        if not self._hwnd:
            raise RuntimeError("Could not find VBA window")
        self._rom_loaded = True

    def reset(self) -> GameState:
        if self._process:
            self.close()
        self.load_rom()
        return self._capture_state()

    def step(self, action: list[int]) -> None:
        self._send_input(action)
        time.sleep(0.05)

    def capture_state(self) -> GameState:
        return self._capture_state()

    def get_available_actions(self) -> list[list[int]]:
        n = len(self._action_names)
        actions = []
        for i in range(n + 1):
            vec = [0] * n
            if i > 0:
                vec[i - 1] = 1
            actions.append(vec)
        return actions

    def get_action_names(self) -> list[str]:
        return self._action_names

    def close(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
            self._hwnd = None

    def _find_vba_window(self) -> Optional[int]:
        target = None
        rom_name = Path(self._rom_path).stem

        def enum_callback(hwnd, _):
            nonlocal target
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "VisualBoyAdvance" in title or rom_name in title:
                    target = hwnd
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return target

    def _send_input(self, action: list[int]) -> None:
        if not self._hwnd:
            return

        for i, pressed in enumerate(action):
            if i >= len(self._action_names):
                break
            name = self._action_names[i]
            vkey = _VBA_KEY_MAP.get(name)
            if vkey is None:
                continue

            _post_key(self._hwnd, vkey, key_up=not pressed)

    def _capture_state(self) -> GameState:
        screenshot = self._capture_screenshot()
        ram = self._read_ram()
        return GameState(screenshot=screenshot, ram=ram, done=False, reward=0.0)

    def _capture_screenshot(self) -> Image.Image:
        if not self._hwnd:
            return Image.new("RGB", (160, 144))

        for attempt in range(5):
            client_rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetClientRect(self._hwnd, ctypes.byref(client_rect))
            pt = ctypes.wintypes.POINT(client_rect.left, client_rect.top)
            ctypes.windll.user32.ClientToScreen(self._hwnd, ctypes.byref(pt))

            width = client_rect.right - client_rect.left
            height = client_rect.bottom - client_rect.top
            if width > 0 and height > 0:
                break
            time.sleep(0.2)
        else:
            return Image.new("RGB", (160, 144))

        try:
            with mss.mss() as sct:
                monitor = {"top": pt.y, "left": pt.x, "width": width, "height": height}
                img_data = sct.grab(monitor)
                img = Image.frombytes("RGB", img_data.size, img_data.bgra, "raw", "BGRX")
        except ScreenShotError as e:
            now = time.time()
            if now - self._last_error_time > 10.0:
                print(f"[VBA] Screenshot capture failed: {e}")
                self._last_error_time = now
            return Image.new("RGB", (160, 144))

        return img

    def _read_ram(self) -> dict:
        if not self._process or not self._process.pid:
            return {}

        pid = self._process.pid
        handle = ctypes.windll.kernel32.OpenProcess(0x0010, False, pid)
        if not handle:
            return {}

        ram = {}
        buf = ctypes.create_string_buffer(256)
        bytes_read = ctypes.c_size_t(0)

        for start, end in _GB_RAM_RANGES:
            size = end - start + 1
            if ctypes.windll.kernel32.ReadProcessMemory(handle, start, buf, size, ctypes.byref(bytes_read)):
                for offset in range(min(int(bytes_read.value), size)):
                    addr = start + offset
                    ram[f"0x{addr:04X}"] = buf[offset]

        ctypes.windll.kernel32.CloseHandle(handle)
        return ram
