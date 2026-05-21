import base64
from unittest.mock import Mock, AsyncMock

import pytest
from PIL import Image

from agent.brain import AgentBrain
from game.base import GameAdapter, GameState


class _MockGame(GameAdapter):
    def __init__(self):
        super().__init__({"game": {"speed": 1.0}})
        self._action_names = ["a", "b", "up", "down", "left", "right", "start", "select"]
        self._call_count = 0

    def load_rom(self, path: str):
        pass

    def reset(self) -> GameState:
        return GameState(screenshot=Image.new("RGB", (160, 144)), reward=0.0)

    def step(self, action: list[int]) -> GameState:
        self._call_count += 1
        return GameState(
            screenshot=Image.new("RGB", (160, 144)),
            reward=1.0 if self._call_count > 1 else 0.0,
            done=self._call_count >= 5,
        )

    def get_available_actions(self) -> list[list[int]]:
        n = len(self._action_names)
        return [[1 if i == j else 0 for j in range(n)] for i in range(n)] + [[0] * n]

    def get_action_names(self) -> list[str]:
        return self._action_names

    def close(self):
        pass


class FakeLLM:
    async def choose_action(self, prompt, action_names):
        return "a"

    async def commentate(self, prompt):
        return "Let's play!"


class FakeCommentary:
    def __init__(self):
        self.last_comment = ""
    def speak(self, text):
        self.last_comment = text
        return text


class TestAgentBrain:
    @pytest.fixture
    def brain(self):
        cfg = {
            "agent": {"strategy": "balanced", "model": "qwen/qwen3.6-plus:free"},
            "commentary": {"personality": "chill"},
            "game": {"observe_every_n_frames": 2},
        }
        brain = AgentBrain(cfg, _MockGame(), FakeCommentary(), llm=FakeLLM())
        return brain

    def test_build_prompt_structure(self, brain):
        state = GameState(screenshot=Image.new("RGB", (160, 144)), ram={"0xFF00": 0}, reward=0.0)
        prompt = brain._build_prompt(state, is_first=True)
        assert len(prompt) == 2
        assert prompt[0]["role"] == "system"
        assert prompt[1]["role"] == "user"
        content = prompt[1]["content"]
        assert isinstance(content, list)
        assert any(c["type"] == "text" for c in content)
        assert any(c["type"] == "image_url" for c in content)

    def test_build_prompt_first_frame(self, brain):
        state = GameState(screenshot=Image.new("RGB", (160, 144)), reward=0.0)
        prompt = brain._build_prompt(state, is_first=True)
        text_part = next(c for c in prompt[1]["content"] if c["type"] == "text")
        assert "[START]" in text_part["text"]

    def test_build_prompt_normal_frame(self, brain):
        state = GameState(screenshot=Image.new("RGB", (160, 144)), reward=0.0)
        prompt = brain._build_prompt(state, is_first=False)
        text_part = next(c for c in prompt[1]["content"] if c["type"] == "text")
        assert "[START]" not in text_part["text"]

    @pytest.mark.asyncio
    async def test_decide_action_returns_valid_vector(self, brain):
        prompt = [{"role": "system", "content": "play"}, {"role": "user", "content": "go"}]
        actions = brain.game.get_available_actions()
        result = await brain._decide_action(prompt, actions)
        assert isinstance(result, list)
        assert len(result) == len(brain.game.get_action_names())
        assert all(v in (0, 1) for v in result)

    @pytest.mark.asyncio
    async def test_unknown_action_returns_zeros(self, brain):
        class UnknownActionLLM:
            async def choose_action(self, prompt, action_names):
                return "zzz_not_a_real_action"
        brain.llm = UnknownActionLLM()
        prompt = [{"role": "system", "content": "play"}, {"role": "user", "content": "go"}]
        actions = brain.game.get_available_actions()
        result = await brain._decide_action(prompt, actions)
        assert result == [0] * len(brain.game.get_action_names())

    def test_build_overlay_state(self, brain):
        state = GameState(
            screenshot=Image.new("RGB", (160, 144)),
            ram={"0xFF00": 42},
            reward=2.5,
        )
        overlay = brain._build_overlay_state(state, [1, 0, 0, 0, 0, 0, 0, 0])
        assert overlay["frame"] == 0
        assert overlay["reward"] == 2.5
        assert overlay["done"] is False
        assert overlay["model"] == "qwen/qwen3.6-plus:free"
        assert isinstance(overlay["screenshot"], str)
        base64.b64decode(overlay["screenshot"])

    def test_screenshot_to_b64(self, brain):
        img = Image.new("RGB", (160, 144), color="red")
        b64 = brain._screenshot_to_b64(img)
        decoded = base64.b64decode(b64)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"
