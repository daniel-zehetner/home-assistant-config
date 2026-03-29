#!/usr/bin/env python3
"""
Home Assistant Deployment Tool

Unified Python-based deployment for automations, dashboards, and config.

Usage:
  python ha_deploy.py [command] [options]

Commands:
  deploy              Full deployment: validate → commit → push → sync automations
  validate            Validate config only (no changes)
  push-automations    Push all automations via REST API
  list-dashboards     List all dashboards
  status              Show HA connection status
  help                Show this help message

Options:
  --skip-git          Don't commit/push to git
  --skip-reload       Don't reload automations after push
  --verbose, -v       Verbose output
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from deployment.automations import AutomationManager
from deployment.config import Config
from deployment.dashboards import DashboardManager
from deployment.ha_client import HAClient


def print_header(text: str):
    """Print formatted header."""
    print(f"\n🚀 {text}")
    print("=" * 50)


def print_status(text: str, success: bool = True):
    """Print status message."""
    symbol = "✅" if success else "❌"
    print(f"{symbol} {text}")


def cmd_deploy(config: Config, client: HAClient, args):
    """Execute full deployment."""
    print_header("Home Assistant Deployment")

    # Step 1: Validate
    print("\n1️⃣  Validating Home Assistant config...")
    result = client.validate_config()

    if result.get("result") != "valid":
        print_status("Validation failed", False)
        print(json.dumps(result, indent=2))
        sys.exit(1)
    print_status("Configuration valid")

    # Step 2: Check for changes
    print("\n2️⃣  Checking git status...")
    git_result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )

    if not git_result.stdout.strip():
        print_status("No changes to commit")
        return

    print(f"   Found {len(git_result.stdout.splitlines())} changed file(s)")

    # Step 3: Commit
    if not args.skip_git:
        print("\n3️⃣  Committing changes...")

        subprocess.run(["git", "add", "-A"], check=True)

        commit_msg = "Deploy: Home Assistant config update\n\nCo-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print_status("Changes committed")
        else:
            print(f"   {result.stdout}")

    # Step 4: Push
    if not args.skip_git:
        print("\n4️⃣  Pushing to remote...")
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print_status("Pushed to GitHub")
        else:
            print(f"   {result.stdout}")

    # Step 5: Push automations
    print("\n5️⃣  Pushing automations via API...")
    manager = AutomationManager(config, client)
    successful, failed = manager.push_all(verbose=args.verbose)
    print_status(f"Pushed {successful} automations" + (f" ({failed} failed)" if failed else ""))

    # Step 6: Reload
    if not args.skip_reload:
        print("\n6️⃣  Reloading automations...")
        client.reload_automations()
        print_status("Automations reloaded")

    print_header("Deployment Complete!")
    print(f"\n✨ All systems synchronized\n")


def cmd_validate(config: Config, client: HAClient, args):
    """Validate configuration only."""
    print_header("Validating Configuration")

    result = client.validate_config()

    if result.get("result") == "valid":
        print_status("Configuration is valid")
        return 0
    else:
        print_status("Validation failed", False)
        print(json.dumps(result, indent=2))
        return 1


def cmd_push_automations(config: Config, client: HAClient, args):
    """Push all automations."""
    print_header("Pushing Automations")

    manager = AutomationManager(config, client)
    successful, failed = manager.push_all(verbose=True)

    print(f"\n📊 Results: {successful} succeeded" + (f", {failed} failed" if failed else ""))

    if not args.skip_reload:
        print("\nReloading automations...")
        client.reload_automations()
        print_status("Reloaded")


def cmd_list_dashboards(config: Config, client: HAClient, args):
    """List all dashboards."""
    print_header("Dashboards")

    manager = DashboardManager(config)
    dashboards = manager.list_dashboards()

    if not dashboards:
        print("No dashboards found")
        return

    for dashboard in dashboards:
        print(f"  • {dashboard.name:30} {dashboard.view_count:2} views, ~{dashboard.card_count:3} cards")


def cmd_status(config: Config, client: HAClient, args):
    """Show HA connection status."""
    print_header("Home Assistant Status")

    print(f"   URL:  {config.ha_url}")
    print(f"   Key:  {config.ha_key[:10]}...")

    result = client.validate_config()

    if result.get("result") == "valid":
        print_status("Connection OK")

        # Get automation count
        states = client.get_states()
        automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]
        print(f"   Automations: {len(automations)} loaded")

    else:
        print_status("Connection failed", False)
        print(f"   {result.get('error', 'Unknown error')}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Home Assistant Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("command", nargs="?", default="deploy", help="Command to execute")
    parser.add_argument("--skip-git", action="store_true", help="Don't commit/push to git")
    parser.add_argument("--skip-reload", action="store_true", help="Don't reload automations")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        config = Config(".env")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    client = HAClient(config)

    commands = {
        "deploy": cmd_deploy,
        "validate": cmd_validate,
        "push-automations": cmd_push_automations,
        "list-dashboards": cmd_list_dashboards,
        "status": cmd_status,
    }

    if args.command == "help" or args.command not in commands:
        parser.print_help()
        sys.exit(0)

    try:
        commands[args.command](config, client, args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
