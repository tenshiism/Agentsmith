from collections import deque
from game.base import GameState


class GameMemory:
    def __init__(self, config: dict):
        max_history = config.get("agent", {}).get("max_history", 50)
        self.history: deque[dict] = deque(maxlen=max_history)
        self.episode_count = 0
        self.total_reward: float = 0.0
        self.episode_reward: float = 0.0
        self.episode_frames: int = 0

    def remember(self, state: GameState, action: list[int] | None):
        self.history.append({
            "frame": len(self.history),
            "reward": state.reward,
            "done": state.done,
            "action": action,
            "ram_snapshot": dict(list(state.ram.items())[:10]),
        })
        self.total_reward += state.reward
        self.episode_reward += state.reward
        self.episode_frames += 1
        if state.done:
            self.episode_count += 1
            self.episode_reward = 0.0
            self.episode_frames = 0

    def summarize(self) -> str:
        if not self.history:
            return "No prior events."
        recent = list(self.history)[-5:]
        lines = []
        for entry in recent:
            action_str = "none" if entry["action"] is None else str(entry["action"])
            lines.append(f"Frame {entry['frame']}: action={action_str} reward={entry['reward']:.2f}")
        lines.append(f"Stats: total_reward={self.total_reward:.1f}, episode_frames={self.episode_frames}")
        return "\n".join(lines)

    def clear(self):
        self.history.clear()
        self.episode_reward = 0.0
        self.episode_frames = 0
