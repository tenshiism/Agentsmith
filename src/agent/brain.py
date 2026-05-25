import asyncio
import base64
import io
import time
from pathlib import Path
from PIL import Image

from .llm_client import LLMClient
from .memory import GameMemory
from .strategies import load_strategy
from utils.debug_log import save_screenshot
from game.base import GameAdapter
from commentary.generator import CommentaryGenerator
from commentary.personalities import PERSONALITIES
from streaming.server import OverlayServer

MODES = {
    "gentle": {
        "min_llm_interval": 12.0,
        "min_commentary_interval": 30.0,
        "shared_ai_cooldown": False,
        "retry_rate_base": 12.0,
        "retry_rate_max": 60.0,
    },
    "balanced": {
        "min_llm_interval": 10.0,
        "min_commentary_interval": 30.0,
        "shared_ai_cooldown": False,
        "retry_rate_base": 2.0,
        "retry_rate_max": 30.0,
    },
    "custom": {
        "min_llm_interval": 10.0,
        "min_commentary_interval": 30.0,
        "shared_ai_cooldown": False,
        "retry_rate_base": 2.0,
        "retry_rate_max": 30.0,
    },
}


class AgentBrain:
    def __init__(self, config: dict, game: GameAdapter, commentary: CommentaryGenerator,
                 overlay: OverlayServer | None = None,
                 llm: LLMClient | None = None,
                 llm_commentary: LLMClient | None = None,
                 llm_fallback: LLMClient | None = None):
        self.config = config
        self.game = game
        self.commentary = commentary
        self.overlay = overlay
        self.llm = llm or LLMClient(config.get("agent", {}))
        self.llm_fallback = llm_fallback
        self.llm_commentary = llm_commentary or self.llm
        self.memory = GameMemory(config)
        self.strategy_name = config.get("agent", {}).get("strategy", "balanced")
        self.strategy = load_strategy(self.strategy_name)
        self.personality_name = config.get("commentary", {}).get("personality", "energetic")
        self.start_time = 0.0
        self._last_overlay_broadcast = 0.0
        self.last_action_name = "none"
        self.last_llm_time = 0.0
        self.last_commentary_time = 0.0
        self._status_intervals = [10, 20, 30, 60, 120, 180, 300, 600, 1800, 3600, 7200, 10800]
        self._status_index = 0
        self._current_ai_task = None
        self.mode_name = "custom"
        self.status = "idle"
        self._tts_enabled = config.get("commentary", {}).get("tts_enabled", False)
        self._commentary_enabled = config.get("commentary", {}).get("enabled", True)
        self._session_costs = {
            "action": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
            "commentary": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
        }
        self._session_start_time = time.time()
        self._current_model_name = config.get("agent", {}).get("model", "unknown")
        self._current_commentary_model = config.get("agent", {}).get("model", "unknown")
        self._apply_mode()
        self._available_games = self._scan_roms()
        self.startup_sequence = config.get("game", {}).get("startup_sequence", [])

    def _apply_mode(self):
        mode = MODES.get(self.mode_name, MODES["gentle"])
        self.min_llm_interval = mode["min_llm_interval"]
        self.min_commentary_interval = mode["min_commentary_interval"]
        self.shared_ai_cooldown = mode["shared_ai_cooldown"]
        self.retry_rate_base = mode["retry_rate_base"]
        self.retry_rate_max = mode["retry_rate_max"]
        for client in [self.llm, self.llm_fallback, self.llm_commentary]:
            if client:
                client.set_retry_params(self.retry_rate_base, self.retry_rate_max)

    def _scan_roms(self) -> list[dict]:
        games = []
        project_root = Path(__file__).resolve().parent.parent.parent
        rom_dir = project_root / "roms"
        if not rom_dir.exists():
            return games
        for ext in (".gb", ".gbc", ".gba"):
            for f in sorted(rom_dir.rglob(f"*{ext}")):
                if f.is_file():
                    name = f.stem.replace("_", " ").replace("-", " ").title()
                    rel = f.relative_to(project_root)
                    games.append({"name": name, "path": str(rel.as_posix())})
        return games

    def change_game(self, rom_path: str, game_name: str) -> None:
        was_running = self.status == "running"
        self.set_status("idle")
        self.memory.clear()
        self.frame_count = 0
        self.start_time = time.time()
        self.last_llm_time = 0.0
        self.last_commentary_time = 0.0
        self.config["game"]["rom_path"] = rom_path
        if game_name:
            self.config["game"]["name"] = game_name
        else:
            stem = Path(rom_path).stem
            self.config["game"]["name"] = stem.replace("_", " ").replace("-", " ").title()
        try:
            self.game.set_rom_path(rom_path)
            state = self.game.reset()
            self.memory.remember(state, action=None)
            print(f"[Agent] Game changed to: {self.config['game']['name']} ({rom_path})")
        except Exception as e:
            print(f"[Agent] Failed to switch game: {e}")
        if was_running:
            self.set_status("running")

    def _apply_config(self):
        for client in [self.llm, self.llm_fallback, self.llm_commentary]:
            if client:
                client.set_retry_params(self.retry_rate_base, self.retry_rate_max)
                client.set_cancel_check(lambda: self.status != "running")

    def set_mode(self, name: str):
        if name == "custom":
            if self.mode_name != "custom":
                self.mode_name = "custom"
                print("[Agent] Mode: custom (preserving current values)")
            return
        if name in MODES and name != self.mode_name:
            self.mode_name = name
            self._apply_mode()
            self._apply_config()
            mode = MODES[name]
            print(f"[Agent] Mode: {name} — action={mode['min_llm_interval']}s comm={mode['min_commentary_interval']}s shared={mode['shared_ai_cooldown']} retry={mode['retry_rate_base']}s->{mode['retry_rate_max']}s")

    def set_config(self, cfg: dict):
        changed = False
        for key in ("min_llm_interval", "min_commentary_interval", "shared_ai_cooldown", "retry_rate_base", "retry_rate_max"):
            if key in cfg and cfg[key] != getattr(self, key, None):
                setattr(self, key, cfg[key])
                changed = True

        action_provider = cfg.get("action_model_provider")
        action_model = cfg.get("action_model_name")
        if action_provider:
            self.llm.set_model(action_provider, action_model or self.llm.model, cfg.get("action_model_base_url", ""))
            changed = True

        commentary_provider = cfg.get("commentary_model_provider")
        commentary_model = cfg.get("commentary_model_name")
        if commentary_provider:
            self.llm_commentary.set_model(commentary_provider, commentary_model or self.llm_commentary.model, cfg.get("commentary_model_base_url", ""))
            changed = True

        # Apply temperature / max_tokens to LLM clients
        if "action_temperature" in cfg:
            self.llm.temperature = cfg["action_temperature"]
            changed = True
        if "commentary_temperature" in cfg:
            self.llm_commentary.temperature = cfg["commentary_temperature"]
            changed = True
        if "action_max_tokens" in cfg:
            self.llm._action_max_tokens = cfg["action_max_tokens"]
            changed = True
        if "commentary_max_tokens" in cfg:
            self.llm_commentary._commentary_max_tokens = cfg["commentary_max_tokens"]
            changed = True

        # Strategy
        if "strategy" in cfg and cfg["strategy"] != self.strategy_name:
            self.strategy_name = cfg["strategy"]
            self.strategy = load_strategy(cfg["strategy"])
            changed = True

        # Personality, TTS, commentary enabled — stored for broadcast, applied in commentary
        if "personality" in cfg:
            self.personality_name = cfg["personality"]
            persona = PERSONALITIES.get(cfg["personality"])
            if persona:
                self.commentary.persona = persona
            changed = True
        if "tts_enabled" in cfg:
            self._tts_enabled = cfg["tts_enabled"]
            if self.commentary.tts:
                self.commentary.tts.enabled = cfg["tts_enabled"]
            changed = True
        if "commentary_enabled" in cfg:
            self._commentary_enabled = cfg["commentary_enabled"]
            changed = True

        model_changed_action = action_model and action_model != self._current_model_name
        model_changed_comm = commentary_model and commentary_model != self._current_commentary_model
        if model_changed_action or model_changed_comm:
            self._session_costs = {
                "action": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
                "commentary": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
            }
            self._session_start_time = time.time()
            if action_model:
                self._current_model_name = action_model
            if commentary_model:
                self._current_commentary_model = commentary_model
            print("[Agent] Model changed — costs reset")

        if changed:
            self.mode_name = "custom"
            self._apply_config()
            print(f"[Agent] Config updated — action={self.min_llm_interval}s comm={self.min_commentary_interval}s shared={self.shared_ai_cooldown}")

    def set_status(self, new_status: str):
        if new_status in ("idle", "running") and new_status != self.status:
            self.status = new_status
            if new_status == "running":
                self.last_llm_time = 0.0
                self.last_commentary_time = 0.0
            print(f"[Agent] Status: {self.status}")

    def _last_ai_time(self) -> float:
        return max(self.last_llm_time, self.last_commentary_time)

    def _llm_cooldown_ok(self) -> bool:
        t = self._last_ai_time() if self.shared_ai_cooldown else self.last_llm_time
        return (time.time() - t) >= self.min_llm_interval

    def _commentary_cooldown_ok(self) -> bool:
        t = self._last_ai_time() if self.shared_ai_cooldown else self.last_commentary_time
        return (time.time() - t) >= self.min_commentary_interval

    def _tts_busy(self) -> bool:
        tts = getattr(self.commentary, 'tts', None)
        return bool(tts and tts.enabled and tts.is_speaking)

    async def _run_ai_call(self, coro):
        task = asyncio.create_task(coro)
        self._current_ai_task = task
        try:
            return await task
        except asyncio.CancelledError:
            print("[Agent] AI call interrupted by stop")
            raise
        finally:
            self._current_ai_task = None

    async def run(self, headless: bool = False):
        state = self.game.reset()
        self.start_time = time.time()
        self.memory.remember(state, action=None)
        print(f"[Agent] Game started — {self.config.get('game', {}).get('name', 'unknown')}")

        if self.overlay:
            await self.overlay.broadcast(self._build_overlay_state(state, [0] * len(self.game.get_available_actions()[0])))

        if self.startup_sequence:
            startup_actions = []
            for action_name in self.startup_sequence:
                actions = self.game.get_available_actions()
                action_names = self.game.get_action_names()
                if action_name in action_names:
                    idx = action_names.index(action_name)
                    vec = [0] * len(actions)
                    vec[idx] = 1
                    startup_actions.append(vec)
            for v in startup_actions:
                self.game.step(v)
                await asyncio.sleep(0.5)
            state = self.game.capture_state()
            print(f"[Agent] Startup sequence complete: {self.startup_sequence}")

        if self.status == "running":
            print("[Agent] Generating initial commentary...")
            try:
                commentary_text, commentary_usage = await self.llm_commentary.commentate(self._build_commentary_prompt(state))
                if commentary_usage:
                    self._session_costs["commentary"]["prompt_tokens"] += commentary_usage.get("prompt_tokens", 0)
                    self._session_costs["commentary"]["completion_tokens"] += commentary_usage.get("completion_tokens", 0)
                    self._session_costs["commentary"]["cost"] += commentary_usage.get("cost", 0.0)
                self.commentary.speak(commentary_text)
                self.last_commentary_time = time.time()
                print(f"[Commentary] {commentary_text}")
            except Exception as e:
                print(f"[Agent] Commentary failed (continuing anyway): {e}")

        while not state.done:
            actions = self.game.get_available_actions()
            noop = [0] * len(actions)
            chosen_action = noop

            action_usage = None
            if self.status == "running" and self._llm_cooldown_ok() and not self._tts_busy():
                print("[Agent] Deciding action...")
                _buf = io.BytesIO(); state.screenshot.save(_buf, format="JPEG", quality=60); save_screenshot(_buf.getvalue())
                try:
                    chosen_action, action_usage = await self._run_ai_call(self._decide_action(state, actions))
                    self.last_action_name = self.game.get_action_names()[
                        chosen_action.index(1)
                    ] if 1 in chosen_action else "none"
                    self.last_llm_time = time.time()
                    print(f"[Action] {self.last_action_name}")
                except (asyncio.CancelledError, RuntimeError):
                    chosen_action = noop
                    self.last_action_name = "none"
                except Exception as e:
                    print(f"[Agent] Action LLM failed: {e}")
                    chosen_action = noop
                    self.last_action_name = "none"
                if action_usage:
                    self._session_costs["action"]["prompt_tokens"] += action_usage.get("prompt_tokens", 0)
                    self._session_costs["action"]["completion_tokens"] += action_usage.get("completion_tokens", 0)
                    self._session_costs["action"]["cost"] += action_usage.get("cost", 0.0)
            else:
                self.last_action_name = "none"

            self.game.step(chosen_action)
            state = self.game.capture_state()

            if chosen_action is not noop:
                self.memory.remember(state, chosen_action)

            commentary_usage = None
            if self.status == "running" and self._commentary_cooldown_ok() and not self._tts_busy():
                print("[Agent] Generating commentary...")
                state = self.game.capture_state()
                commentary_prompt = self._build_commentary_prompt(state)
                try:
                    commentary_text, commentary_usage = await self._run_ai_call(self.llm_commentary.commentate(commentary_prompt))
                    self.commentary.speak(commentary_text)
                    self.last_commentary_time = time.time()
                    print(f"[Commentary] {commentary_text}")
                except (asyncio.CancelledError, RuntimeError):
                    pass
                except Exception as e:
                    print(f"[Agent] Commentary failed: {e}")
                if commentary_usage:
                    self._session_costs["commentary"]["prompt_tokens"] += commentary_usage.get("prompt_tokens", 0)
                    self._session_costs["commentary"]["completion_tokens"] += commentary_usage.get("completion_tokens", 0)
                    self._session_costs["commentary"]["cost"] += commentary_usage.get("cost", 0.0)

            if self._status_index < len(self._status_intervals):
                elapsed = time.time() - self.start_time
                if elapsed >= self._status_intervals[self._status_index]:
                    print(f"[Status] ({elapsed:.0f}s) — last action: {self.last_action_name}")
                    self._status_index += 1
                    if self._status_index >= len(self._status_intervals):
                        print("[Agent] 3 hours elapsed, shutting down.")
                        import sys; sys.exit(0)

            if self.overlay:
                now = time.time()
                if now - self._last_overlay_broadcast >= 0.3:
                    self._last_overlay_broadcast = now
                    await self.overlay.broadcast(self._build_overlay_state(state, chosen_action))

            await asyncio.sleep(0.01)

        self.commentary.speak("Game over! That was a great run.")

    def _screenshot_to_b64(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.resize((224, 224)).save(buf, format="JPEG", quality=60)
        return base64.b64encode(buf.getvalue()).decode()

    def _screenshot_to_b64_full(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()

    def _build_prompt(self, state, is_first: bool = False, with_image: bool = True) -> list:
        ram_summary = ", ".join(f"{k}={v}" for k, v in list(state.ram.items())[:20])
        game_name = self.config.get("game", {}).get("name", "a game")

        system_msg = self.strategy["system_prompt"]
        game_context = self.memory.summarize()

        elapsed = time.time() - self.start_time
        user_content = (
            f"You are playing {game_name} on a 4x4 grid. "
            f"The screenshot shows the current tile positions. Merge matching tiles to reach 2048. "
            f"[Elapsed: {elapsed:.0f}s]\nRAM: {ram_summary}\nRecent events: {game_context}"
        )
        if is_first:
            user_content = "[START] Game just began.\n" + user_content

        msg = {"role": "user", "content": user_content}
        if with_image:
            b64_img = self._screenshot_to_b64(state.screenshot)
            msg["content"] = [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
            ]

        return [
            {"role": "system", "content": system_msg},
            msg,
        ]

    def _build_overlay_state(self, state, action: list[int]) -> dict:
        tc = self._session_costs
        total_cost = tc["action"]["cost"] + tc["commentary"]["cost"]
        elapsed_h = (time.time() - self._session_start_time) / 3600
        hourly_rate = total_cost / elapsed_h if elapsed_h > 0 else 0
        return {
            "elapsed": round(time.time() - self.start_time, 1),
            "reward": state.reward,
            "done": state.done,
            "last_action": self.last_action_name,
            "mode": self.mode_name,
            "model": self.llm.model,
            "episode": self.memory.episode_count,
            "memory_size": len(self.memory.history),
            "commentary": self.commentary.last_comment,
            "screenshot": self._screenshot_to_b64(state.screenshot),
            "screenshot_full": self._screenshot_to_b64_full(state.screenshot),
            "tts_speaking": self._tts_busy(),
            "status": self.status,
            "strategy": self.strategy_name,
            "game_name": self.config.get("game", {}).get("name", ""),
            "game_path": self.config.get("game", {}).get("rom_path", ""),
            "available_games": self._available_games,
            "config": {
                "min_llm_interval": self.min_llm_interval,
                "min_commentary_interval": self.min_commentary_interval,
                "shared_ai_cooldown": self.shared_ai_cooldown,
                "retry_rate_base": self.retry_rate_base,
                "retry_rate_max": self.retry_rate_max,
                "action_model_provider": self.llm.provider,
                "action_model_name": self.llm.model,
                "action_model_base_url": getattr(self.llm, 'base_url', ''),
                "action_temperature": self.llm.temperature,
                "action_max_tokens": getattr(self.llm, '_action_max_tokens', 10),
                "commentary_model_provider": self.llm_commentary.provider,
                "commentary_model_name": self.llm_commentary.model,
                "commentary_model_base_url": getattr(self.llm_commentary, 'base_url', ''),
                "commentary_temperature": self.llm_commentary.temperature,
                "commentary_max_tokens": getattr(self.llm_commentary, '_commentary_max_tokens', 120),
                "strategy": self.strategy_name,
                "personality": self.personality_name,
                "tts_enabled": self._tts_enabled,
                "commentary_enabled": self._commentary_enabled,
            },
            "costs": {
                "action_tokens": tc["action"]["prompt_tokens"] + tc["action"]["completion_tokens"],
                "action_cost": round(tc["action"]["cost"], 6),
                "commentary_tokens": tc["commentary"]["prompt_tokens"] + tc["commentary"]["completion_tokens"],
                "commentary_cost": round(tc["commentary"]["cost"], 6),
                "total_cost": round(total_cost, 6),
                "hourly_rate": round(hourly_rate, 4),
                "model": self._current_model_name,
            },
        }

    def _build_commentary_prompt(self, state) -> list:
        ram_summary = ", ".join(f"{k}={v}" for k, v in list(state.ram.items())[:10])
        game_name = self.config.get("game", {}).get("name", "a game")

        personality = self.config.get("commentary", {}).get("personality", "energetic")
        style_prompt = f"You are a {personality} game streamer narrating gameplay. React to what's happening on screen. Be natural, concise, and entertaining."

        elapsed = time.time() - self.start_time
        user_content = f"You are playing {game_name} on a 4x4 grid. The screenshot shows the current tile positions. Merge matching tiles to reach 2048. [Elapsed: {elapsed:.0f}s]\nRAM: {ram_summary}\nCommentate on what you see."

        b64_img = self._screenshot_to_b64(state.screenshot)
        return [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
            ]},
        ]

    async def _decide_action(self, state, actions: list[list[int]]) -> tuple[list[int], dict | None]:
        action_names = self.game.get_action_names()
        result = "none"
        usage = None

        prompt = self._build_prompt(state, with_image=True)
        try:
            result, usage = await self.llm.choose_action(prompt, action_names)
        except Exception as e:
            print(f"[Agent] Primary action LLM failed: {e}")
            if self.llm_fallback:
                print("[Agent] Trying fallback LLM...")
                try:
                    result, usage = await self.llm_fallback.choose_action(prompt, action_names)
                except Exception as e2:
                    print(f"[Agent] Fallback LLM also failed: {e2}")

        chosen = [0] * len(action_names)
        if result in action_names:
            idx = action_names.index(result)
            chosen[idx] = 1

        return chosen, usage
