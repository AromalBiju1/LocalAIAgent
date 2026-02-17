"""
ElyssiaAgent CLI Gateway.

Provides command-line management for:
- Initial setup wizard
- Plugin management (list, install, remove)
- Channel management (start, stop, status)
- System status check
"""

import argparse
import asyncio
import logging
import os
import sys
import yaml
from typing import Dict, Any

from src.core.llm_factory import LLMFactory
from src.core.security import validate_path, SecurityError
from src.channels.channel_manager import ChannelManager
from src.plugins.plugin_loader import PluginLoader

# Configure basic logging for CLI
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("elyssia.cli")


class CLIGateway:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="ElyssiaAgent Management CLI",
            usage="elyssia [command] [options]"
        )
        self.subparsers = self.parser.add_subparsers(dest="command", help="Available commands")
        self._setup_parsers()

    def _setup_parsers(self):
        # ── Setup Command ──
        setup_parser = self.subparsers.add_parser("setup", help="Interactive setup wizard")
        
        # ── Plugin Commands ──
        plugin_parser = self.subparsers.add_parser("plugin", help="Manage plugins")
        plugin_subs = plugin_parser.add_subparsers(dest="subcommand")
        
        plugin_subs.add_parser("list", help="List installed plugins")
        
        install_parser = plugin_subs.add_parser("install", help="Install a plugin")
        install_parser.add_argument("path", help="Path to plugin directory or zip file")
        
        remove_parser = plugin_subs.add_parser("remove", help="Remove a plugin (disable)")
        remove_parser.add_argument("name", help="Plugin name")

        # ── Channel Commands ──
        channel_parser = self.subparsers.add_parser("channel", help="Manage communication channels")
        channel_subs = channel_parser.add_subparsers(dest="subcommand")
        
        channel_subs.add_parser("list", help="List configured channels")
        
        start_parser = channel_subs.add_parser("start", help="Start a channel")
        start_parser.add_argument("type", help="Channel type (telegram, discord)")
        
        stop_parser = channel_subs.add_parser("stop", help="Stop a channel")
        stop_parser.add_argument("type", help="Channel type (telegram, discord)")

        # ── Status Command ──
        self.subparsers.add_parser("status", help="Check system health")

    def run(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            return

        try:
            if args.command == "setup":
                self._run_setup()
            elif args.command == "plugin":
                asyncio.run(self._handle_plugin(args))
            elif args.command == "channel":
                self._handle_channel(args)
            elif args.command == "status":
                asyncio.run(self._check_status())
            else:
                self.parser.print_help()
        except KeyboardInterrupt:
            print("\n🛑 Operation cancelled.")
        except Exception as e:
            print(f"\n❌ Error: {e}")

    # ── implementation ───────────────────────────────────

    def _run_setup(self):
        """Interactive setup wizard."""
        print("\n🚀 Welcome to ElyssiaAgent Setup Wizard 🚀\n")
        
        config = {}
        config_path = "config/config.yaml"
        
        if os.path.exists(config_path):
            print(f" found existing config at {config_path}")
            if input(" Create new config? [y/N]: ").lower() != 'y':
                return

        # Model Selection
        print("\n🤖 Model Configuration")
        print("  1. Ollama (Recommended for local)")
        print("  2. OpenAI-Compatible (vLLM, Groq, LM Studio)")
        choice = input(" Choose backend [1]: ") or "1"
        
        if choice == "1":
            config["model"] = {
                "backend": "ollama",
                "name": input("  Model name [qwen3:4b]: ") or "qwen3:4b",
                "base_url": input("  Base URL [http://localhost:11434]: ") or "http://localhost:11434"
            }
        else:
            config["model"] = {
                "backend": "openai",
                "name": input("  Model name: ") or "local-model",
                "openai": {
                    "base_url": input("  API Base URL: ") or "http://localhost:8000/v1",
                    "api_key": input("  API Key [optional]: ") or ""
                }
            }

        # Channels
        print("\n📡 Channel Configuration")
        config["channels"] = {}
        
        if input(" Enable Telegram Bot? [y/N]: ").lower() == 'y':
            token = input("  Telegram Bot Token: ")
            if token:
                config["channels"]["telegram"] = {
                    "enabled": True,
                    "bot_token": token
                }
        
        if input(" Enable Discord Bot? [y/N]: ").lower() == 'y':
            token = input("  Discord Bot Token: ")
            if token:
                config["channels"]["discord"] = {
                    "enabled": True,
                    "bot_token": token
                }

        # Save
        os.makedirs("config", exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print(f"\n✅ Configuration saved to {config_path}")
        print("Run 'python run.py' to start the agent.")

    async def _handle_plugin(self, args):
        loader = PluginLoader()
        
        if args.subcommand == "list":
            discovered = loader.discover()
            print(f"\n🧩 Plugins ({len(discovered)}):")
            for m in discovered:
                print(f"  - {m.name} v{m.version}: {m.description} ({m.author})")
        
        elif args.subcommand == "install":
            path = args.path
            try:
                # Security check
                safe_path = validate_path(path)
                print(f"Installing plugin from {safe_path}...")
                # Logic to copy/install would go here
                print("⚠️  Manual installation needed: Copy folder to 'plugins/community/'")
            except SecurityError as e:
                print(f"⛔ Security Error: {e}")
                
        elif args.subcommand == "remove":
            print(f"To remove, delete the folder in plugins/community/{args.name}")

    def _handle_channel(self, args):
        if args.subcommand == "list":
             # This requires reading config as channels are runtime objects
             print("To see active channels, check 'config/config.yaml' or run the server.")
        elif args.subcommand in ["start", "stop"]:
             print("Channel control is available via the running server API or by editing config.")

    async def _check_status(self):
        print("\n🏥 System Health Check")
        
        # Check LLM
        print("Checking LLM...", end=" ", flush=True)
        try:
            llm = LLMFactory.from_yaml("config/config.yaml")
            if await llm.check_health():
                print("✅ OK")
            else:
                print("❌ Failed")
            await llm.close()
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Check Plugins
        loader = PluginLoader()
        plugins = loader.discover()
        print(f"Plugins available: {len(plugins)}")


def main():
    cli = CLIGateway()
    cli.run()


if __name__ == "__main__":
    main()
