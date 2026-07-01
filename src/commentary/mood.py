import time
from enum import Enum


class Mood(Enum):
    NEUTRAL = "neutral"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    FOCUSED = "focused"
    BORED = "bored"
    PANICKED = "panicked"


HAPPY = "happy"
SAD = "sad"
ANGRY = "angry"
SURPRISED = "surprised"
RELAXED = "relaxed"

MOOD_BLENDSHAPE_MAP = {
    Mood.NEUTRAL: "neutral",
    Mood.EXCITED: "happy",
    Mood.FRUSTRATED: "angry",
    Mood.FOCUSED: "neutral",
    Mood.BORED: "relaxed",
    Mood.PANICKED: "surprised",
}

VRMA_MOOD_MAP = {
    "happy": 4,
    "angry": 0,
    "relaxed": 6,
    "surprised": 9,
    "neutral": -1,
}


class MoodTracker:
    def __init__(self):
        self._current = Mood.NEUTRAL
        self._recent_rewards: list[float] = []
        self._recent_actions: list[str] = []
        self._idle_frames = 0
        self._last_action_frame = 0
        self._frame_count = 0
        self._last_mood_change = 0.0
        self._min_mood_hold = 3.0

    def update(self, reward: float, action: str, frame: int):
        self._frame_count = frame
        self._recent_rewards.append(reward)
        self._recent_actions.append(action)

        if action and action != "none":
            self._idle_frames = 0
            self._last_action_frame = frame
        else:
            self._idle_frames += 1

        if len(self._recent_rewards) > 20:
            self._recent_rewards = self._recent_rewards[-20:]
        if len(self._recent_actions) > 20:
            self._recent_actions = self._recent_actions[-20:]

        new_mood = self._compute_mood()
        now = time.time()
        if new_mood != self._current and (now - self._last_mood_change) >= self._min_mood_hold:
            self._current = new_mood
            self._last_mood_change = now

    @property
    def mood(self) -> Mood:
        return self._current

    @property
    def mood_name(self) -> str:
        return self._current.value

    @property
    def blendshape_name(self) -> str:
        return MOOD_BLENDSHAPE_MAP.get(self._current, "neutral")

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
        avg = sum(recent) / len(recent) if recent else 0
        trend = recent[-1] - recent[0] if len(recent) > 1 else 0

        if avg > 5 or (len(recent) >= 3 and all(r > 3 for r in recent[-3:])):
            return Mood.EXCITED

        if avg < -3 or trend < -5:
            return Mood.FRUSTRATED

        if len(self._recent_actions) >= 5:
            unique = len(set(self._recent_actions[-5:]))
            if unique >= 4 and any(r < 0 for r in recent[-5:]):
                return Mood.PANICKED

        if self._idle_frames > 120:
            return Mood.BORED

        if avg > 0 and trend >= 0:
            return Mood.FOCUSED

        return Mood.NEUTRAL
