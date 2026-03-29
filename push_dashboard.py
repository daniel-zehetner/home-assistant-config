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
import asyncio, json, os, sys
import websockets

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()
WS_URL = HA_URL.replace("http://", "ws://").replace("/api", "") + "/api/websocket"


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        print("PyYAML not found — install it: pip install pyyaml")
        sys.exit(1)
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            print(f"ERROR: {path} does not parse to a YAML mapping.")
            sys.exit(1)
        return data
    except Exception as e:
        print(f"YAML parse error in {path}:\n  {e}")
        sys.exit(1)


def count_cards(views):
    """Recursively count all card objects in a views list."""
    total = 0
    for view in (views or []):
        for card in view.get("cards", []):
            total += 1
            # count nested cards (grid, vertical-stack, etc.)
            for sub in card.get("cards", []):
                total += 1
                for subsub in sub.get("cards", []):
                    total += 1
    return total


def summarise(config):
    views = config.get("views", [])
    return {
        "title": config.get("title", "—"),
        "views": len(views),
        "view_titles": [v.get("title", "?") for v in views],
        "cards": count_cards(views),
    }


async def ws_connect():
    ws = await websockets.connect(WS_URL)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": HA_KEY}))
    auth = json.loads(await ws.recv())
    if auth.get("type") != "auth_ok":
        print(f"Auth failed: {auth}")
        sys.exit(1)
    return ws, auth.get("ha_version", "?")


async def ws_send(ws, mid_ref, payload):
    mid_ref[0] += 1
    payload["id"] = mid_ref[0]
    await ws.send(json.dumps(payload))
    while True:
        d = json.loads(await ws.recv())
        if d.get("id") == mid_ref[0]:
            return d


async def check(yaml_path, url_path):
    """Validate locally and diff against live HA config."""
    print(f"Validating {yaml_path} ...")
    local = load_yaml(yaml_path)
    print(f"  YAML syntax OK")

    local_s = summarise(local)
    print(f"  Local  : title='{local_s['title']}', {local_s['views']} views "
          f"({', '.join(local_s['view_titles'])}), ~{local_s['cards']} cards")

    ws, version = await ws_connect()
    mid = [0]
    print(f"  Connected to HA {version}")

    resp = await ws_send(ws, mid, {"type": "lovelace/config", "url_path": url_path})
    await ws.close()

    if not resp.get("success"):
        print(f"  Live   : no config found at /{url_path} (will be created on push)")
        return

    live_s = summarise(resp["result"])
    print(f"  Live   : title='{live_s['title']}', {live_s['views']} views "
          f"({', '.join(live_s['view_titles'])}), ~{live_s['cards']} cards")

    if local_s == live_s:
        print("  No structural changes detected.")
    else:
        if local_s["views"] != live_s["views"]:
            print(f"  Views  : {live_s['views']} → {local_s['views']}")
        if local_s["cards"] != live_s["cards"]:
            print(f"  Cards  : ~{live_s['cards']} → ~{local_s['cards']}")
        if local_s["title"] != live_s["title"]:
            print(f"  Title  : '{live_s['title']}' → '{local_s['title']}'")

    print("\nCheck passed — run without --check to push.")


async def push(yaml_path, url_path, title, icon="mdi:home-variant"):
    config = load_yaml(yaml_path)
    ws, version = await ws_connect()
    mid = [0]
    print(f"Connected to HA {version}")

    dashboard_id = None

    resp = await ws_send(ws, mid, {
        "type": "lovelace/dashboards/create",
        "url_path": url_path,
        "title": title,
        "icon": icon,
        "show_in_sidebar": True,
        "require_admin": False,
        "mode": "storage",
    })
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
        resp = await ws_send(ws, mid, {
            "type": "lovelace/dashboards/update",
            "dashboard_id": dashboard_id,
            "title": title,
            "icon": icon,
            "show_in_sidebar": True,
            "require_admin": False,
        })
        if not resp.get("success"):
            print(f"WARNING: could not update dashboard metadata: {resp.get('error')}")
        else:
            print(f"Updated title/icon for /{url_path}")

    resp = await ws_send(ws, mid, {
        "type": "lovelace/config/save",
        "url_path": url_path,
        "config": config,
    })
    await ws.close()

    if resp.get("success"):
        print(f"Config saved successfully.")
        print(f"\nDashboard available at: {HA_URL.replace('/api', '')}/{url_path}")
    else:
        print(f"ERROR saving config: {resp.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else "dashboards/bewaesserung.yaml"
    url_path  = sys.argv[2] if len(sys.argv) > 2 else "bewaesserung"

    if len(sys.argv) > 3 and sys.argv[3] == "--check":
        asyncio.run(check(yaml_path, url_path))
    else:
        title = sys.argv[3] if len(sys.argv) > 3 else "Bewässerung"
        icon  = sys.argv[4] if len(sys.argv) > 4 else "mdi:home-variant"
        asyncio.run(push(yaml_path, url_path, title, icon))
