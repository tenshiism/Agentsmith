import ctypes
import ctypes.wintypes
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import mss
from mss.exception import ScreenShotError
import numpy as np
from PIL import Image

from .base import GameAdapter, GameState

_VBA_KEY_MAP = {
    "a": 0x5A,
    "b": 0x58,
    "start": 0x0D,
    "select": 0x08,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}

_GB_RAM_RANGES = [
    (0xC000, 0xCFFF),
    (0xFF00, 0xFF7F),
]

def _send_key(vk: int, press: bool):
    ctypes.windll.user32.keybd_event(vk, 0, 0 if press else 2, 0)


class VBAAdapter(GameAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._hwnd: Optional[int] = None
        self._action_names = ["a", "b", "up", "down", "left", "right", "start", "select"]
        self._last_error_time = 0.0
        self._held_vkeys: set[int] = set()

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

    def set_rom_path(self, path: str) -> None:
        raw = path
        rom_path = Path(raw)
        if not rom_path.is_absolute():
            rom_path = Path(__file__).resolve().parent.parent.parent / rom_path
        resolved = str(rom_path)
        if not Path(resolved).exists():
            raise FileNotFoundError(f"ROM not found: {resolved}")
        self._rom_path = resolved

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
        for vk in self._held_vkeys:
            _send_key(vk, False)
        self._held_vkeys.clear()
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
        max_area = 0
        rom_name = Path(self._rom_path).stem

        def enum_callback(hwnd, _):
            nonlocal target, max_area
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "VisualBoyAdvance" in title or rom_name in title:
                    rect = ctypes.wintypes.RECT()
                    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
                    area = (rect.right - rect.left) * (rect.bottom - rect.top)
                    if area > max_area:
                        max_area = area
                        target = hwnd
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return target

    def _send_input(self, action: list[int]) -> None:
        if not self._hwnd:
            return

        wanted: set[int] = set()
        for i, pressed in enumerate(action):
            if i >= len(self._action_names):
                break
            if pressed:
                name = self._action_names[i]
                vkey = _VBA_KEY_MAP.get(name)
                if vkey is not None:
                    wanted.add(vkey)

        keys_to_press = wanted - self._held_vkeys
        keys_to_release = self._held_vkeys - wanted
        if not keys_to_press and not keys_to_release:
            return

        for vk in keys_to_press:
            _send_key(vk, True)
        for vk in keys_to_release:
            _send_key(vk, False)

        self._held_vkeys = wanted

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
