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
        self._setup_routes()

    def set_message_handler(self, handler):
        self._on_message = handler

    def _setup_routes(self):
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/ws", self._handle_ws)
        self._app.router.add_static(
            "/assets",
            Path(__file__).resolve().parent.parent.parent / "assets",
            show_index=False,
        )

    async def _handle_index(self, request: web.Request) -> web.Response:
        html = self.renderer.render_overlay()
        return web.Response(text=html, content_type="text/html")

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)
        try:
            if self._latest_state:
                await ws.send_json(self._latest_state)
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                    if data.get("type") in ("set_mode", "set_status", "set_config", "change_game") and self._on_message:
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
