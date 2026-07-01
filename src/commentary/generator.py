from typing import Optional
from .personalities import PERSONALITIES
from .tts import TTSController


import re

_MAX_WORDS = 128


def _clean_commentary(raw: str) -> str:
    text = raw.strip()
    first_quote = text.find('"')
    if first_quote >= 0:
        text = text[first_quote:]
    text = re.sub(r'\*[^*]*\*', '', text)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    words = text.split()
    if len(words) > _MAX_WORDS:
        words = words[:_MAX_WORDS]
    text = " ".join(words)
    para = text.find("\n\n")
    if para > 0:
        text = text[:para]
    if text.count('"') % 2 != 0:
        text = text.rstrip('"')
    return text.strip()


class CommentaryGenerator:
    def __init__(self, config: dict, tts: Optional[TTSController] = None):
        self.config = config
        self.tts = tts
        persona_name = config.get("commentary", {}).get("personality", "energetic")
        self.persona = PERSONALITIES.get(persona_name, PERSONALITIES["energetic"])
        self.last_comment = ""
        if self.tts:
            voice = config.get("commentary", {}).get("tts_voice") or self.persona.get("voice", "en-US-GuyNeural")
            self.tts.set_voice(voice)

    def speak(self, text: str):
        if not text or text == self.last_comment:
            return
        cleaned = _clean_commentary(text)
        if not cleaned:
            return
        self.last_comment = cleaned
        if self.tts:
            self.tts.say(cleaned)
        return cleaned

