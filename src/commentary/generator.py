from typing import Optional
from .personalities import PERSONALITIES
from .tts import TTSController


class CommentaryGenerator:
    def __init__(self, config: dict, tts: Optional[TTSController] = None):
        self.config = config
        self.tts = tts
        persona_name = config.get("commentary", {}).get("personality", "energetic")
        self.persona = PERSONALITIES.get(persona_name, PERSONALITIES["energetic"])
        self.last_comment = ""

    def speak(self, text: str):
        if not text or text == self.last_comment:
            return
        self.last_comment = text
        if self.tts:
            self.tts.say(text)
        return text

    def build_commentary_context(self, game_state) -> str:
        reward = game_state.reward
        if reward > 10:
            return "Big score! Something good just happened."
        elif reward < -5:
            return "Ouch, took some damage there."
        return ""
