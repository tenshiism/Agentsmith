from pathlib import Path

try:
    from pyboy import PyBoy
    from pyboy.utils import WindowEvent
except ImportError:
    PyBoy = None
    WindowEvent = None

from PIL import Image
from .base import GameAdapter, GameState


_BUTTON_MAP = {
    "a": WindowEvent.PRESS_BUTTON_A,
    "b": WindowEvent.PRESS_BUTTON_B,
    "up": WindowEvent.PRESS_ARROW_UP,
    "down": WindowEvent.PRESS_ARROW_DOWN,
    "left": WindowEvent.PRESS_ARROW_LEFT,
    "right": WindowEvent.PRESS_ARROW_RIGHT,
    "start": WindowEvent.PRESS_BUTTON_START,
    "select": WindowEvent.PRESS_BUTTON_SELECT,
}

_RELEASE_MAP = {
    "a": WindowEvent.RELEASE_BUTTON_A,
    "b": WindowEvent.RELEASE_BUTTON_B,
    "up": WindowEvent.RELEASE_ARROW_UP,
    "down": WindowEvent.RELEASE_ARROW_DOWN,
    "left": WindowEvent.RELEASE_ARROW_LEFT,
    "right": WindowEvent.RELEASE_ARROW_RIGHT,
    "start": WindowEvent.RELEASE_BUTTON_START,
    "select": WindowEvent.RELEASE_BUTTON_SELECT,
}


class PyBoyAdapter(GameAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        if PyBoy is None:
            raise ImportError("pyboy is not installed. Run: pip install pyboy")
        self._boy: PyBoy | None = None
        self._action_names = ["a", "b", "up", "down", "left", "right", "start", "select"]

    def load_rom(self, path: str) -> None:
        rom_path = Path(path)
        if not rom_path.exists():
            raise FileNotFoundError(f"ROM not found: {rom_path}")
        speed = self.config.get("game", {}).get("speed", 1.0)
        self._boy = PyBoy(str(rom_path), window="null", game_wrapper=True)
        self._boy.set_emulation_speed(speed)
        self._rom_loaded = True

    def reset(self) -> GameState:
        if not self._rom_loaded:
            self.load_rom(self.config["game"]["rom_path"])
        self._boy.stop(save=False)
        self._boy = None
        self.load_rom(self.config["game"]["rom_path"])
        self._boy.tick()
        return self._capture_state()

    def step(self, action: list[int]) -> GameState:
        for i, pressed in enumerate(action):
            if pressed and i < len(self._action_names):
                name = self._action_names[i]
                self._boy.send_input(_BUTTON_MAP[name])
            elif i < len(self._action_names):
                name = self._action_names[i]
                self._boy.send_input(_RELEASE_MAP[name])
        self._boy.tick()
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
        if self._boy:
            self._boy.stop(save=False)

    def _capture_state(self) -> GameState:
        screen = self._boy.screen_image()
        ram = {}
        try:
            for addr in range(0xFF00, 0xFF80):
                ram[f"0x{addr:04X}"] = self._boy.get_memory_value(addr)
        except Exception:
            pass
        return GameState(screenshot=screen, ram=ram, done=False)
