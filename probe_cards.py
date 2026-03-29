"""Push a minimal test dashboard to check which card types work with cover entities."""
import asyncio, json, os
import websockets

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()
WS_URL = HA_URL.replace("http://", "ws://").replace("/api", "") + "/api/websocket"

TEST_COVER = "cover.knx_interface_rollo_bad"  # simplest cover — one rollo

TEST_CONFIG = {
    "title": "Card Test",
    "views": [{
        "title": "Test",
        "cards": [
            {"type": "tile",     "entity": TEST_COVER, "name": "tile card"},
            {"type": "entities", "entities": [{"entity": TEST_COVER, "name": "entities card"}]},
            {"type": "button",   "entity": TEST_COVER, "name": "button card"},
            {"type": "entity",   "entity": TEST_COVER, "name": "entity card"},
        ]
    }]
}

async def main():
    mid = 0
    async def send(ws, p):
        nonlocal mid; mid += 1; p["id"] = mid
        await ws.send(json.dumps(p))
        while True:
            d = json.loads(await ws.recv())
            if d.get("id") == mid: return d

    async with websockets.connect(WS_URL) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": HA_KEY}))
        await ws.recv()
        r = await send(ws, {"type": "lovelace/config/save", "url_path": "licht-rollos", "config": TEST_CONFIG})
        print("saved:", r.get("success"), r.get("error", ""))

asyncio.run(main())
