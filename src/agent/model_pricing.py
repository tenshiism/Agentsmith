import json
from pathlib import Path

_data = json.loads(Path(__file__).with_suffix(".json").read_text())
MODEL_PRICING = _data["pricing"]
