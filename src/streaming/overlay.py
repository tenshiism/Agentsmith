from pathlib import Path

_HTML_PATH = Path(__file__).resolve().parent / "overlay.html"
OVERLAY_HTML = _HTML_PATH.read_text(encoding="utf-8")


class OverlayRenderer:
    def __init__(self, config: dict):
        self.config = config

    def render_overlay(self) -> str:
        return OVERLAY_HTML
