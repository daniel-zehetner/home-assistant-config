#!/usr/bin/env python3
"""
Push a local dashboard YAML file to Home Assistant via WebSocket API.

Usage:
  python push_dashboard.py <yaml_file> <url_path> <title> [icon]
  python push_dashboard.py <yaml_file> <url_path> --check      # validate only, no push

--check mode:
  1. Validates YAML syntax locally
  2. Fetches live config from HA and shows a summary diff (views count, card count)
  No changes are made to HA.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

try:
    import websockets
    import yaml
except ImportError as e:
    print(f"ERROR: Missing dependency — install it: pip install pyyaml websockets")
    sys.exit(1)

from deployment.config import Config


class DashboardPusher:
    """Push dashboards to HA via WebSocket API."""

    def __init__(self, config: Config):
        """Initialize pusher."""
        self.config = config
        self.ws_url = config.ws_url
        self.ha_key = config.ha_key
        self.ha_base_url = config.ha_url.replace("/api", "")

    async def connect(self):
        """Connect and authenticate to HA WebSocket."""
        ws = await websockets.connect(self.ws_url)
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": self.ha_key}))
        auth = json.loads(await ws.recv())

        if auth.get("type") != "auth_ok":
            raise RuntimeError(f"Auth failed: {auth}")

        version = auth.get("ha_version", "?")
        return ws, version

    async def send_request(self, ws, mid_ref, payload):
        """Send WebSocket request and wait for response."""
        mid_ref[0] += 1
        payload["id"] = mid_ref[0]
        await ws.send(json.dumps(payload))

        while True:
            response = json.loads(await ws.recv())
            if response.get("id") == mid_ref[0]:
                return response

    def load_dashboard(self, path: str) -> dict:
        """Load dashboard YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError(f"{path} does not parse to a YAML mapping")

            return data
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parse error in {path}: {e}")

    def summarize_dashboard(self, config: dict) -> dict:
        """Create summary of dashboard structure."""
        views = config.get("views", [])
        cards = self._count_cards(views)

        return {
            "title": config.get("title", "—"),
            "views": len(views),
            "view_titles": [v.get("title", "?") for v in views],
            "cards": cards,
        }

    @staticmethod
    def _count_cards(views):
        """Recursively count all cards."""
        total = 0
        for view in views or []:
            for card in view.get("cards", []):
                total += 1
                for sub in card.get("cards", []):
                    total += 1
                    for subsub in sub.get("cards", []):
                        total += 1
        return total

    async def check(self, yaml_path: str, url_path: str):
        """Validate dashboard locally and show diff with live version."""
        print(f"Validating {yaml_path} ...")

        try:
            local = self.load_dashboard(yaml_path)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

        print("  ✓ YAML syntax OK")

        local_s = self.summarize_dashboard(local)
        print(
            f"  Local  : title='{local_s['title']}', {local_s['views']} views "
            f"({', '.join(local_s['view_titles'])}), ~{local_s['cards']} cards"
        )

        ws, version = await self.connect()
        mid = [0]
        print(f"  Connected to HA {version}")

        resp = await self.send_request(ws, mid, {"type": "lovelace/config", "url_path": url_path})
        await ws.close()

        if not resp.get("success"):
            print(f"  Live   : no config found at /{url_path} (will be created on push)")
            return

        live_s = self.summarize_dashboard(resp["result"])
        print(
            f"  Live   : title='{live_s['title']}', {live_s['views']} views "
            f"({', '.join(live_s['view_titles'])}), ~{live_s['cards']} cards"
        )

        if local_s == live_s:
            print("  ✓ No structural changes detected")
        else:
            if local_s["views"] != live_s["views"]:
                print(f"  Views  : {live_s['views']} → {local_s['views']}")
            if local_s["cards"] != live_s["cards"]:
                print(f"  Cards  : ~{live_s['cards']} → ~{local_s['cards']}")
            if local_s["title"] != live_s["title"]:
                print(f"  Title  : '{live_s['title']}' → '{local_s['title']}'")

        print("\n✅ Check passed — run without --check to push.")

    async def push(self, yaml_path: str, url_path: str, title: str, icon: str = "mdi:home-variant"):
        """Push dashboard to HA."""
        try:
            config = self.load_dashboard(yaml_path)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

        ws, version = await self.connect()
        mid = [0]
        print(f"Connected to HA {version}")

        # Create or update dashboard
        dashboard_id = None

        resp = await self.send_request(
            ws,
            mid,
            {
                "type": "lovelace/dashboards/create",
                "url_path": url_path,
                "title": title,
                "icon": icon,
                "show_in_sidebar": True,
                "require_admin": False,
                "mode": "storage",
            },
        )

        if resp.get("success"):
            dashboard_id = resp.get("result", {}).get("id")
            print(f"Created dashboard '{title}' at /{url_path}")
        else:
            err_key = resp.get("error", {}).get("translation_key", "")
            if err_key != "url_already_exists":
                print(f"ERROR creating dashboard: {resp.get('error')}")
                await ws.close()
                sys.exit(1)

        if dashboard_id:
            resp = await self.send_request(
                ws,
                mid,
                {
                    "type": "lovelace/dashboards/update",
                    "dashboard_id": dashboard_id,
                    "title": title,
                    "icon": icon,
                    "show_in_sidebar": True,
                    "require_admin": False,
                },
            )
            if not resp.get("success"):
                print(f"WARNING: could not update dashboard metadata: {resp.get('error')}")
            else:
                print(f"Updated title/icon for /{url_path}")

        # Save config
        resp = await self.send_request(
            ws,
            mid,
            {
                "type": "lovelace/config/save",
                "url_path": url_path,
                "config": config,
            },
        )
        await ws.close()

        if resp.get("success"):
            print("Config saved successfully.")
            print(f"\n✅ Dashboard available at: {self.ha_base_url}/{url_path}")
        else:
            print(f"ERROR saving config: {resp.get('error')}")
            sys.exit(1)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Push Home Assistant dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("yaml_file", nargs="?", default="dashboards/bewaesserung.yaml")
    parser.add_argument("url_path", nargs="?", default="bewaesserung")
    parser.add_argument("title", nargs="?", default="Bewässerung")
    parser.add_argument("--check", action="store_true", help="Validate only, no push")
    parser.add_argument("--icon", default="mdi:home-variant", help="Dashboard icon")

    args = parser.parse_args()

    try:
        config = Config(".env")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    pusher = DashboardPusher(config)

    try:
        if args.check:
            await pusher.check(args.yaml_file, args.url_path)
        else:
            await pusher.push(args.yaml_file, args.url_path, args.title, args.icon)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
