# Claude Code Skills

Custom skills and agents for Home Assistant configuration management.

## Available Skills

### ha-deploy

Unified deployment management for Home Assistant automations, dashboards, and configuration.

**Quick Commands:**

```bash
# Full deployment
/ha-deploy deploy

# Validate configuration
/ha-deploy validate

# Push automations
/ha-deploy push-automations

# Check status
/ha-deploy status

# List dashboards
/ha-deploy list-dashboards

# Push dashboard
/ha-deploy push-dashboard dashboards/haussteuerung.yaml haus-steuerung "Haussteuerung"
```

**Documentation:** See `skills/ha-deploy.md`

## Installation

### Method 1: Claude Code VSCode Extension

1. Open your Home Assistant config workspace in VSCode
2. Go to Claude Code settings
3. Add the skill from `.claude/skills/ha-deploy.yaml`

### Method 2: Claude Code CLI

```bash
claude code setup-skill ./.claude/skills/ha-deploy.yaml
```

### Method 3: Manual Registration

Add to your Claude Code configuration:

```yaml
skills:
  - name: ha-deploy
    path: ./.claude/skills/ha-deploy.yaml
    enabled: true
```

## Using Skills

### Interactive Deployment

```
I want to deploy the kitchen automation and dashboard changes.

/ha-deploy validate

Now pushing the changes.

/ha-deploy deploy --verbose
```

### Dashboard Management

```
Let me check which dashboards exist.

/ha-deploy list-dashboards

Now I'll push the updated housekeeping dashboard.

/ha-deploy push-dashboard dashboards/haussteuerung.yaml haus-steuerung "Haussteuerung"
```

### Safe Validation

```
Before deploying, let me validate the configuration.

/ha-deploy validate

Let me check the connection status.

/ha-deploy status
```

## Environment Setup

Skills require `.env` file in repo root:

```env
HOME_ASSISTANT_URL=http://192.168.178.159:8123/api
HOME_ASSISTANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Dependencies

Skills automatically handle dependencies via Python:

```bash
pip install pyyaml websockets
```

## Development

To modify skills:

1. Edit `skills/ha-deploy.yaml` or `skills/ha-deploy.md`
2. Reload Claude Code configuration
3. Test with `/ha-deploy [command]`

To add new skills:

1. Create `skills/skill-name.yaml` with command definitions
2. Create `skills/skill-name.md` with documentation
3. Register in Claude Code settings

## Troubleshooting

### Skill not found

Ensure `.claude/skills/` directory exists:

```bash
mkdir -p .claude/skills
```

### Command fails with "Python not found"

Ensure Python 3 is in PATH:

```bash
python3 --version
```

### Missing dependencies

Install required packages:

```bash
pip install pyyaml websockets
```

### Authentication errors

Check `.env` file:
- `HOME_ASSISTANT_URL` must end with `/api`
- `HOME_ASSISTANT_API_KEY` must be valid long-lived token
- File must not be gitignored (local only)

## Advanced Usage

### Custom Scripts

Import deployment modules in your own scripts:

```python
from deployment.skill import HASkill

skill = HASkill()
skill.deploy(skip_git=True)
skill.push_automations()
```

### Integration with Workflows

```bash
#!/bin/bash
# Deploy workflow

/ha-deploy validate || exit 1
/ha-deploy deploy --verbose
/ha-deploy status
```

## Examples

See `skills/ha-deploy.yaml` for full command examples and parameters.

## API Reference

### HASkill Class

```python
from deployment.skill import HASkill

skill = HASkill()

# Methods
skill.deploy(skip_git=False, skip_reload=False, verbose=False) -> bool
skill.validate() -> bool
skill.push_automations(verbose=True) -> bool
skill.push_dashboard(yaml_file, url_path, title, icon, check_only=False) -> bool
skill.list_dashboards() -> bool
skill.status() -> bool
```

## Support

For issues or feature requests, check:
- `DEPLOYMENT.md` - System documentation
- `CLAUDE.md` - Project guidelines
- `skills/ha-deploy.md` - Skill reference
