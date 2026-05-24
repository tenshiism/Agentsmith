import time
from enum import Enum


class Mood(Enum):
    NEUTRAL = "neutral"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    FOCUSED = "focused"
    BORED = "bored"
    PANICKED = "panicked"


class MoodTracker:
    def __init__(self):
        self._current = Mood.NEUTRAL
        self._recent_rewards: list[float] = []
        self._recent_actions: list[str] = []
        self._idle_frames = 0
        self._last_action_frame = 0
        self._frame_count = 0

    def update(self, reward: float, action: str, frame: int):
        self._frame_count = frame
        self._recent_rewards.append(reward)
        self._recent_actions.append(action)

        if action and action != "none":
            self._idle_frames = 0
            self._last_action_frame = frame
        else:
            self._idle_frames += 1

        # Keep only recent history
        if len(self._recent_rewards) > 20:
            self._recent_rewards = self._recent_rewards[-20:]
        if len(self._recent_actions) > 20:
            self._recent_actions = self._recent_actions[-20:]

        self._current = self._compute_mood()

    @property
    def mood(self) -> Mood:
        return self._current

    @property
    def is_idle(self) -> bool:
        return self._idle_frames > 60

    @property
    def recent_actions(self) -> list[str]:
        return list(self._recent_actions)

    @property
    def recent_reward_sum(self) -> float:
        return sum(self._recent_rewards[-10:])

    def _compute_mood(self) -> Mood:
        if not self._recent_rewards:
            return Mood.NEUTRAL

        recent = self._recent_rewards[-10:]
        avg = sum(recent) / len(recent)
        trend = recent[-1] - recent[0] if len(recent) > 1 else 0

        # High positive rewards = excited (need significant gains, not just small positives)
        if avg > 5 or (len(recent) >= 3 and all(r > 3 for r in recent[-3:])):
            return Mood.EXCITED

        # Negative rewards = frustrated
        if avg < -3 or trend < -5:
            return Mood.FRUSTRATED

        # Rapid action changes = panicked
        if len(self._recent_actions) >= 5:
            unique = len(set(self._recent_actions[-5:]))
            if unique >= 4 and any(r < 0 for r in recent[-5:]):
                return Mood.PANICKED

        # Idle = bored
        if self._idle_frames > 120:
            return Mood.BORED

        # Steady positive progress = focused
        if avg > 0 and trend >= 0:
            return Mood.FOCUSED

        return Mood.NEUTRAL
