"""
Export Lovelace dashboards from Home Assistant via WebSocket API.
Produces dashboards/<slug>.yaml for each dashboard.
"""
import asyncio, json, os, re, sys
import websockets

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()
WS_URL = HA_URL.replace("http://", "ws://").replace("https://", "wss://").replace("/api", "") + "/api/websocket"
BASE   = os.path.dirname(os.path.abspath(__file__))


def to_yaml(obj, indent=0):
    pad = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for k, v in obj.items():
            rendered = to_yaml(v, indent + 1)
            if rendered.startswith("\n"):
                lines.append(f"{pad}{k}:{rendered}")
            else:
                lines.append(f"{pad}{k}: {rendered}")
        return "\n" + "\n".join(lines)
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for item in obj:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    rendered = to_yaml(v, indent + 2)
                    prefix = f"{pad}  - {k}" if first else f"{pad}    {k}"
                    first = False
                    if rendered.startswith("\n"):
                        lines.append(f"{prefix}:{rendered}")
                    else:
                        lines.append(f"{prefix}: {rendered}")
            else:
                rendered = to_yaml(item, indent + 1)
                lines.append(f"{pad}  - {rendered.lstrip()}")
        return "\n" + "\n".join(lines)
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    elif isinstance(obj, str):
        if "\n" in obj:
            escaped = obj.replace("\n", f"\n{pad}  ")
            return f"|\n{pad}  {escaped}"
        if any(c in obj for c in ':#{}[],"\'&*?|<>=!%@`') or obj.lower() in (
            "true", "false", "null", "yes", "no", "on", "off"
        ) or obj == "":
            return f'"{obj.replace(chr(34), chr(92)+chr(34))}"'
        return obj
    else:
        return str(obj)


async def fetch():
    msg_id = 0

    async def send(ws, payload):
        nonlocal msg_id
        msg_id += 1
        payload["id"] = msg_id
        await ws.send(json.dumps(payload))
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                return data

    print(f"Connecting to {WS_URL} ...")
    async with websockets.connect(WS_URL) as ws:
        # Handshake
        hello = json.loads(await ws.recv())
        print(f"  HA {hello.get('ha_version', '?')}")

        # Authenticate
        await ws.send(json.dumps({"type": "auth", "access_token": HA_KEY}))
        auth_resp = json.loads(await ws.recv())
        if auth_resp.get("type") != "auth_ok":
            print(f"ERROR: Auth failed: {auth_resp}")
            sys.exit(1)
        print("  Authenticated")

        # List all dashboards
        resp = await send(ws, {"type": "lovelace/dashboards"})
        dashboards = resp.get("result", [])

        # Always include the default dashboard (url_path = None)
        default_entry = {"url_path": None, "title": "Default", "mode": "?"}
        all_dashboards = [default_entry] + [d for d in dashboards if d.get("url_path")]

        print(f"  Found {len(all_dashboards)} dashboard(s): default + {len(dashboards)} custom")

        os.makedirs(os.path.join(BASE, "dashboards"), exist_ok=True)

        for db in all_dashboards:
            url_path = db.get("url_path")
            title    = db.get("title", url_path or "default")
            slug     = re.sub(r"[^a-z0-9]+", "_", (url_path or "default").lower()).strip("_")

            print(f"\n  Fetching '{title}' (/{url_path or 'lovelace'}) ...")
            payload = {"type": "lovelace/config", "force": False}
            if url_path:
                payload["url_path"] = url_path

            resp = await send(ws, payload)

            if not resp.get("success"):
                print(f"    Skipped — {resp.get('error', {}).get('message', 'unknown error')}")
                continue

            config = resp["result"]
            mode = config.get("strategy") and "strategy" or ("views" in config and "yaml" or "storage")

            out_path = os.path.join(BASE, "dashboards", f"{slug}.yaml")
            rendered = to_yaml(config).lstrip("\n")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# Dashboard: {title}\n")
                f.write(f"# url_path: {url_path or '(default)'}\n\n")
                f.write(rendered)
                f.write("\n")
            print(f"    Saved → dashboards/{slug}.yaml")

    print("\nDone.")


asyncio.run(fetch())
