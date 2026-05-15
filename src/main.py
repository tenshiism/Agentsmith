import argparse
import json
import asyncio
from pathlib import Path

from agent.brain import AgentBrain
from game.base import GameAdapter
from game.pyboy_adapter import PyBoyAdapter
from game.gym_adapter import GymRetroAdapter
from commentary.generator import CommentaryGenerator
from commentary.tts import TTSController
from streaming.server import OverlayServer


ADAPTERS = {
    "pyboy": PyBoyAdapter,
    "gym_retro": GymRetroAdapter,
}


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_adapter(cfg: dict) -> GameAdapter:
    kind = cfg["game"]["adapter"]
    cls = ADAPTERS.get(kind)
    if not cls:
        raise ValueError(f"Unknown adapter '{kind}'. Available: {list(ADAPTERS)}")
    return cls(cfg)


async def main():
    parser = argparse.ArgumentParser(description="AgentSmith — AI game streamer")
    parser.add_argument("--config", "-c", required=True, help="Path to config JSON")
    parser.add_argument("--headless", action="store_true", help="No display")
    args = parser.parse_args()

    cfg = load_config(args.config)

    game = build_adapter(cfg)
    tts = TTSController(cfg) if cfg.get("commentary", {}).get("tts_enabled") else None
    commentary = CommentaryGenerator(cfg, tts)

    overlay = None
    if cfg.get("streaming", {}).get("overlay_enabled", True):
        overlay = OverlayServer(cfg)
        await overlay.start()

    brain = AgentBrain(cfg, game, commentary, overlay=overlay)

    try:
        await brain.run(headless=args.headless)
    except KeyboardInterrupt:
        pass
    finally:
        game.close()
        if overlay:
            await overlay.stop()
        if tts:
            tts.stop()


if __name__ == "__main__":
    asyncio.run(main())
