# HA Deploy Skill

AI-powered Home Assistant deployment management through Claude Code.

## Usage

```
/ha-deploy [command] [options]
```

## Commands

### deploy
Execute full deployment: validate → commit → push → sync automations.

**Options:**
- `--skip-git` - Skip git commit/push
- `--skip-reload` - Skip reloading automations
- `--verbose` - Show detailed output

**Example:**
```
/ha-deploy deploy
/ha-deploy deploy --skip-git
/ha-deploy deploy --verbose
```

### validate
Validate Home Assistant core configuration without making changes.

**Example:**
```
/ha-deploy validate
```

### push-automations
Push all automations from `automations/` to HA via REST API.

**Example:**
```
/ha-deploy push-automations
```

### push-dashboard
Push an individual dashboard to HA.

**Arguments:**
- `yaml_file` - Path to dashboard YAML (e.g., `dashboards/haussteuerung.yaml`)
- `url_path` - URL path (must contain hyphen, e.g., `haus-steuerung`)
- `title` - Dashboard title
- `--check` - Validate only, no push
- `--icon` - Mdi icon (default: `mdi:home-variant`)

**Example:**
```
/ha-deploy push-dashboard dashboards/haussteuerung.yaml haus-steuerung "Haussteuerung"
/ha-deploy push-dashboard dashboards/bewaesserung.yaml garten-bewaesserung --check
```

### list-dashboards
List all dashboards in the repository with view and card counts.

**Example:**
```
/ha-deploy list-dashboards
```

### status
Show Home Assistant connection status and automation count.

**Example:**
```
/ha-deploy status
```

## Environment

The skill automatically loads configuration from `.env`:
- `HOME_ASSISTANT_URL` - HA base URL with `/api`
- `HOME_ASSISTANT_API_KEY` - Long-lived access token

## Return Values

All commands return:
- **Success** (exit code 0): Operation completed successfully
- **Failure** (exit code 1): Operation failed (details shown in output)

The skill provides:
- ✅ Formatted status messages
- 📊 Progress indicators
- ❌ Clear error reporting
- 📝 Optional verbose output

## Behind the Scenes

The skill uses the unified Python deployment system:
- `deployment.Config` - Configuration management
- `deployment.HAClient` - REST API interactions
- `deployment.AutomationManager` - Automation handling
- `deployment.DashboardManager` - Dashboard management

## Integration with Claude Code

After adding this skill to your Claude Code configuration, you can:

1. **Deploy with confirmation:**
   ```
   I'm going to deploy the changes now.
   /ha-deploy deploy
   ```

2. **Check status before deployment:**
   ```
   Let me verify the connection is working.
   /ha-deploy status

   Now pushing automations.
   /ha-deploy push-automations
   ```

3. **Validate without pushing:**
   ```
   /ha-deploy validate
   ```

4. **Interactive dashboard management:**
   ```
   First, let me list available dashboards.
   /ha-deploy list-dashboards

   Now pushing the kitchen dashboard.
   /ha-deploy push-dashboard dashboards/haussteuerung.yaml haus-steuerung
   ```

## Error Handling

The skill provides clear error messages for:
- Missing `.env` file
- Invalid HA connection
- YAML parsing errors
- Missing dependencies (pyyaml, websockets)
- Git operation failures
- API errors

## Verbose Mode

Use `--verbose` flag to see:
- Individual automation push status
- API response details
- Git operation output
- Module import details
