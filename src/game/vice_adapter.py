import ctypes
import ctypes.wintypes
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import mss
from mss.exception import ScreenShotError
from PIL import Image

from .base import GameAdapter, GameState


_VICE_KEY_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "delete": 0x08,
    "backspace": 0x08,
    "space": 0x20,
    "arrow_up": 0x26,
    "arrow_down": 0x28,
    "arrow_left": 0x25,
    "arrow_right": 0x27,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
}

_CHAR_TO_VK = {}
for c in "abcdefghijklmnopqrstuvwxyz0123456789.,!?;:'-":
    if c.isalpha():
        _CHAR_TO_VK[c] = ord(c.upper())
    elif c.isdigit():
        _CHAR_TO_VK[c] = ord(c)
    elif c == '.':
        _CHAR_TO_VK[c] = 0xBE
    elif c == ',':
        _CHAR_TO_VK[c] = 0xBC
    elif c == '!':
        _CHAR_TO_VK[c] = 0x31
    elif c == '?':
        _CHAR_TO_VK[c] = 0xBF

_COMMON_ACTIONS = [
    "go north",
    "go south",
    "go east",
    "go west",
    "look",
    "inventory",
    "examine",
    "take",
    "use",
    "open",
    "close",
    "talk",
    "wait",
    "help",
]


def _send_key(vk: int, press: bool):
    ctypes.windll.user32.keybd_event(vk, 0, 0 if press else 2, 0)


class ViceAdapter(GameAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._hwnd: Optional[int] = None
        self._last_error_time = 0.0
        self._held_vkeys: set[int] = set()

        vice_path = config.get("game", {}).get("vice_path")
        if vice_path:
            self._vice_exe = Path(vice_path)
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            candidates = [
                project_root / "roms" / "VICE" / "bin" / "x64sc.exe",
            ]
            for c in candidates:
                if c.exists():
                    self._vice_exe = c
                    break
            else:
                raise FileNotFoundError(
                    "x64sc.exe not found. Set game.vice_path in config."
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
            [str(self._vice_exe), "-autostart", rom],
        )
        time.sleep(3.0)
        self._hwnd = self._find_vice_window()
        if not self._hwnd:
            raise RuntimeError("Could not find VICE window")
        self._rom_loaded = True

    def reset(self) -> GameState:
        if self._process:
            self.close()
        self.load_rom()
        return self._capture_state()

    def step(self, action: list[int]) -> None:
        self._send_action_input(action)
        time.sleep(0.05)

    def type_text(self, text: str) -> None:
        if not self._ensure_hwnd():
            return
        self._activate_vice_window()
        for ch in text.lower():
            vk = _CHAR_TO_VK.get(ch)
            if vk is not None:
                _send_key(vk, True)
                _send_key(vk, False)
                time.sleep(0.02)
        _send_key(_VICE_KEY_MAP["enter"], True)
        _send_key(_VICE_KEY_MAP["enter"], False)
        time.sleep(0.1)

    def capture_state(self) -> GameState:
        return self._capture_state()

    def get_available_actions(self) -> list[list[int]]:
        n = len(_COMMON_ACTIONS)
        actions = []
        for i in range(n + 1):
            vec = [0] * n
            if i > 0:
                vec[i - 1] = 1
            actions.append(vec)
        return actions

    def get_action_names(self) -> list[str]:
        return list(_COMMON_ACTIONS)

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

    def _find_vice_window(self) -> Optional[int]:
        target = None
        max_area = 0

        def enum_callback(hwnd, _):
            nonlocal target, max_area
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "VICE" in title or "x64sc" in title or "C64" in title:
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

    def _ensure_hwnd(self) -> bool:
        if self._hwnd and ctypes.windll.user32.IsWindow(self._hwnd):
            return True
        self._hwnd = self._find_vice_window()
        return self._hwnd is not None

    def _activate_vice_window(self) -> bool:
        if not self._ensure_hwnd():
            return False
        hwnd = self._hwnd
        fore = ctypes.windll.user32.GetForegroundWindow()
        if fore == hwnd:
            return True
        fore_tid = ctypes.windll.user32.GetWindowThreadProcessId(fore, None)
        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = False
        if fore_tid and current_tid != fore_tid:
            attached = ctypes.windll.user32.AttachThreadInput(current_tid, fore_tid, True)
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        result = ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        if attached:
            ctypes.windll.user32.AttachThreadInput(current_tid, fore_tid, False)
        time.sleep(0.03)
        return bool(result)

    def _send_action_input(self, action: list[int]) -> None:
        if not self._ensure_hwnd():
            return

        idx = -1
        for i, pressed in enumerate(action):
            if pressed:
                idx = i
                break

        if idx < 0 or idx >= len(_COMMON_ACTIONS):
            return

        cmd = _COMMON_ACTIONS[idx]
        self.type_text(cmd)

    def _capture_state(self) -> GameState:
        screenshot = self._capture_screenshot()
        return GameState(screenshot=screenshot, ram={}, done=False, reward=0.0)

    def _capture_screenshot(self) -> Image.Image:
        if not self._hwnd:
            return Image.new("RGB", (640, 400))

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
            return Image.new("RGB", (640, 400))

        try:
            with mss.mss() as sct:
                monitor = {"top": pt.y, "left": pt.x, "width": width, "height": height}
                img_data = sct.grab(monitor)
                img = Image.frombytes("RGB", img_data.size, img_data.bgra, "raw", "BGRX")
        except ScreenShotError as e:
            now = time.time()
            if now - self._last_error_time > 10.0:
                print(f"[VICE] Screenshot capture failed: {e}")
                self._last_error_time = now
            return Image.new("RGB", (640, 400))

        return img
