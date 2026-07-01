import argparse
import json
import asyncio
from pathlib import Path

from agent.brain import AgentBrain, scan_roms
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
        buf = ctypes.create_unicode_buffer(url)
        size = ctypes.sizeof(buf)
        h = ctypes.windll.kernel32.GlobalAlloc(0x42, size)
        p = ctypes.windll.kernel32.GlobalLock(h)
        ctypes.memmove(p, buf, size)
        ctypes.windll.kernel32.GlobalUnlock(h)
        ctypes.windll.user32.OpenClipboard(0)
        ctypes.windll.user32.EmptyClipboard()
        ctypes.windll.user32.SetClipboardData(13, h)
        ctypes.windll.user32.CloseClipboard()
        print(f"\nOverlay: {url} (copied to clipboard)")
    except Exception:
        print(f"\nOverlay: {url}")


def build_adapter(cfg: dict) -> GameAdapter:
    kind = cfg["game"]["adapter"]
    if kind == "vba":
        from game.vba_adapter import VBAAdapter
        return VBAAdapter(cfg)
    if kind == "vice":
        from game.vice_adapter import ViceAdapter
        return ViceAdapter(cfg)
    raise ValueError(f"Unknown adapter '{kind}'. Available: vba, vice")


async def main():
    parser = argparse.ArgumentParser(description="AgentSmith — AI game streamer")
    parser.add_argument("--config", "-c", required=True, help="Path to config JSON")
    parser.add_argument("--headless", action="store_true", help="No display")
    parser.add_argument("--debug", "-d", action="store_true", help="Print LLM prompts and responses")
    args = parser.parse_args()

    cfg = load_config(args.config)

    print("[Agent] Scanning for ROMs...")
    available_games = scan_roms()
    print(f"[Agent] Found {len(available_games)} game(s)")

    overlay = None
    if cfg.get("streaming", {}).get("overlay_enabled", True):
        overlay = OverlayServer(cfg)
        if available_games:
            overlay.push_state({"available_games": available_games})
        await overlay.start()
        if not args.headless:
            _prompt_overlay(overlay)

    tool_cfg = cfg.get("game", {})
    print(f"[Agent] Initializing {tool_cfg.get('adapter', '?')} adapter...")
    game = build_adapter(cfg)
    tts = TTSController(cfg)
    commentary = CommentaryGenerator(cfg, tts)

    from agent.llm_client import LLMClient
    agent_cfg = cfg.get("agent", {})
    llm_action = LLMClient(agent_cfg)
    llm_action.debug = args.debug
    llm_action_fallback = LLMClient(agent_cfg["fallback"]) if agent_cfg.get("fallback") else None
    if llm_action_fallback:
        llm_action_fallback.debug = args.debug
    commentary_cfg = cfg.get("commentary", {})
    llm_commentary = LLMClient(commentary_cfg) if commentary_cfg.get("model") else llm_action
    llm_commentary.debug = args.debug

    brain = AgentBrain(cfg, game, commentary, overlay=overlay, llm=llm_action, llm_commentary=llm_commentary, llm_fallback=llm_action_fallback, available_games=available_games, debug=args.debug)

    if overlay:
        def _on_overlay_msg(d):
            if d.get("type") == "set_mode":
                brain.set_mode(d.get("mode", "direct"))
            elif d.get("type") == "set_config":
                brain.set_config(d.get("config", {}))
            elif d.get("type") == "set_status":
                brain.set_status(d.get("status", "idle"))
            elif d.get("type") == "change_game":
                brain.change_game(d.get("rom_path", ""), d.get("game_name", ""))
            elif d.get("type") == "change_character":
                brain.set_config({"personality": d.get("personality", "energetic")})
            elif d.get("type") == "test_key":
                brain.test_key(d.get("key", ""), d.get("down", True))
            elif d.get("type") == "set_volume":
                if tts:
                    tts.set_volume(d.get("volume", 0.8))
            elif d.get("type") == "voice_trigger":
                brain.on_voice_trigger()
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
