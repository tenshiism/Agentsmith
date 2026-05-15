import asyncio
import base64
import io
from PIL import Image

from .llm_client import LLMClient
from .memory import GameMemory
from .strategies import load_strategy
from game.base import GameAdapter
from commentary.generator import CommentaryGenerator
from streaming.server import OverlayServer


class AgentBrain:
    def __init__(self, config: dict, game: GameAdapter, commentary: CommentaryGenerator,
                 overlay: OverlayServer | None = None, llm: LLMClient | None = None):
        self.config = config
        self.game = game
        self.commentary = commentary
        self.overlay = overlay
        self.llm = llm or LLMClient(config.get("agent", {}))
        self.memory = GameMemory(config)
        self.strategy = load_strategy(config.get("agent", {}).get("strategy", "balanced"))
        self.frame_interval = config.get("game", {}).get("observe_every_n_frames", 30)
        self.frame_count = 0
        self.last_action_name = "none"

    async def run(self, headless: bool = False):
        state = self.game.reset()
        self.memory.remember(state, action=None)

        initial_prompt = self._build_prompt(state, is_first=True)
        commentary_text = await self.llm.commentate(initial_prompt)
        self.commentary.speak(commentary_text)

        while not state.done:
            actions = self.game.get_available_actions()
            prompt = self._build_prompt(state)

            chosen_action = await self._decide_action(prompt, actions)
            self.last_action_name = self.game.get_action_names()[
                chosen_action.index(1)
            ] if 1 in chosen_action else "none"
            state = self.game.step(chosen_action)
            self.frame_count += 1

            self.memory.remember(state, chosen_action)

            if self.frame_count % self.frame_interval == 0:
                commentary_prompt = self._build_commentary_prompt(state)
                commentary_text = await self.llm.commentate(commentary_prompt)
                self.commentary.speak(commentary_text)

            if self.overlay:
                await self.overlay.broadcast(self._build_overlay_state(state, chosen_action))

            await asyncio.sleep(0.01)

        self.commentary.speak("Game over! That was a great run.")

    def _screenshot_to_b64(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.resize((224, 224)).save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def _build_prompt(self, state, is_first: bool = False) -> list:
        b64_img = self._screenshot_to_b64(state.screenshot)
        ram_summary = ", ".join(f"{k}={v}" for k, v in list(state.ram.items())[:20])

        system_msg = self.strategy["system_prompt"]
        game_context = self.memory.summarize()

        user_content = f"[Frame {self.frame_count}]\nRAM: {ram_summary}\nRecent events: {game_context}"
        if is_first:
            user_content = "[START] Game just began.\n" + user_content

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
            ]},
        ]

    def _build_overlay_state(self, state, action: list[int]) -> dict:
        return {
            "frame": self.frame_count,
            "reward": state.reward,
            "done": state.done,
            "last_action": self.last_action_name,
            "strategy": self.config.get("agent", {}).get("strategy", "balanced"),
            "model": self.config.get("agent", {}).get("model", "unknown"),
            "episode": self.memory.episode_count,
            "memory_size": len(self.memory.history),
            "commentary": self.commentary.last_comment,
            "screenshot": self._screenshot_to_b64(state.screenshot),
        }

    def _build_commentary_prompt(self, state) -> list:
        b64_img = self._screenshot_to_b64(state.screenshot)
        ram_summary = ", ".join(f"{k}={v}" for k, v in list(state.ram.items())[:10])

        personality = self.config.get("commentary", {}).get("personality", "energetic")
        style_prompt = f"You are a {personality} game streamer narrating gameplay. React to what's happening on screen. Be natural, concise, and entertaining."

        return [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": f"Game state — Frame {self.frame_count}\nRAM: {ram_summary}\nCommentate on what you see."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
            ]},
        ]

    async def _decide_action(self, prompt: list, actions: list[list[int]]) -> list[int]:
        result = await self.llm.choose_action(prompt, self.game.get_action_names())
        action_names = self.game.get_action_names()

        chosen = [0] * len(action_names)
        if result in action_names:
            idx = action_names.index(result)
            chosen[idx] = 1

        return chosen
