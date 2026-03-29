# HA Deployment System

Unified Python-based deployment and management tools for Home Assistant configuration.

## Overview

The deployment system provides:
- **Centralized configuration** via `deployment.config.Config`
- **HA API client** for REST and WebSocket interactions
- **Automation management** via REST API
- **Dashboard management** with validation and pushing
- **CLI tools** for common operations

## Quick Start

### Full deployment

```bash
python3 ha_deploy.py deploy
```

This validates config, commits changes to git, pushes to remote, and syncs automations via API.

### Validate only

```bash
python3 ha_deploy.py validate
```

### Push dashboards

```bash
python3 push_dashboard.py dashboards/haussteuerung.yaml haus-steuerung "Haussteuerung"
python3 push_dashboard.py dashboards/bewaesserung.yaml garten-bewaesserung --check
```

### Check status

```bash
python3 ha_deploy.py status
```

## Module Structure

### `deployment/config.py`

**`Config` class** — loads and manages environment/configuration.

```python
from deployment.config import Config

config = Config(".env")
print(config.ha_url)              # HTTP URL
print(config.ws_url)              # WebSocket URL
print(config.automations_dir)     # Path to automations/
```

### `deployment/ha_client.py`

**`HAClient` class** — REST API interactions with HA.

```python
from deployment.config import Config
from deployment.ha_client import HAClient

config = Config(".env")
client = HAClient(config)

# Validate core config
result = client.validate_config()  # Returns {result: "valid", ...}

# Get all entity states
states = client.get_states()       # Returns list of state dicts

# Push single automation
client.push_automation(auto_id, auto_config)  # Returns bool

# Reload automations
client.reload_automations()        # Returns dict
```

### `deployment/automations.py`

**`AutomationManager` class** — load and push automations from YAML files.

```python
from deployment.config import Config
from deployment.ha_client import HAClient
from deployment.automations import AutomationManager

config = Config(".env")
client = HAClient(config)
manager = AutomationManager(config, client)

# Load all automations from files
automations = manager.load_from_files()  # Returns [(id, config), ...]

# Push all to HA
successful, failed = manager.push_all()  # Returns (int, int)
```

### `deployment/dashboards.py`

**`Dashboard` class** — represents a dashboard configuration.

**`DashboardManager` class** — list and manage dashboards.

```python
from deployment.config import Config
from deployment.dashboards import DashboardManager, Dashboard

config = Config(".env")
manager = DashboardManager(config)

# List all dashboards
dashboards = manager.list_dashboards()  # Returns [Dashboard, ...]

# Find specific dashboard
dashboard = manager.find_dashboard("haussteuerung")
print(dashboard.title)       # "Haussteuerung"
print(dashboard.view_count)  # 6
print(dashboard.card_count)  # ~103
```

## Usage Examples

### Deploy everything

```bash
python3 ha_deploy.py deploy
```

Workflow:
1. Validate HA core config
2. Commit changes to git
3. Push to GitHub
4. Push all automations via REST API
5. Reload automations in HA

### Custom Python script

```python
#!/usr/bin/env python3
from deployment.config import Config
from deployment.ha_client import HAClient
from deployment.automations import AutomationManager

config = Config(".env")
client = HAClient(config)
manager = AutomationManager(config, client)

# Validate first
result = client.validate_config()
if result.get("result") != "valid":
    print("Config invalid!")
    exit(1)

# Push automations
successful, failed = manager.push_all(verbose=True)
print(f"Pushed {successful} automations, {failed} failed")
```

### Using HAClient directly

```python
from deployment.config import Config
from deployment.ha_client import HAClient
import json

config = Config(".env")
client = HAClient(config)

# Get all states
states = client.get_states()

# Find all automations
automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]
print(f"Loaded {len(automations)} automations")

# Check specific automation
for auto in automations:
    if "dishwasher" in auto["entity_id"]:
        print(json.dumps(auto, indent=2))
```

## Environment Setup

The system reads from `.env` file (gitignored):

```env
HOME_ASSISTANT_URL=http://192.168.178.159:8123/api
HOME_ASSISTANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

- `HOME_ASSISTANT_URL` — base URL with `/api` suffix
- `HOME_ASSISTANT_API_KEY` — long-lived access token from HA profile page

## Dependencies

```bash
pip install pyyaml websockets
```

- `pyyaml` — for YAML parsing (automations, dashboards)
- `websockets` — for WebSocket API (dashboards)

## CLI Commands

### `ha_deploy.py`

```bash
python3 ha_deploy.py [command] [options]

Commands:
  deploy              Full deployment (validate, commit, push, sync)
  validate            Validate config only
  push-automations    Push automations via REST API
  list-dashboards     List all dashboards
  status              Show HA connection status

Options:
  --skip-git          Don't commit/push to git
  --skip-reload       Don't reload automations
  -v, --verbose       Verbose output
```

### `push_dashboard.py`

```bash
python3 push_dashboard.py <yaml_file> <url_path> [title] [options]

Arguments:
  yaml_file           Path to dashboard YAML
  url_path            URL path (must contain hyphen)
  title               Dashboard title (default: derived from filename)

Options:
  --check             Validate only, no push
  --icon ICON         Mdi icon (default: mdi:home-variant)
```

## Architecture

```
deployment/
├── __init__.py          # Package marker
├── config.py            # Configuration loading
├── ha_client.py         # REST API client
├── automations.py       # Automation management
└── dashboards.py        # Dashboard management

ha_deploy.py             # Main CLI tool
push_dashboard.py        # Dashboard push tool (refactored)
deploy.sh               # Deprecated — use ha_deploy.py instead
```

## Migrating from old scripts

**Old way:**
```bash
export $(grep -v '^#' .env | ...) && \
  python3 push_dashboard.py dashboards/foo.yaml foo-url "Title"
```

**New way:**
```bash
python3 push_dashboard.py dashboards/foo.yaml foo-url "Title"
```

The script now handles `.env` loading internally via `deployment.Config`.

## Notes

- All scripts load `.env` automatically — no need for manual `export` commands
- The REST API for automations is internal/undocumented but stable
- WebSocket API requires `websockets` library for dashboard operations
- Configuration paths are automatically derived from repo structure
