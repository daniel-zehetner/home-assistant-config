"""
Fetch all entities from HA and produce:
  - entities.yaml       : full catalog of entity IDs + friendly names
  - automations/        : skeleton files per domain with real entity IDs
  - configuration.yaml  : updated with actual HA location/timezone
"""
import json, os, urllib.request, urllib.error
from collections import defaultdict

HA_URL = os.environ["HOME_ASSISTANT_URL"].strip().rstrip("/")
HA_KEY = os.environ["HOME_ASSISTANT_API_KEY"].strip()
HEADERS = {"Authorization": f"Bearer {HA_KEY}"}
BASE = os.path.dirname(os.path.abspath(__file__))


def get(path):
    req = urllib.request.Request(f"{HA_URL}{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def q(s):
    """Quote a YAML string if needed."""
    if not s:
        return '""'
    if any(c in s for c in ':#{}[],"\'&*?|<>=!%@`'):
        return f'"{s.replace(chr(34), chr(92)+chr(34))}"'
    if s.lower() in ("true", "false", "null", "yes", "no", "on", "off"):
        return f'"{s}"'
    return s


# ── Fetch data ────────────────────────────────────────────────────────────────
print("Fetching config ...")
cfg = get("/config")
print(f"  {cfg.get('location_name')} | HA {cfg.get('version')} | {cfg.get('time_zone')}")

print("Fetching states ...")
states = get("/states")
print(f"  {len(states)} entities")

# ── Build entity catalog ──────────────────────────────────────────────────────
by_domain = defaultdict(list)
for s in states:
    domain = s["entity_id"].split(".")[0]
    by_domain[domain].append(s)

catalog_path = os.path.join(BASE, "entities.yaml")
with open(catalog_path, "w", encoding="utf-8") as f:
    f.write("# Auto-generated entity catalog — re-run build_config.py to refresh\n\n")
    for domain in sorted(by_domain):
        f.write(f"{domain}:\n")
        for s in sorted(by_domain[domain], key=lambda x: x["entity_id"]):
            eid = s["entity_id"]
            name = s["attributes"].get("friendly_name", eid)
            state = s.get("state", "")
            f.write(f"  - entity_id: {eid}\n")
            f.write(f"    name: {q(name)}\n")
            f.write(f"    state: {q(state)}\n")
        f.write("\n")
print(f"  Wrote {catalog_path}")


# ── Automation skeletons ──────────────────────────────────────────────────────
def entity_list_yaml(entities, indent=6):
    pad = " " * indent
    lines = []
    for s in entities:
        lines.append(f"{pad}- {s['entity_id']}")
    return "\n".join(lines)


def write_automation(filename, automations):
    path = os.path.join(BASE, "automations", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Automations — {filename.replace('.yaml','')}\n")
        f.write("# Generated from live HA entities. Fill in triggers/conditions/actions.\n\n")
        for auto in automations:
            f.write(auto)
            f.write("\n")
    print(f"  Wrote automations/{filename}  ({len(automations)} stubs)")


lights = by_domain.get("light", [])
covers = by_domain.get("cover", [])
climates = by_domain.get("climate", [])
switches = by_domain.get("switch", [])
binary_sensors = by_domain.get("binary_sensor", [])
sensors = by_domain.get("sensor", [])

os.makedirs(os.path.join(BASE, "automations"), exist_ok=True)

# ── Lighting ──────────────────────────────────────────────────────────────────
if lights:
    autos = []
    light_ids = "\n".join(f"          - {s['entity_id']}" for s in lights)
    autos.append(f"""\
- id: lights_on_at_sunset
  alias: Lights on at sunset
  description: Turn on all lights 30 min before sunset
  trigger:
    - platform: sun
      event: sunset
      offset: "-00:30:00"
  condition: []
  action:
    - action: light.turn_on
      target:
        entity_id:
{light_ids}
      data:
        brightness_pct: 80
  mode: single
""")
    autos.append(f"""\
- id: lights_off_at_midnight
  alias: Lights off at midnight
  description: Turn off all lights at midnight
  trigger:
    - platform: time
      at: "00:00:00"
  condition: []
  action:
    - action: light.turn_off
      target:
        entity_id:
{light_ids}
  mode: single
""")
    write_automation("lighting.yaml", autos)

# ── Covers / blinds ───────────────────────────────────────────────────────────
if covers:
    cover_ids = "\n".join(f"          - {s['entity_id']}" for s in covers)
    autos = []
    autos.append(f"""\
- id: covers_open_at_sunrise
  alias: Covers open at sunrise
  description: Open all covers at sunrise
  trigger:
    - platform: sun
      event: sunrise
      offset: "+00:30:00"
  condition: []
  action:
    - action: cover.open_cover
      target:
        entity_id:
{cover_ids}
  mode: single
""")
    autos.append(f"""\
- id: covers_close_at_sunset
  alias: Covers close at sunset
  description: Close all covers at sunset
  trigger:
    - platform: sun
      event: sunset
  condition: []
  action:
    - action: cover.close_cover
      target:
        entity_id:
{cover_ids}
  mode: single
""")
    write_automation("covers.yaml", autos)

# ── Climate ───────────────────────────────────────────────────────────────────
if climates:
    autos = []
    for c in climates:
        eid = c["entity_id"]
        name = c["attributes"].get("friendly_name", eid)
        autos.append(f"""\
- id: {eid.replace('.', '_')}_schedule
  alias: "{name} schedule"
  description: "Set {name} temperature based on time of day"
  trigger:
    - platform: time
      at: "07:00:00"
    - platform: time
      at: "22:00:00"
  condition: []
  action:
    - choose:
        - conditions:
            - condition: time
              after: "07:00:00"
              before: "22:00:00"
          sequence:
            - action: climate.set_temperature
              target:
                entity_id: {eid}
              data:
                temperature: 21
        - conditions:
            - condition: time
              after: "22:00:00"
          sequence:
            - action: climate.set_temperature
              target:
                entity_id: {eid}
              data:
                temperature: 18
  mode: single
""")
    write_automation("climate.yaml", autos)

# ── Presence placeholder ──────────────────────────────────────────────────────
device_trackers = by_domain.get("device_tracker", [])
if device_trackers:
    tracker_ids = "\n".join(f"        - {s['entity_id']}" for s in device_trackers[:5])
    autos = [f"""\
- id: arrived_home
  alias: Arrived home
  description: Actions when someone arrives home
  trigger:
    - platform: state
      entity_id:
{tracker_ids}
      to: home
  condition: []
  action:
    - action: light.turn_on
      target:
        area_id: living_room  # TODO: adjust area
      data:
        brightness_pct: 80
  mode: single

- id: left_home
  alias: Left home
  description: Actions when everyone leaves
  trigger:
    - platform: state
      entity_id:
{tracker_ids}
      to: not_home
  condition:
    - condition: template
      value_template: >
        {{{{ states | selectattr('entity_id', 'in', [
{tracker_ids.replace('        - ', '          "').replace(chr(10), '",' + chr(10))}
        ]) | selectattr('state', 'eq', 'home') | list | count == 0 }}}}
  action: []  # TODO: fill in away actions
  mode: single
"""]
    write_automation("presence.yaml", autos)

# ── Update configuration.yaml with real HA values ────────────────────────────
lat = cfg.get("latitude", 0)
lon = cfg.get("longitude", 0)
elev = cfg.get("elevation", 0)
tz = cfg.get("time_zone", "UTC")
loc_name = cfg.get("location_name", "Home")
currency = cfg.get("currency", "EUR")
country = cfg.get("country", "")
unit = cfg.get("unit_system", {})
unit_name = "metric" if isinstance(unit, dict) and unit.get("length") == "km" else str(unit)

config_path = os.path.join(BASE, "configuration.yaml")
with open(config_path, "w", encoding="utf-8") as f:
    f.write(f"""\
homeassistant:
  name: {q(loc_name)}
  latitude: !secret latitude
  longitude: !secret longitude
  elevation: {elev}
  unit_system: {unit_name}
  currency: {currency}
  country: {country}
  time_zone: {tz}

# Enable the frontend
frontend:

# Enable HTTP
http:

# Enable logging
logger:
  default: warning

# Automations — one file per topic in automations/
automation: !include_dir_merge_list automations/

# Scripts
script: !include_dir_merge_named scripts/

# Scenes
scene: !include_dir_merge_list scenes/
""")
print(f"  Updated configuration.yaml")

# Update secrets.yaml with real lat/lon (gitignored)
secrets_path = os.path.join(BASE, "secrets.yaml")
with open(secrets_path, "w", encoding="utf-8") as f:
    f.write(f"""\
# Sensitive values — gitignored
latitude: {lat}
longitude: {lon}
ha_url: {HA_URL.replace('/api', '')}
""")
print(f"  Updated secrets.yaml")

print("\nDone.")
print(f"  Entities catalog : entities.yaml")
print(f"  Automations      : automations/*.yaml  (stubs — fill in logic)")
print(f"  Scenes           : scenes/scenes.yaml  ({len(by_domain.get('scene',[]))} scenes)")
