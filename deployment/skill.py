#!/usr/bin/env python3
"""HA Deployment Skill - Unified deployment interface."""

import sys
from .config import Config
from .ha_client import HAClient
from .automations import AutomationManager
from .dashboards import DashboardManager


class HASkill:
    """Unified HA deployment skill."""

    def __init__(self):
        """Initialize skill."""
        try:
            self.config = Config(".env")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ ERROR: {e}")
            sys.exit(1)

        self.client = HAClient(self.config)
        self.auto_manager = AutomationManager(self.config, self.client)
        self.dash_manager = DashboardManager(self.config)

    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n🚀 {text}")
        print("=" * 60)

    def print_status(self, text: str, success: bool = True):
        """Print status message."""
        symbol = "✅" if success else "❌"
        print(f"{symbol} {text}")

    def deploy(self, skip_git: bool = False, skip_reload: bool = False, verbose: bool = False) -> bool:
        """Execute full deployment."""
        self.print_header("Full Deployment")
        print("\n1️⃣  Validating configuration...")
        result = self.client.validate_config()

        if result.get("result") != "valid":
            self.print_status("Validation failed", False)
            return False

        self.print_status("Configuration valid")

        if not skip_git:
            print("\n2️⃣  Git operations...")
            import subprocess

            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                check=False,
            )

            if status.stdout.strip():
                subprocess.run(["git", "add", "-A"], check=False)
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        "Deploy: HA config\n\nCo-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>",
                    ],
                    capture_output=True,
                    check=False,
                )
                subprocess.run(["git", "push", "origin", "main"], capture_output=True, check=False)
                self.print_status("Committed and pushed")
            else:
                print("   No changes")

        print("\n3️⃣  Pushing automations via REST API...")
        successful, failed = self.auto_manager.push_all(verbose=verbose)
        self.print_status(f"Pushed {successful} automations" + (f" ({failed} failed)" if failed else ""))

        if not skip_reload:
            print("\n4️⃣  Reloading automations...")
            self.client.reload_automations()
            self.print_status("Reloaded")

        self.print_header("Deployment Complete!")
        return True

    def validate(self) -> bool:
        """Validate configuration only."""
        self.print_header("Configuration Validation")
        result = self.client.validate_config()

        if result.get("result") == "valid":
            self.print_status("Configuration is valid")
            return True
        else:
            self.print_status("Validation failed", False)
            return False

    def push_automations(self, verbose: bool = True) -> bool:
        """Push all automations."""
        self.print_header("Pushing Automations")
        successful, failed = self.auto_manager.push_all(verbose=verbose)
        print(f"\n📊 Results: {successful} succeeded" + (f", {failed} failed" if failed else ""))
        self.client.reload_automations()
        self.print_status("Reloaded")
        return failed == 0

    def list_dashboards(self) -> bool:
        """List all dashboards."""
        self.print_header("Dashboards")
        dashboards = self.dash_manager.list_dashboards()

        if not dashboards:
            print("No dashboards found")
            return True

        for dashboard in dashboards:
            print(
                f"  • {dashboard.name:30} {dashboard.view_count:2} views, ~{dashboard.card_count:3} cards"
            )
        return True

    def status(self) -> bool:
        """Show HA connection status."""
        self.print_header("Home Assistant Status")
        print(f"   URL:  {self.config.ha_url}")
        print(f"   Key:  {self.config.ha_key[:10]}...")

        result = self.client.validate_config()

        if result.get("result") == "valid":
            self.print_status("Connection OK")
            states = self.client.get_states()
            automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]
            print(f"   Automations: {len(automations)} loaded")
            return True
        else:
            self.print_status("Connection failed", False)
            return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Home Assistant Deployment Skill")
    parser.add_argument("command", nargs="?", default="deploy")
    parser.add_argument("--skip-git", action="store_true")
    parser.add_argument("--skip-reload", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    skill = HASkill()

    commands = {
        "deploy": lambda: skill.deploy(
            skip_git=args.skip_git, skip_reload=args.skip_reload, verbose=args.verbose
        ),
        "validate": skill.validate,
        "push-automations": lambda: skill.push_automations(verbose=args.verbose),
        "list-dashboards": skill.list_dashboards,
        "status": skill.status,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(1)

    try:
        success = commands[args.command]()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
