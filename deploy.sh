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

# Step 5: Reload automations
echo "5️⃣  Reloading automations..."
curl -s -X POST "$HOME_ASSISTANT_URL/services/automation/reload" \
  -H "Authorization: Bearer $HOME_ASSISTANT_API_KEY" \
  -H "Content-Type: application/json" > /dev/null
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
echo "Verify in HA:"
echo "  • Automations → dishwasher_finished_notification should be active"
echo "  • Developer Tools → States → search 'automation.dishwasher'"
