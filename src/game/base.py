from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image
import numpy as np


@dataclass
class GameState:
    screenshot: Image.Image
    ram: dict[str, int] = field(default_factory=dict)
    info: dict = field(default_factory=dict)
    done: bool = False
    reward: float = 0.0


class GameAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config
        self._rom_loaded = False

    @abstractmethod
    def load_rom(self, path: str) -> None:
        ...

    @abstractmethod
    def step(self, action: list[int]) -> GameState:
        ...

    @abstractmethod
    def reset(self) -> GameState:
        ...

    @abstractmethod
    def get_available_actions(self) -> list[list[int]]:
        ...

    @abstractmethod
    def get_action_names(self) -> list[str]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def screenshot_to_array(self, img: Image.Image) -> np.ndarray:
        return np.array(img.convert("RGB"))
