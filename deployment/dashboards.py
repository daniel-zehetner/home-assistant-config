"""Dashboard management for Home Assistant."""

from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not found — install it: pip install pyyaml")
    exit(1)

from .config import Config


class Dashboard:
    """Represents a dashboard configuration."""

    def __init__(self, path: Path):
        """Load dashboard from YAML file."""
        self.path = path
        self.name = path.stem

        with open(path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

    @property
    def url_path(self) -> Optional[str]:
        """Extract url_path from dashboard metadata."""
        # Can be specified in comments or derived from filename
        return self.config.get("url_path") or self.name.replace("_", "-")

    @property
    def title(self) -> str:
        """Get dashboard title."""
        return self.config.get("title", self.name)

    @property
    def view_count(self) -> int:
        """Count views in dashboard."""
        return len(self.config.get("views", []))

    @property
    def card_count(self) -> int:
        """Count all cards recursively."""
        total = 0
        for view in self.config.get("views", []):
            for card in view.get("cards", []):
                total += 1
                # Count nested cards (grid, vertical-stack, etc.)
                for sub in card.get("cards", []):
                    total += 1
                    for subsub in sub.get("cards", []):
                        total += 1
        return total

    def __repr__(self) -> str:
        return f"Dashboard({self.name}, views={self.view_count}, cards=~{self.card_count})"


class DashboardManager:
    """Manage dashboards."""

    def __init__(self, config: Config):
        """Initialize dashboard manager."""
        self.config = config

    def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards in repo."""
        dashboards = []

        if not self.config.dashboards_dir.exists():
            return dashboards

        for yaml_file in sorted(self.config.dashboards_dir.glob("*.yaml")):
            try:
                dashboards.append(Dashboard(yaml_file))
            except Exception as e:
                print(f"ERROR loading {yaml_file}: {e}")

        return dashboards

    def find_dashboard(self, name: str) -> Optional[Dashboard]:
        """Find dashboard by name."""
        for dashboard in self.list_dashboards():
            if dashboard.name == name or dashboard.name.replace("-", "_") == name:
                return dashboard
        return None
