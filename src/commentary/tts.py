import asyncio
import tempfile
import threading
import os
import struct
from typing import Optional, Callable


class TTSController:
    def __init__(self, config: dict):
        self.enabled = config.get("commentary", {}).get("tts_enabled", False)
        self._voice = config.get("commentary", {}).get("tts_voice", "en-US-GuyNeural")
        self._volume = config.get("commentary", {}).get("tts_volume", 0.8)
        self._speaking = False
        self._edge_tts = None
        self._pygame_init = False
        self._amplitude_callback: Optional[Callable[[float], None]] = None
        self._amplitude_envelope: list[float] = []
        self._amplitude_start_time: float = 0
        self._amplitude_duration: float = 0
        self._amplitude_lock = threading.Lock()
        try:
            import edge_tts
            self._edge_tts = edge_tts
        except ImportError:
            print("Warning: edge-tts not installed. TTS disabled.")
            self.enabled = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def set_voice(self, voice: str):
        self._voice = voice

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        try:
            import pygame
            if self._pygame_init:
                pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass

    def set_amplitude_callback(self, callback: Optional[Callable[[float], None]]):
        self._amplitude_callback = callback

    def get_amplitude(self) -> float:
        import time
        with self._amplitude_lock:
            if not self._speaking or not self._amplitude_envelope:
                return 0.0
            elapsed = time.time() - self._amplitude_start_time
            if elapsed >= self._amplitude_duration:
                return 0.0
            idx = (elapsed / self._amplitude_duration) * len(self._amplitude_envelope)
            idx = max(0, min(len(self._amplitude_envelope) - 1, int(idx)))
            return self._amplitude_envelope[idx]

    def say(self, text: str):
        if not self.enabled or not self._edge_tts:
            return
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def _speak_sync(self, text: str):
        try:
            self._speaking = True
            asyncio.run(self._speak(text))
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            self._speaking = False
            with self._amplitude_lock:
                self._amplitude_envelope = []

    async def _speak(self, text: str):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        try:
            communicate = self._edge_tts.Communicate(text, self._voice)
            await communicate.save(tmp_path)
            await asyncio.to_thread(self._analyze_and_play, tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _analyze_and_play(self, path: str):
        try:
            import pygame
            if not self._pygame_init:
                pygame.mixer.init(frequency=24000)
                self._pygame_init = True

            envelope = self._extract_amplitude(path)
            import time
            with self._amplitude_lock:
                self._amplitude_envelope = envelope
                self._amplitude_start_time = time.time()
                self._amplitude_duration = 0

            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play()

            start = time.time()
            while pygame.mixer.music.get_busy():
                elapsed = time.time() - start
                with self._amplitude_lock:
                    self._amplitude_duration = elapsed
                    self._amplitude_start_time = start
                if self._amplitude_callback and envelope:
                    idx = (elapsed / max(0.01, elapsed + 0.001)) * len(envelope)
                    idx = max(0, min(len(envelope) - 1, int(idx)))
                    self._amplitude_callback(envelope[idx])
                pygame.time.wait(33)

            with self._amplitude_lock:
                self._amplitude_duration = time.time() - start
        except Exception as e:
            print(f"[TTS] Playback error: {e}")

    def _extract_amplitude(self, path: str) -> list[float]:
        try:
            import pygame
            sound = pygame.mixer.Sound(file=path)
            raw = sound.get_raw()
            sample_width = 2
            num_samples = len(raw) // sample_width
            if num_samples == 0:
                return []

            chunk_size = 1024
            envelope = []
            for i in range(0, num_samples, chunk_size):
                end = min(i + chunk_size, num_samples)
                chunk = raw[i * sample_width:end * sample_width]
                n = len(chunk) // sample_width
                if n == 0:
                    envelope.append(0.0)
                    continue
                samples = struct.unpack(f'<{n}h', chunk)
                rms = (sum(s * s for s in samples) / n) ** 0.5
                normalized = min(1.0, rms / 16000.0)
                envelope.append(normalized)

            if len(envelope) > 2:
                smoothed = []
                for i in range(len(envelope)):
                    window = envelope[max(0, i - 1):min(len(envelope), i + 2)]
                    smoothed.append(sum(window) / len(window))
                envelope = smoothed

            sound.stop()
            return envelope
        except Exception as e:
            print(f"[TTS] Amplitude analysis failed: {e}")
            return []

    def stop(self):
        try:
            import pygame
            if self._pygame_init:
                pygame.mixer.music.stop()
        except Exception:
            pass
