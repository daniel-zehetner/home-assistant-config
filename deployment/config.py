"""Configuration and environment management."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Load and manage HA configuration."""

    def __init__(self, env_file: str = ".env"):
        """Initialize config from .env file."""
        self.env_file = Path(env_file)
        self.ha_url = ""
        self.ha_key = ""
        self.repo_root = Path.cwd()

        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file."""
        if not self.env_file.exists():
            raise FileNotFoundError(f".env file not found at {self.env_file}")

        with open(self.env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()

                    if key == "HOME_ASSISTANT_URL":
                        self.ha_url = val.rstrip("/")
                    elif key == "HOME_ASSISTANT_API_KEY":
                        self.ha_key = val

        if not self.ha_url or not self.ha_key:
            raise ValueError("HOME_ASSISTANT_URL and HOME_ASSISTANT_API_KEY must be set in .env")

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL from HTTP URL."""
        return (
            self.ha_url.replace("http://", "ws://")
            .replace("https://", "wss://")
            .replace("/api", "")
            + "/api/websocket"
        )

    @property
    def automations_dir(self) -> Path:
        """Get automations directory."""
        return self.repo_root / "automations"

    @property
    def dashboards_dir(self) -> Path:
        """Get dashboards directory."""
        return self.repo_root / "dashboards"

    @property
    def scripts_dir(self) -> Path:
        """Get scripts directory."""
        return self.repo_root / "scripts"

    def __repr__(self) -> str:
        return f"Config(ha_url={self.ha_url}, automations_dir={self.automations_dir})"
