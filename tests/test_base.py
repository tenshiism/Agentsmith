import numpy as np
from PIL import Image

from game.base import GameState, GameAdapter


class TestGameState:
    def test_default_values(self):
        img = Image.new("RGB", (160, 144))
        state = GameState(screenshot=img)
        assert state.ram == {}
        assert state.info == {}
        assert state.done is False
        assert state.reward == 0.0

    def test_custom_values(self):
        img = Image.new("RGB", (160, 144))
        state = GameState(
            screenshot=img,
            ram={"lives": 3},
            info={"score": 100},
            done=True,
            reward=50.0,
        )
        assert state.ram["lives"] == 3
        assert state.info["score"] == 100
        assert state.done is True
        assert state.reward == 50.0


class TestGameAdapter:
    def test_screenshot_to_array(self):
        class ConcreteAdapter(GameAdapter):
            def load_rom(self, path): pass
            def step(self, action): pass
            def reset(self): pass
            def get_available_actions(self): return []
            def get_action_names(self): return []
            def close(self): pass

        adapter = ConcreteAdapter({"game": {}})
        img = Image.new("RGB", (4, 4), color=(255, 0, 0))
        arr = adapter.screenshot_to_array(img)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (4, 4, 3)
        assert (arr[0, 0] == [255, 0, 0]).all()
