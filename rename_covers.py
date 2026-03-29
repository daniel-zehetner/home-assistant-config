"""
Rename cover entities in HA entity registry to drop the 'Rollo' prefix.
Uses WebSocket config/entity_registry/update.
"""
import asyncio, json, os
import websockets

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()
WS_URL = HA_URL.replace("http://", "ws://").replace("/api", "") + "/api/websocket"

# entity_id -> new friendly name
RENAMES = {
    "cover.knx_interface":                          "Büro vorne",
    "cover.rollo_buro_seitlich_lang":               "Büro seitlich",
    "cover.rollo_wz_seitlich_lang":                 "WZ seitlich",
    "cover.knx_interface_rollo_wz_hinten_lang":     "WZ hinten",
    "cover.knx_interface_rollo_wz_ausgang_lang":    "WZ Ausgang",
    "cover.knx_interface_rollo_wz_alle_lang":       "WZ alle",
    "cover.knx_interface_rollo_hebeschiebe_links_lang":  "Hebeschiebe links",
    "cover.knx_interface_rollo_hebeschiebe_rechts": "Hebeschiebe rechts",
    "cover.knx_interface_rollo_kuche":              "Küche",
    "cover.knx_interface_rollo_schlafzimmer":       "Schlafzimmer",
    "cover.knx_interface_rollo_gang":               "Gang",
    "cover.knx_interface_rollo_kz_aussen":          "KZ außen seitlich",
    "cover.knx_interface_rollo_kz_aussen_hinten":   "KZ außen hinten",
    "cover.knx_interface_rollo_kz_mitte":           "KZ mitte",
    "cover.knx_interface_rollo_bad":                "Bad",
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

        for entity_id, new_name in RENAMES.items():
            r = await send(ws, {
                "type": "config/entity_registry/update",
                "entity_id": entity_id,
                "name": new_name,
            })
            if r.get("success"):
                print(f"  OK  {entity_id}  →  '{new_name}'")
            else:
                print(f"  ERR {entity_id}: {r.get('error')}")

asyncio.run(main())
