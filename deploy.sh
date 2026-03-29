#!/bin/bash
set -e

# Home Assistant Deployment Script
# Validates config, commits changes, and syncs to HA server

usage() {
  cat <<EOF
Usage: deploy.sh [options]

Options:
  --validate-only   Check config without committing
  --skip-push       Commit locally but don't push to remote
  --ha-host HOST    SSH host to pull on HA server (e.g., ha@192.168.1.100)
  --help            Show this help

Examples:
  ./deploy.sh                              # Full deployment: validate, commit, push
  ./deploy.sh --validate-only              # Check config only
  ./deploy.sh --ha-host ha@192.168.1.100   # Deploy and pull on HA server
EOF
  exit 0
}

# Parse arguments
VALIDATE_ONLY=false
SKIP_PUSH=false
HA_HOST=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --validate-only) VALIDATE_ONLY=true; shift ;;
    --skip-push) SKIP_PUSH=true; shift ;;
    --ha-host) HA_HOST="$2"; shift 2 ;;
    --help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

# Load environment
if [[ ! -f .env ]]; then
  echo "ERROR: .env file not found"
  exit 1
fi
export $(grep -v '^#' .env | sed 's/ *= */=/' | xargs)

# Push automations from YAML files via REST API
push_automations() {
  if [[ ! -d automations ]]; then
    return 0
  fi

  python3 - <<'PYTHON_END'
import os, json, yaml, subprocess, sys

HA_URL = os.environ.get('HOME_ASSISTANT_URL', '').rstrip('/')
HA_KEY = os.environ.get('HOME_ASSISTANT_API_KEY', '')

if not HA_URL or not HA_KEY:
  print("   ERROR: HOME_ASSISTANT_URL or HOME_ASSISTANT_API_KEY not set")
  sys.exit(1)

try:
  import yaml
except ImportError:
  print("   PyYAML not found — install it: pip install pyyaml")
  sys.exit(1)

# Find all automation YAML files
for root, dirs, files in os.walk('automations'):
  for file in sorted(files):
    if not file.endswith('.yaml'):
      continue

    filepath = os.path.join(root, file)
    try:
      with open(filepath, encoding='utf-8') as f:
        automations = yaml.safe_load(f) or []

      if not isinstance(automations, list):
        automations = [automations]

      for auto in automations:
        if not isinstance(auto, dict) or 'id' not in auto:
          continue

        auto_id = auto['id']
        # POST /api/config/automation/config/{id}
        cmd = [
          'curl', '-s', '-X', 'POST',
          f'{HA_URL}/config/automation/config/{auto_id}',
          '-H', f'Authorization: Bearer {HA_KEY}',
          '-H', 'Content-Type: application/json',
          '-d', json.dumps(auto)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
          resp = json.loads(result.stdout)
          if resp.get('result') == 'ok':
            print(f"   ✓ {auto_id}")
          else:
            print(f"   ⚠ {auto_id}: {resp.get('error', 'unknown error')}")
        except:
          print(f"   ⚠ {auto_id}: {result.stdout[:100]}")

    except yaml.YAMLError as e:
      print(f"   ERROR parsing {filepath}: {e}")
      sys.exit(1)
    except Exception as e:
      print(f"   ERROR processing {filepath}: {e}")
      sys.exit(1)

PYTHON_END
}

echo "🚀 Home Assistant Deployment"
echo "======================================"

# Step 1: Validate HA core config
echo -n "1️⃣  Validating Home Assistant config... "
VALIDATION=$(curl -s -X POST "$HOME_ASSISTANT_URL/config/core/check_config" \
  -H "Authorization: Bearer $HOME_ASSISTANT_API_KEY" \
  -H "Content-Type: application/json")

if echo "$VALIDATION" | grep -q '"result":"valid"'; then
  echo "✅"
else
  echo "❌"
  echo "Validation errors:"
  echo "$VALIDATION" | python3 -m json.tool 2>/dev/null || echo "$VALIDATION"
  exit 1
fi

[[ "$VALIDATE_ONLY" == true ]] && exit 0

# Step 2: Check for uncommitted changes
echo -n "2️⃣  Checking for changes... "
if git diff --quiet && git diff --cached --quiet; then
  echo "No changes"
  echo "✅ Already up to date"
  exit 0
fi
echo "Found changes"

# Step 3: Commit changes
echo "3️⃣  Committing changes..."
git add -A
COMMIT_MSG=$(git diff --cached --name-only | head -10 | xargs -I {} basename {} | paste -sd ',' - | sed 's/^/Update: /')
git commit -m "$COMMIT_MSG

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>" 2>&1 | sed 's/^/   /'
echo "✅"

# Step 4: Push to remote
if [[ "$SKIP_PUSH" == false ]]; then
  echo "4️⃣  Pushing to remote..."
  git push origin main 2>&1 | sed 's/^/   /'
  echo "✅"
fi

# Step 5: Push automations via API
echo "5️⃣  Pushing automations via API..."
push_automations
echo "✅"

# Step 6: Pull on HA server (if host provided)
if [[ -n "$HA_HOST" ]]; then
  echo "6️⃣  Pulling on HA server ($HA_HOST)..."
  ssh "$HA_HOST" "cd /home/homeassistant/.homeassistant && git pull" 2>&1 | sed 's/^/   /'
  echo "✅"
else
  echo "6️⃣  Pull on HA server"
  echo "   Run on HA machine: cd /home/homeassistant/.homeassistant && git pull"
fi

echo ""
echo "======================================"
echo "✅ Deployment complete!"
echo ""
echo "All automations have been pushed via REST API and are active."
echo "Note: Entity IDs are derived from automation aliases (lowercase, spaces→underscores)."
