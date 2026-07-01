import asyncio
import json
import logging
from pathlib import Path

import aiohttp
from aiohttp import web

from .overlay import OverlayRenderer

logger = logging.getLogger(__name__)


class OverlayServer:
    def __init__(self, config: dict):
        self.config = config
        self.port = config.get("streaming", {}).get("overlay_port", 8765)
        self.renderer = OverlayRenderer(config)
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._latest_state: dict | None = None
        self._ws_clients: set[web.WebSocketResponse] = set()
        self._on_message = None
        self._vtuber_model_idx = 0
        self._setup_routes()

    def set_message_handler(self, handler):
        self._on_message = handler

    def _setup_routes(self):
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/avatar-only", self._handle_avatar_only)
        self._app.router.add_get("/ws", self._handle_ws)
        self._app.router.add_get("/api/model-pricing", self._handle_model_pricing)
        self._app.router.add_post("/api/cache-font", self._handle_cache_font)
        self._app.router.add_static(
            "/assets",
            Path(__file__).resolve().parent.parent.parent / "assets",
            show_index=False,
        )
        self._app.router.add_static(
            "/streaming",
            Path(__file__).resolve().parent,
            show_index=False,
        )
        _docs_repos = Path(__file__).resolve().parent.parent.parent / "docs" / "repos"
        if _docs_repos.exists():
            self._app.router.add_static("/docs/repos", _docs_repos, show_index=True)

    async def _handle_index(self, request: web.Request) -> web.Response:
        html = self.renderer.render_overlay()
        return web.Response(text=html, content_type="text/html")

    async def _handle_avatar_only(self, request: web.Request) -> web.Response:
        avatar_path = Path(__file__).resolve().parent / "avatar.html"
        if not avatar_path.exists():
            return web.Response(status=404, text="avatar.html not found")
        html = avatar_path.read_text(encoding="utf-8")
        return web.Response(text=html, content_type="text/html")

    async def _handle_model_pricing(self, request: web.Request) -> web.Response:
        pricing_path = Path(__file__).resolve().parent.parent / "agent" / "model_pricing.json"
        data = pricing_path.read_text(encoding="utf-8")
        return web.Response(text=data, content_type="application/json")

    async def _handle_cache_font(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            rel_path = data.get("path", "")
            raw = data.get("data", [])
            if not rel_path.startswith("/assets/fonts/") or not raw:
                return web.json_response({"ok": False}, status=400)
            assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
            dest = assets_dir / rel_path.removeprefix("/assets/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes(raw))
            return web.json_response({"ok": True})
        except Exception as exc:
            logger.warning("cache-font failed: %s", exc)
            return web.json_response({"ok": False}, status=500)

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)
        try:
            if self._latest_state:
                await ws.send_json(self._latest_state)
            if self._vtuber_model_idx is not None:
                await ws.send_json({"type": "vtuber_model", "index": self._vtuber_model_idx})
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                    if data.get("type") in ("set_mode", "set_status", "set_config", "change_game", "change_character", "test_key", "set_volume", "avatar_reset_camera", "avatar_freeze", "avatar_config", "avatar_vrma_load", "avatar_vrma_play", "avatar_vrma_stop", "voice_trigger") and self._on_message is not None:
                        if data.get("type") in ("set_config",):
                            self._on_message(data)
                            config = data.get("config", {})
                            vtm = config.get("vtuber_model")
                            if vtm is not None:
                                self._vtuber_model_idx = int(vtm)
                                await self._broadcast_raw({"type": "vtuber_model", "index": self._vtuber_model_idx})
                            avatar_keys = ["eye_tracking", "eye_interval", "lip_sync", "blink_interval", "eye_range", "idle_sway", "sway_strength", "mood_expressions"]
                            avatar_config = {k: config[k] for k in avatar_keys if k in config}
                            if avatar_config:
                                await self._broadcast_raw({"type": "avatar_config", "config": avatar_config})
                        elif data.get("type") in ("avatar_reset_camera", "avatar_freeze", "avatar_config", "avatar_vrma_load", "avatar_vrma_play", "avatar_vrma_stop", "avatar_vrma_mood"):
                            await self._broadcast_raw(data)
                        elif data.get("type") in ("voice_trigger",):
                            self._on_message(data)
                            await self._broadcast_raw(data)
                        else:
                            self._on_message(data)
        except asyncio.CancelledError:
            pass
        finally:
            self._ws_clients.discard(ws)
        return ws

    async def broadcast(self, state_update: dict):
        self._latest_state = state_update
        if not self._ws_clients:
            return
        dead: set[web.WebSocketResponse] = set()
        for ws in set(self._ws_clients):
            try:
                await ws.send_json(state_update)
            except (ConnectionError, asyncio.TimeoutError):
                dead.add(ws)
        self._ws_clients -= dead

    async def _broadcast_raw(self, msg: dict):
        dead: set[web.WebSocketResponse] = set()
        for ws in set(self._ws_clients):
            try:
                await ws.send_json(msg)
            except (ConnectionError, asyncio.TimeoutError):
                dead.add(ws)
        self._ws_clients -= dead

    def push_state(self, state: dict):
        self._latest_state = state

    async def start(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "localhost", self.port)
        await site.start()
        logger.info("Overlay server running on http://localhost:%d", self.port)

    async def stop(self):
        for ws in set(self._ws_clients):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()
