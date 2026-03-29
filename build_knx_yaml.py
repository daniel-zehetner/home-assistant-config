"""
Build KNX YAML config files from the ETS project export.
Maps group addresses by name to HA KNX entity config.
Writes files to knx/ directory.
"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "_knx_knx_get_knx_project.json")) as f:
    project = json.load(f)

gas = project["group_addresses"]  # addr -> {name, dpt}

# Index by name for lookup
by_name = {v["name"]: k for k, v in gas.items()}


def ga(name):
    """Return group address for an ETS name, or None."""
    return by_name.get(name)


os.makedirs(os.path.join(BASE, "knx"), exist_ok=True)


# ── Covers ────────────────────────────────────────────────────────────────────
covers = [
    # (entity name, lang_name, kurz_name, status_name, hoehe_name)
    ("Rollo Büro vorne",          "Rollo Büro vorne lang",             "Rollo Büro vorne kurz",            "Rollo Büro vorne status",          "Rollo Büro Vorne Höhe"),
    ("Rollo Büro seitlich",       "Rollo Büro seitlich lang",          "Rollo Büro seitlich kurz",         "Rollo Büro seitlich status",       "Rollo Büro seitlich Höhe"),
    ("Rollo WZ seitlich",         "Rollo WZ seitlich lang",            "Rollo WZ seitlich kurz",           "Rollo WZ seitlich status",         "Rollo WZ seitlich Höhe"),
    ("Rollo WZ hinten",           "Rollo WZ hinten lang",              "Rollo WZ hinten kurz",             "Rollo WZ hinten status",           "Rollo WZ hinten Höhe"),
    ("Rollo WZ alle",             "Rollo WZ alle lang",                "Rollo WZ alle kurz",               "Rollo WZ alle status",             None),
    ("Rollo WZ Ausgang",          "Rollo WZ Ausgang lang",             "Rollo WZ Ausgang kurz",            "Rollo WZ Ausgang status",          None),
    ("Rollo Hebeschiebe links",   "Rollo Hebeschiebe links lang",      "Rollo Hebeschiebe links kurz",     "Rollo Hebeschiebe links status",   "Rollo Hebeschiebe links Höhe"),
    ("Rollo Hebeschiebe rechts",  "Rollo Hebeschiebe rechts lang",     "Rollo Hebeschiebe rechts kurz",    "Rollo Hebeschiebe rechts status",  "Rollo Hebeschiebe rechts Höhe"),
    ("Rollo Küche",               "Rollo Küche lang",                  "Rollo Küche kurz",                 "Rollo Küche status",               "Rollo Küche Höhe"),
    ("Rollo KZ aussen seitlich",  "Rollo KZ aussen seitlich lang",    "Rollo KZ aussen seitlich kurz",    "Rollo KZ aussen seitlich status",  "Rollo KZ aussen seitlich Höhe"),
    ("Rollo KZ aussen hinten",    "Rollo KZ aussen hinten lang",      "Rollo KZ aussen hinten kurz",      "Rollo KZ aussen hinten status",    "Rollo KZ aussen hinten Höhe"),
    ("Rollo KZ mitte",            "Rollo KZ mitte lang",               "Rollo KZ mitte kurz",              "Rollo KZ mitte status",            "Rollo KZ mitte Höhe"),
    ("Rollo Schlafzimmer",        "Rollo Schlafzimmer lang",           "Rollo Schlafzimmer kurz",          "Rollo Schlafzimmer status",        "Rollo Schlafzimmer Höhe"),
    ("Rollo Bad",                 "Rollo Bad lang",                    "Rollo Bad kurz",                   "Rollo Bad status",                 "Rollo Bad Höhe"),
    ("Rollo Gang",                "Rollo Gang lang",                   "Rollo Gang kurz",                  "Rollo Flur status",                "Rollo Gang Höhe"),
]

cover_lines = ["# KNX covers (Rollos) — auto-generated from ETS project\n"]
for name, lang, kurz, status, hoehe in covers:
    lang_addr   = ga(lang)
    kurz_addr   = ga(kurz)
    status_addr = ga(status)
    hoehe_addr  = ga(hoehe)
    cover_lines.append(f'- name: "{name}"')
    if lang_addr:
        cover_lines.append(f'  move_long_address: "{lang_addr}"')
    if kurz_addr:
        cover_lines.append(f'  move_short_address: "{kurz_addr}"')
    if hoehe_addr:
        cover_lines.append(f'  position_address: "{hoehe_addr}"')
    if status_addr:
        cover_lines.append(f'  position_state_address: "{status_addr}"')
    cover_lines.append(f'  travelling_time_down: 30  # TODO: measure actual travel time')
    cover_lines.append(f'  travelling_time_up: 30    # TODO: measure actual travel time')
    cover_lines.append("")

cover_path = os.path.join(BASE, "knx", "covers.yaml")
with open(cover_path, "w", encoding="utf-8") as f:
    f.write("\n".join(cover_lines))
print(f"Wrote knx/covers.yaml  ({len(covers)} covers)")


# ── Lights ────────────────────────────────────────────────────────────────────
lights = [
    # (entity name,              switch_name,                  status_name)
    ("Schalten Licht Terasse",  "Schalten Licht Terasse",    "Licht Terasse Status"),
    ("Schalten Licht Poolrand", "Schalten Licht Poolrand",   "Licht Poolrand Status"),
    ("Schalten Licht Pool",     "Schalten Licht Pool",       "Licht Pool Status"),
    ("Schalten Licht Weg",      "Schalten Licht Weg",        "Licht Weg Status"),
    ("Licht Terasse",           "Licht Terasse Schalten",    "Licht Terasse Status"),
    ("Licht Abstellraum",       "Licht Abstellraum Schalten", None),
    ("Licht Nebenraum",         "Licht Nebenraum Schalten",  "Licht Nebenraum Status"),
]

light_lines = ["# KNX lights — auto-generated from ETS project\n"]
for name, switch, status in lights:
    addr      = ga(switch)
    state_addr = ga(status)
    light_lines.append(f'- name: "{name}"')
    if addr:
        light_lines.append(f'  address: "{addr}"')
    if state_addr:
        light_lines.append(f'  state_address: "{state_addr}"')
    light_lines.append("")

light_path = os.path.join(BASE, "knx", "lights.yaml")
with open(light_path, "w", encoding="utf-8") as f:
    f.write("\n".join(light_lines))
print(f"Wrote knx/lights.yaml  ({len(lights)} lights)")


# ── Sensors (temperature) ─────────────────────────────────────────────────────
sensors = [
    ("Temperatur Wohnesszimmer", "Temperatur Innen Wohnesszimmer", "temperature"),
    ("Temperatur Schlafzimmer",  "Temperatur Innen Schlafzimmer",  "temperature"),
    ("Temperatur Abstellraum",   "Temperatur Innen Abstellraum",   "temperature"),
]

sensor_lines = ["# KNX sensors — auto-generated from ETS project\n"]
for name, ga_name, typ in sensors:
    addr = ga(ga_name)
    sensor_lines.append(f'- name: "{name}"')
    if addr:
        sensor_lines.append(f'  state_address: "{addr}"')
    sensor_lines.append(f'  type: {typ}')
    sensor_lines.append(f'  state_class: measurement')
    sensor_lines.append(f'  sync_state: every 60')
    sensor_lines.append("")

sensor_path = os.path.join(BASE, "knx", "sensors.yaml")
with open(sensor_path, "w", encoding="utf-8") as f:
    f.write("\n".join(sensor_lines))
print(f"Wrote knx/sensors.yaml  ({len(sensors)} sensors)")


# ── Binary sensors ────────────────────────────────────────────────────────────
binary_sensors = [
    ("Tor Status",  "Status Tor",  "garage_door"),
]
# Irrigation valve statuses
for i, name in enumerate([
    "Status Ventil 1", "Status Ventil 2", "Status Ventil 3", "Status Ventil 4",
    "Status Ventil 5", "Status Ventil 6", "Status Ventil 7", "Status Ventil 8",
]):
    binary_sensors.append((f"Bewässerung Ventil {i+1} Status", name, None))

bs_lines = ["# KNX binary sensors — auto-generated from ETS project\n"]
for name, ga_name, device_class in binary_sensors:
    addr = ga(ga_name)
    bs_lines.append(f'- name: "{name}"')
    if addr:
        bs_lines.append(f'  state_address: "{addr}"')
    if device_class:
        bs_lines.append(f'  device_class: {device_class}')
    bs_lines.append("")

bs_path = os.path.join(BASE, "knx", "binary_sensors.yaml")
with open(bs_path, "w", encoding="utf-8") as f:
    f.write("\n".join(bs_lines))
print(f"Wrote knx/binary_sensors.yaml  ({len(binary_sensors)} binary sensors)")


# ── Switches (gate + irrigation valves) ──────────────────────────────────────
switches = [
    ("Tor",                             "Tor schalten",                       "garage"),
    ("Bewässerung alle Kreise",         "Schalten - alle Kreise",             None),
    ("Bewässerung Haus Vorne",          "Schalten Ventil Haus Vorne",         None),
    ("Bewässerung Terasse Links",       "Schalten Ventil Terasse Links",      None),
    ("Bewässerung Terasse Rechts",      "Schalten Ventil Terasse Rechts",     None),
    ("Bewässerung Links Mitte",         "Schalten Ventil Links Mitte",        None),
    ("Bewässerung Links Hinten",        "Schalten Ventil Links Hinten",       None),
    ("Bewässerung Garage Vorne",        "Schalten Ventil Garage Vorne",       None),
    ("Bewässerung Garage Seitlich",     "Schalten Ventil Garage Seitlich",    None),
    ("Bewässerung Rechts Hinten",       "Schalten Ventil Rechts Hinten",      None),
]

switch_lines = ["# KNX switches — auto-generated from ETS project\n"]
for name, ga_name, device_class in switches:
    addr = ga(ga_name)
    switch_lines.append(f'- name: "{name}"')
    if addr:
        switch_lines.append(f'  address: "{addr}"')
    if device_class:
        switch_lines.append(f'  device_class: {device_class}')
    switch_lines.append("")

switch_path = os.path.join(BASE, "knx", "switches.yaml")
with open(switch_path, "w", encoding="utf-8") as f:
    f.write("\n".join(switch_lines))
print(f"Wrote knx/switches.yaml  ({len(switches)} switches)")


# ── Climate ───────────────────────────────────────────────────────────────────
# Only temperature read-back available; setpoint GAs not in ETS export
climates = [
    ("Wohnesszimmer", "Temperatur Innen Wohnesszimmer"),
    ("Schlafzimmer",  "Temperatur Innen Schlafzimmer"),
    ("Abstellraum",   "Temperatur Innen Abstellraum"),
]

climate_lines = [
    "# KNX climate — auto-generated from ETS project",
    "# NOTE: only temperature_address found in ETS project.",
    "# Add target_temperature_address / operation_mode_address if available.\n",
]
for name, temp_ga in climates:
    addr = ga(temp_ga)
    climate_lines.append(f'- name: "{name}"')
    if addr:
        climate_lines.append(f'  temperature_address: "{addr}"')
    climate_lines.append(f'  # target_temperature_address: "TODO"')
    climate_lines.append(f'  # operation_mode_address: "TODO"')
    climate_lines.append(f'  min_temp: 15')
    climate_lines.append(f'  max_temp: 30')
    climate_lines.append("")

climate_path = os.path.join(BASE, "knx", "climate.yaml")
with open(climate_path, "w", encoding="utf-8") as f:
    f.write("\n".join(climate_lines))
print(f"Wrote knx/climate.yaml  ({len(climates)} climate entities)")


# ── Main knx.yaml ─────────────────────────────────────────────────────────────
knx_main = """\
# KNX integration configuration
# Connection is auto-discovered; override here if needed:
# connection_type: tunneling
# host: 192.168.178.x
# port: 3671

light:     !include knx/lights.yaml
cover:     !include knx/covers.yaml
switch:    !include knx/switches.yaml
binary_sensor: !include knx/binary_sensors.yaml
sensor:    !include knx/sensors.yaml
climate:   !include knx/climate.yaml
"""
knx_main_path = os.path.join(BASE, "knx.yaml")
with open(knx_main_path, "w", encoding="utf-8") as f:
    f.write(knx_main)
print(f"Wrote knx.yaml  (top-level include file)")


# ── Patch configuration.yaml ──────────────────────────────────────────────────
cfg_path = os.path.join(BASE, "configuration.yaml")
with open(cfg_path) as f:
    cfg = f.read()

if "knx:" not in cfg:
    cfg = cfg.rstrip() + "\n\n# KNX integration\nknx: !include knx.yaml\n"
    with open(cfg_path, "w") as f:
        f.write(cfg)
    print("Patched configuration.yaml  (added knx: !include knx.yaml)")
else:
    print("configuration.yaml already has knx: — skipped")

print("\nDone.")
