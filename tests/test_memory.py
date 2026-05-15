from PIL import Image
from agent.memory import GameMemory
from game.base import GameState


def _make_state(ram: dict | None = None, reward: float = 0.0, done: bool = False) -> GameState:
    return GameState(
        screenshot=Image.new("RGB", (160, 144)),
        ram=ram or {},
        reward=reward,
        done=done,
    )


class TestGameMemory:
    def test_remember_and_summarize(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        state = _make_state(reward=1.0)
        mem.remember(state, action=[1, 0, 0, 0, 0, 0, 0, 0])
        summary = mem.summarize()
        assert "Frame" in summary
        assert "action" in summary
        assert "reward" in summary

    def test_empty_summary(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        assert mem.summarize() == "No prior events."

    def test_episode_count(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        mem.remember(_make_state(done=True), None)
        assert mem.episode_count == 1
        mem.remember(_make_state(done=True), None)
        assert mem.episode_count == 2

    def test_total_reward_tracking(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        mem.remember(_make_state(reward=5.0), None)
        mem.remember(_make_state(reward=-2.0), None)
        assert mem.total_reward == 3.0

    def test_episode_reward_resets_on_done(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        mem.remember(_make_state(reward=10.0), None)
        mem.remember(_make_state(reward=5.0, done=True), None)
        assert mem.episode_reward == 0.0
        assert mem.episode_frames == 0

    def test_max_history(self):
        mem = GameMemory({"agent": {"max_history": 3}})
        for i in range(5):
            mem.remember(_make_state(reward=float(i)), None)
        assert len(mem.history) == 3

    def test_clear_resets_state(self):
        mem = GameMemory({"agent": {"max_history": 50}})
        mem.remember(_make_state(reward=10.0), None)
        mem.clear()
        assert len(mem.history) == 0
        assert mem.episode_reward == 0.0
        assert mem.episode_frames == 0
