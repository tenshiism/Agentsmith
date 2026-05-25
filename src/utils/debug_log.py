import os
import datetime
import time
from pathlib import Path

_log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
_start_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
_MAX_BYTES = 10 * 1024 * 1024


def _prune():
    if not _log_dir.exists():
        return
    files = sorted(_log_dir.iterdir(), key=lambda f: f.stat().st_mtime)
    total = sum(f.stat().st_size for f in files if f.is_file())
    while total > _MAX_BYTES and len(files) > 2:
        oldest = files.pop(0)
        total -= oldest.stat().st_size
        oldest.unlink()


def _append(filename: str, text: str):
    _log_dir.mkdir(parents=True, exist_ok=True)
    path = _log_dir / filename
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    _prune()


def log(text: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _append(f"log_{_start_ts}.txt", f"[{ts}] {text}")
    print(text)


_last_screenshot: str | None = None


def save_screenshot(img_bytes: bytes) -> str:
    _log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    fname = f"screen_{ts}.jpg"
    path = _log_dir / fname
    path.write_bytes(img_bytes)
    global _last_screenshot
    _last_screenshot = fname
    _prune()
    return fname


def log_call(call_type: str, frame: int, messages: list, response: str, parsed: str, duration: float):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    lines = [f"=== {call_type} === [{ts}] [frame {frame}] [{duration:.1f}s]"]
    if _last_screenshot:
        lines.append(f"[screenshot: {_last_screenshot}]")
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "text":
                        parts.append(c["text"])
                    elif c.get("type") == "image_url":
                        parts.append("[IMAGE: " + c["image_url"]["url"] + "]")
            content = "\n".join(parts)
        lines.append(f"--- {role} ---")
        lines.append(content)
    lines.append(f"--- RESPONSE ---")
    lines.append(response)
    lines.append(f"--- PARSED ---")
    lines.append(parsed)
    _append(f"calls_{_start_ts}.log", "\n".join(lines))
