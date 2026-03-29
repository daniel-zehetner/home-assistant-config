"""Check entity states and units via HA REST API."""
import json, os, sys
import urllib.request

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()

req = urllib.request.Request(
    f"{HA_URL}/states",
    headers={"Authorization": f"Bearer {HA_KEY}"}
)
with urllib.request.urlopen(req) as r:
    states = json.loads(r.read())

search = sys.argv[1] if len(sys.argv) > 1 else "kwh"

for s in states:
    attrs = s.get("attributes", {})
    unit = attrs.get("unit_of_measurement", "")
    eid = s["entity_id"]
    state = s["state"]
    if search.lower() in eid.lower() or search.lower() in unit.lower():
        print(f"{eid}  |  {state} {unit}")
