import os
import datetime
from pathlib import Path

_log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
_log_file = None


def _ensure_log():
    global _log_file
    if _log_file is not None:
        return
    _log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = _log_dir / f"agent_{ts}.log"
    _append("=== AgentSmith Debug Log ===")
    _append(f"Started at {datetime.datetime.now().isoformat()}")
    print(f"[DebugLog] Writing to {_log_file}")


def _append(text: str):
    with open(_log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def to_console(text: str):
    print(text)


def log_call(call_type: str, frame: int, messages: list, response: str, parsed: str, duration: float):
    _ensure_log()
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    lines = [
        f"\n[{ts}] === {call_type} (frame {frame}) === [{duration:.1f}s]",
    ]
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
                        parts.append("[IMAGE: " + c["image_url"]["url"][:60] + "...]")
            content = "\n".join(parts)
        lines.append(f"  [{role}] {content[:2000]}")
    lines.append(f"  [RESPONSE] {response[:500]}")
    lines.append(f"  [PARSED] {parsed}")
    text = "\n".join(lines)
    _append(text)
    print(text)
