import argparse
import json
import asyncio
from pathlib import Path

from agent.brain import AgentBrain
from game.base import GameAdapter
from commentary.generator import CommentaryGenerator
from commentary.tts import TTSController
from streaming.server import OverlayServer


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _prompt_overlay(overlay):
    port = overlay.port
    url = f"http://localhost:{port}"
    try:
        import ctypes
        w = ctypes.create_unicode_buffer(url + "\0")
        ctypes.windll.user32.OpenClipboard(0)
        ctypes.windll.user32.EmptyClipboard()
        h = ctypes.windll.kernel32.GlobalAlloc(0x42, len(url) * 2 + 2)
        ctypes.windll.kernel32.lstrcpyW(h, w)
        ctypes.windll.user32.SetClipboardData(13, h)
        ctypes.windll.user32.CloseClipboard()
        resp = ctypes.windll.user32.MessageBoxW(0, f"Overlay: {url}\n(URL copied to clipboard)\n\nOpen in browser?", "AgentSmith", 4)
        if resp == 6:
            import webbrowser
            webbrowser.open(url)
    except Exception:
        print(f"\nOverlay: {url}")


def build_adapter(cfg: dict) -> GameAdapter:
    kind = cfg["game"]["adapter"]
    if kind == "vba":
        from game.vba_adapter import VBAAdapter
        return VBAAdapter(cfg)
    raise ValueError(f"Unknown adapter '{kind}'. Available: vba")


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
        if not args.headless:
            _prompt_overlay(overlay)

    from agent.llm_client import LLMClient
    agent_cfg = cfg.get("agent", {})
    llm_action = LLMClient(agent_cfg)
    llm_action_fallback = LLMClient(agent_cfg["fallback"]) if agent_cfg.get("fallback") else None
    commentary_cfg = cfg.get("commentary", {})
    llm_commentary = LLMClient(commentary_cfg) if commentary_cfg.get("model") else llm_action

    brain = AgentBrain(cfg, game, commentary, overlay=overlay, llm=llm_action, llm_commentary=llm_commentary, llm_fallback=llm_action_fallback)

    if overlay:
        def _on_overlay_msg(d):
            if d.get("type") == "set_mode":
                brain.set_mode(d.get("mode", "gentle"))
            elif d.get("type") == "set_config":
                brain.set_config(d.get("config", {}))
            elif d.get("type") == "set_status":
                brain.set_status(d.get("status", "idle"))
        overlay.set_message_handler(_on_overlay_msg)

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
