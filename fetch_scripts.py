#!/usr/bin/env python3
"""
Fetch all script configs from HA and write them to scripts/ as YAML.

Usage:
  python fetch_scripts.py              # fetch all scripts
  python fetch_scripts.py bewasser     # fetch scripts matching a keyword
"""

import asyncio
import json
import sys
from pathlib import Path

try:
    import websockets
    import yaml
except ImportError:
    print("ERROR: Missing dependency — install it: pip install pyyaml websockets")
    sys.exit(1)

from deployment.config import Config


async def fetch_scripts(keyword: str = ""):
    config = Config()
    ws_url = config.ws_url

    print(f"Connecting to {ws_url} ...")
    ws = await websockets.connect(ws_url)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": config.ha_key}))
    auth = json.loads(await ws.recv())
    if auth.get("type") != "auth_ok":
        raise RuntimeError(f"Auth failed: {auth}")
    print(f"Connected (HA {auth.get('ha_version', '?')})")

    mid = [0]

    async def request(payload):
        mid[0] += 1
        payload["id"] = mid[0]
        await ws.send(json.dumps(payload))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == mid[0]:
                return msg

    # Get all script entity IDs from states
    states_resp = await request({"type": "get_states"})
    all_states = states_resp.get("result", [])
    script_ids = [
        s["entity_id"].replace("script.", "")
        for s in all_states
        if s["entity_id"].startswith("script.")
        and (not keyword or keyword.lower() in s["entity_id"].lower())
    ]

    print(f"Found {len(script_ids)} script(s) matching '{keyword or '*'}'")

    # Fetch full config for each script
    scripts = {}
    for script_id in sorted(script_ids):
        resp = await request({"type": "script/config", "entity_id": f"script.{script_id}"})
        if resp.get("success"):
            config_data = resp.get("result", {})
            scripts[script_id] = config_data
            print(f"  fetched: {script_id}")
        else:
            print(f"  WARN: could not fetch {script_id}: {resp.get('error')}")

    await ws.close()
    return scripts


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else ""
    scripts = asyncio.run(fetch_scripts(keyword))

    if not scripts:
        print("No scripts fetched.")
        return

    # Group by filename heuristic
    # All bewaesserung/bewasserung scripts → scripts/bewaesserung.yaml
    # Everything else → scripts/other.yaml (or separate files)
    groups: dict[str, dict] = {}
    for script_id, config_data in scripts.items():
        if "bewaesser" in script_id or "bewasser" in script_id:
            groups.setdefault("bewaesserung", {})[script_id] = config_data
        else:
            groups.setdefault("other", {})[script_id] = config_data

    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)

    for group, data in groups.items():
        out_path = scripts_dir / f"{group}.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=True)
        print(f"\nWrote {len(data)} script(s) to {out_path}")

    if "other" in groups:
        print(f"\nNOTE: {len(groups['other'])} non-irrigation script(s) written to scripts/other.yaml")
        print("Review and split into appropriate files as needed.")


if __name__ == "__main__":
    main()
