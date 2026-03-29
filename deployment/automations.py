"""Automation management for Home Assistant."""

from pathlib import Path
from typing import List, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not found — install it: pip install pyyaml")
    exit(1)

from .config import Config
from .ha_client import HAClient


class AutomationManager:
    """Manage automations in Home Assistant."""

    def __init__(self, config: Config, client: HAClient):
        """Initialize automation manager."""
        self.config = config
        self.client = client

    def load_from_files(self) -> List[Tuple[str, dict]]:
        """Load all automations from YAML files.

        Returns:
            List of tuples (automation_id, automation_config)
        """
        automations = []

        if not self.config.automations_dir.exists():
            return automations

        for yaml_file in sorted(self.config.automations_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []

                if not isinstance(data, list):
                    data = [data]

                for auto in data:
                    if not isinstance(auto, dict) or "id" not in auto:
                        continue

                    automations.append((auto["id"], auto))

            except yaml.YAMLError as e:
                print(f"ERROR parsing {yaml_file}: {e}")
                exit(1)

        return automations

    def push_all(self, verbose: bool = True) -> Tuple[int, int]:
        """Push all automations to HA.

        Returns:
            Tuple of (successful, failed) count
        """
        automations = self.load_from_files()

        if not automations:
            if verbose:
                print("   No automations to push")
            return 0, 0

        successful = 0
        failed = 0

        for auto_id, auto_config in automations:
            if self.client.push_automation(auto_id, auto_config):
                if verbose:
                    print(f"   ✓ {auto_id}")
                successful += 1
            else:
                if verbose:
                    print(f"   ⚠ {auto_id}: failed")
                failed += 1

        return successful, failed
