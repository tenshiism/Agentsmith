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


_VBA_SCAN_MAP = {
    "a": 0x2C,       # Z (DirectInput DIK_Z)
    "b": 0x2D,       # X (DIK_X)
    "start": 0x1C,   # Enter (DIK_RETURN)
    "select": 0x0E,  # Backspace (DIK_BACK)
    "up": 0xC8,      # Up arrow (DIK_UP, extended)
    "down": 0xD0,    # Down arrow (DIK_DOWN, extended)
    "left": 0xCB,    # Left arrow (DIK_LEFT, extended)
    "right": 0xCD,   # Right arrow (DIK_RIGHT, extended)
}

_EXTENDED_SCAN_CODES = {0xC8, 0xD0, 0xCB, 0xCD}

_GB_RAM_RANGES = [
    (0xC000, 0xCFFF),
    (0xFF00, 0xFF7F),
]


PUL = ctypes.POINTER(ctypes.c_ulong)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', ctypes.c_ushort),
        ('wScan', ctypes.c_ushort),
        ('dwFlags', ctypes.c_ulong),
        ('time', ctypes.c_ulong),
        ('dwExtraInfo', PUL),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', ctypes.c_long),
        ('dy', ctypes.c_long),
        ('mouseData', ctypes.c_ulong),
        ('dwFlags', ctypes.c_ulong),
        ('time', ctypes.c_ulong),
        ('dwExtraInfo', PUL),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', ctypes.c_ulong),
        ('wParamL', ctypes.c_short),
        ('wParamH', ctypes.c_ushort),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ('ki', _KEYBDINPUT),
        ('mi', _MOUSEINPUT),
        ('hi', _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ('type', ctypes.c_ulong),
        ('ii', _INPUT_UNION),
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_SendInput = _user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]
_SendInput.restype = ctypes.c_uint

_last_send_error = 0.0
_last_error_time = 0.0


def _send_key(code: int, press: bool, extended: bool = False) -> bool:
    extra = ctypes.c_ulong(0)
    flags = KEYEVENTF_SCANCODE
    if not press:
        flags |= KEYEVENTF_KEYUP
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    ii = _INPUT_UNION()
    ii.ki = _KEYBDINPUT(0, code, flags, 0, ctypes.pointer(extra))
    inp = _INPUT(INPUT_KEYBOARD, ii)
    return _SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) == 1


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
        for code in self._held_vkeys:
            _send_key(code, False, code in _EXTENDED_SCAN_CODES)
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
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "VisualBoyAdvance" in title or rom_name in title:
                    rect = ctypes.wintypes.RECT()
                    _user32.GetClientRect(hwnd, ctypes.byref(rect))
                    area = (rect.right - rect.left) * (rect.bottom - rect.top)
                    if area > max_area:
                        max_area = area
                        target = hwnd
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        _user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return target

    def _ensure_hwnd(self) -> bool:
        if self._hwnd and _user32.IsWindow(self._hwnd):
            return True
        self._hwnd = self._find_vba_window()
        return self._hwnd is not None

    def _activate_vba_window(self) -> bool:
        if not self._ensure_hwnd():
            return False
        hwnd = self._hwnd
        fore = _user32.GetForegroundWindow()
        if fore == hwnd:
            return True
        fore_tid = _user32.GetWindowThreadProcessId(fore, None)
        current_tid = _kernel32.GetCurrentThreadId()
        attached = False
        if fore_tid and current_tid != fore_tid:
            attached = _user32.AttachThreadInput(current_tid, fore_tid, True)
        _user32.ShowWindow(hwnd, 9)
        result = _user32.SetForegroundWindow(hwnd)
        _user32.BringWindowToTop(hwnd)
        if attached:
            _user32.AttachThreadInput(current_tid, fore_tid, False)
        time.sleep(0.03)
        return bool(result)

    def _send_input(self, action: list[int]) -> None:
        if not self._ensure_hwnd():
            return

        wanted: set[int] = set()
        for i, pressed in enumerate(action):
            if i >= len(self._action_names):
                break
            if pressed:
                name = self._action_names[i]
                scan = _VBA_SCAN_MAP.get(name)
                if scan is not None:
                    wanted.add(scan)

        keys_to_press = wanted - self._held_vkeys
        keys_to_release = self._held_vkeys - wanted
        if not keys_to_press and not keys_to_release:
            return

        self._activate_vba_window()

        for code in keys_to_press:
            _send_key(code, True, code in _EXTENDED_SCAN_CODES)
        for code in keys_to_release:
            _send_key(code, False, code in _EXTENDED_SCAN_CODES)

        self._held_vkeys = wanted

        if wanted:
            time.sleep(0.05)
            for code in wanted:
                _send_key(code, False, code in _EXTENDED_SCAN_CODES)
            self._held_vkeys = set()

    def _capture_state(self) -> GameState:
        screenshot = self._capture_screenshot()
        ram = self._read_ram()
        return GameState(screenshot=screenshot, ram=ram, done=False, reward=0.0)

    def _capture_screenshot(self) -> Image.Image:
        if not self._hwnd:
            return Image.new("RGB", (160, 144))

        for attempt in range(5):
            client_rect = ctypes.wintypes.RECT()
            _user32.GetClientRect(self._hwnd, ctypes.byref(client_rect))
            pt = ctypes.wintypes.POINT(client_rect.left, client_rect.top)
            _user32.ClientToScreen(self._hwnd, ctypes.byref(pt))

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
        handle = _kernel32.OpenProcess(0x0010, False, pid)
        if not handle:
            return {}

        ram = {}
        buf = ctypes.create_string_buffer(256)
        bytes_read = ctypes.c_size_t(0)

        for start, end in _GB_RAM_RANGES:
            size = end - start + 1
            if _kernel32.ReadProcessMemory(handle, start, buf, size, ctypes.byref(bytes_read)):
                for offset in range(min(int(bytes_read.value), size)):
                    addr = start + offset
                    ram[f"0x{addr:04X}"] = buf[offset]

        _kernel32.CloseHandle(handle)
        return ram
