import threading
from typing import Optional


class TTSController:
    def __init__(self, config: dict):
        self.enabled = config.get("commentary", {}).get("tts_enabled", False)
        self._engine = None
        if self.enabled:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 180)
                self._engine.setProperty("volume", 0.9)
            except ImportError:
                print("Warning: pyttsx3 not installed. TTS disabled.")
                self.enabled = False

    def say(self, text: str):
        if not self.enabled or not self._engine:
            return
        thread = threading.Thread(target=self._speak, args=(text,), daemon=True)
        thread.start()

    def _speak(self, text: str):
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass

    def stop(self):
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
