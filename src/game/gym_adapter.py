from pathlib import Path
from typing import Optional

try:
    import retro
except ImportError:
    retro = None

from PIL import Image
from .base import GameAdapter, GameState


class GymRetroAdapter(GameAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        if retro is None:
            raise ImportError("gym-retro is not installed. Run: pip install gym-retro")
        self._env: Optional[retro.RetroEnv] = None

    def load_rom(self, path: str) -> None:
        game_cfg = self.config["game"]
        game_name = game_cfg.get("rom_path") or game_cfg.get("rom_name", path)
        self._env = retro.make(game=game_name)
        self._rom_loaded = True

    def reset(self) -> GameState:
        if not self._env:
            self.load_rom("")
        obs = self._env.reset()
        return self._make_state(obs, {}, 0.0, False)

    def step(self, action: list[int]) -> GameState:
        obs, reward, done, info = self._env.step(action)
        return self._make_state(obs, info, reward, done)

    def get_available_actions(self) -> list[list[int]]:
        return list(self._env.action_space)

    def get_action_names(self) -> list[str]:
        return list(self._env.buttons)

    def close(self) -> None:
        if self._env:
            self._env.close()

    def _make_state(self, obs, info: dict, reward: float, done: bool) -> GameState:
        img = Image.fromarray(obs) if hasattr(obs, "shape") else Image.new("RGB", (1, 1))
        ram_values = {}
        if hasattr(self._env, "get_ram"):
            try:
                ram = self._env.get_ram()
                for addr in range(0, min(len(ram), 256)):
                    ram_values[f"0x{addr:04X}"] = int(ram[addr])
            except Exception:
                pass
        return GameState(
            screenshot=img, ram=ram_values, info=info, reward=reward, done=done
        )
