"""Home Assistant REST and WebSocket API client."""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict

from .config import Config


class HAClient:
    """Client for Home Assistant API interactions."""

    def __init__(self, config: Config):
        """Initialize HA client."""
        self.config = config

    def validate_config(self) -> Dict[str, Any]:
        """Validate HA core configuration."""
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{self.config.ha_url}/config/core/check_config",
            "-H",
            f"Authorization: Bearer {self.config.ha_key}",
            "-H",
            "Content-Type: application/json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": f"Invalid response: {result.stdout}"}

    def reload_automations(self) -> Dict[str, Any]:
        """Reload automations service."""
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{self.config.ha_url}/services/automation/reload",
            "-H",
            f"Authorization: Bearer {self.config.ha_key}",
            "-H",
            "Content-Type: application/json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        try:
            return json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            if result.stderr:
                print(f"WARNING: reload failed: {result.stderr.strip()}", file=sys.stderr)
            return {}

    def get_states(self) -> list:
        """Get all entity states from HA."""
        cmd = [
            "curl",
            "-s",
            f"{self.config.ha_url}/states",
            "-H",
            f"Authorization: Bearer {self.config.ha_key}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            if result.stderr:
                print(f"WARNING: get_states failed: {result.stderr.strip()}", file=sys.stderr)
            return []

    def push_automation(self, automation_id: str, automation_config: Dict[str, Any]) -> bool:
        """Push single automation to HA via REST API."""
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{self.config.ha_url}/config/automation/config/{automation_id}",
            "-H",
            f"Authorization: Bearer {self.config.ha_key}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(automation_config),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        try:
            resp = json.loads(result.stdout)
            return resp.get("result") == "ok"
        except json.JSONDecodeError:
            return False
