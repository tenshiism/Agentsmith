import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class OBSIntegration:
    def __init__(self, config: dict):
        self.enabled = config.get("streaming", {}).get("obs_enabled", False)
        self.host = config.get("streaming", {}).get("obs_host", "localhost")
        self.port = config.get("streaming", {}).get("obs_port", 4455)
        self.password = config.get("streaming", {}).get("obs_password", "")
        overlay_port = config.get("streaming", {}).get("overlay_port", 8765)
        self.overlay_url = f"http://localhost:{overlay_port}/"

    def generate_browser_source_config(self) -> dict:
        return {
            "type": "browser_source",
            "settings": {
                "url": self.overlay_url,
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "shutdown": False,
                "restart_when_active": True,
            },
        }

    def save_scene_collection(self, output_path: str):
        if not self.enabled:
            logger.info("OBS integration disabled, skipping scene config")
            return
        config = {
            "sources": [
                {
                    "name": "AgentSmith Game Capture",
                    "type": "game_capture",
                    "settings": {
                        "capture_mode": "window",
                        "window": "AgentSmith",
                    },
                },
                {
                    "name": "AgentSmith Overlay",
                    **self.generate_browser_source_config(),
                },
            ],
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2))
        logger.info("OBS scene config saved to %s", output_path)

    def switch_to_scene(self, scene_name: str = "AgentSmith"):
        if not self.enabled:
            return
        try:
            import obsws_python as obs

            client = obs.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
            )
            client.set_current_program_scene(scene_name)
            logger.info("Switched OBS to scene '%s'", scene_name)
        except ImportError:
            logger.warning("obsws_python not installed. Cannot switch scenes.")
        except Exception as e:
            logger.warning("Failed to switch OBS scene: %s", e)
