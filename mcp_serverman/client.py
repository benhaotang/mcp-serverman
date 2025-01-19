#!/usr/bin/env python3
# This is the file for client controls with ClientManager class
import json
import re
from pathlib import Path
import platform
import click
from rich.console import Console
from rich.table import Table
from typing import Optional

from .config import BaseConfigManager, ClaudeConfigManager

console = Console()

class ClientManager:
    """Manages configuration for multiple clients"""
    def __init__(self):
        self.system = platform.system()
        self.config_dir = self._get_config_dir()
        self.clients_file = self.config_dir / "clients.json"
        self.global_registry = self.config_dir / "mcp-global-registry.json"

    def _get_config_dir(self) -> Path:
        """Get the configuration directory based on OS."""
        if self.system == "Linux":
            return Path.home() / ".config" / "mcp-serverman"
        elif self.system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "mcp-serverman"
        elif self.system == "Windows":
            return Path.home() / "mcp-serverman"
        else:
            raise NotImplementedError(f"Unsupported operating system: {self.system}")

    def initialize(self):
        """Initialize client configuration."""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize global registry if it doesn't exist
        if not self.global_registry.exists():
            self._create_global_registry()
        elif click.confirm("Global registry already exists. Do you want to overwrite it?"):
            self._create_global_registry()

        # Initialize clients file if it doesn't exist
        if not self.clients_file.exists():
            self._create_clients_file()
        elif click.confirm("Clients file already exists. Do you want to overwrite it?"):
            self._create_clients_file()
    
    def list_clients(self):
        """List all registered clients."""
        if not self.clients_file.exists():
            raise click.ClickException("Clients file not found. Please run 'mcp-serverman client init' first.")

        with open(self.clients_file) as f:
            clients = json.load(f)

        table = Table(title="MCP Server Clients")
        table.add_column("Short Name")
        table.add_column("Name")
        table.add_column("Config Path")
        table.add_column("Servers Key")
        table.add_column("Status")

        for short_name, info in sorted(clients.items()):
            config_path = Path(info["config_path"])
            path_exists = config_path.exists()
            
            table.add_row(
                short_name,
                info["name"],
                str(info["config_path"]),
                info["servers_key"],
                "[green]default[/green]" if info["is_default"] else (
                    "[yellow]system[/yellow]" if short_name == "system" else (
                        "[red]invalid path[/red]" if not path_exists else ""
                    )
                )
            )

        console.print(table)

    def _create_global_registry(self):
        """Create a new global registry file with empty mcpServers."""
        with open(self.global_registry, 'w') as f:
            json.dump({"mcpServers": {}}, f, indent=2)
        click.echo(f"Created global registry at {self.global_registry}")

    def _create_clients_file(self):
        """Create a new clients file with default entries."""
        clients = {
            "claude": {
                "name": "Claude Desktop",
                "short_name": "claude",
                "config_path": str(ClaudeConfigManager()._get_config_path()),
                "servers_key": "mcpServers",
                "is_default": 1
            },
            "system": {
                "name": "System Global Registry",
                "short_name": "system",
                "config_path": str(self.global_registry),
                "servers_key": "mcpServers",
                "is_default": 0
            }
        }
        with open(self.clients_file, 'w') as f:
            json.dump(clients, f, indent=2)
        click.echo(f"Created clients file at {self.clients_file}")

    def validate_short_name(self, short_name: str) -> bool:
        """Validate if a short name is valid for CLI usage."""
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', short_name))

    def get_client(self, short_name: Optional[str] = None) -> BaseConfigManager:
        """Get a config manager instance for a specific client. Also handles vaildation check for global config."""
        # Check if client configuration is initialized
        if not self.clients_file.exists() or not self.global_registry.exists():
            raise click.ClickException(
                "Client configuration not initialized. Please run 'mcp-serverman client init' first."
            )

        # Read and validate client configuration
        with open(self.clients_file) as f:
            try:
                clients = json.load(f)
            except json.JSONDecodeError:
                raise click.ClickException("Invalid clients file format. Please run 'mcp-serverman client init' to reset.")

        # Validate system client exists and is valid
        if "system" not in clients:
            raise click.ClickException("System client not found. Please run 'mcp-serverman client init' to reset.")
        
        system_client = clients["system"]
        if (system_client["short_name"] != "system" or
            system_client["config_path"] != str(self.global_registry) or
            system_client["servers_key"] != "mcpServers"):
            raise click.ClickException("System client configuration is invalid. Please run 'mcp-serverman client init' to reset.")

        # Verify global registry has mcpServers key
        with open(self.global_registry) as f:
            try:
                global_config = json.load(f)
                if "mcpServers" not in global_config:
                    global_config["mcpServers"] = {}
                    with open(self.global_registry, 'w') as f:
                        json.dump(global_config, f, indent=2)
            except json.JSONDecodeError:
                raise click.ClickException("Invalid global registry format. Please run 'mcp-serverman client init' to reset.")

        # Handle default client selection
        if short_name is None:
            default_clients = [name for name, info in clients.items() if info["is_default"]]
            if len(default_clients) > 1:
                click.echo("Multiple default clients found. Please select one:")
                for i, name in enumerate(default_clients, 1):
                    click.echo(f"{i}. {clients[name]['name']}")
                choice = click.prompt("Enter number", type=click.IntRange(1, len(default_clients)))
                chosen_client = default_clients[choice - 1]
                
                # Update client.json to set only the chosen client as default
                for client_name in clients:
                    clients[client_name]["is_default"] = 1 if client_name == chosen_client else 0
                
                with open(self.clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
                
                click.echo(f"Set '{chosen_client}' as the default client")
                short_name = chosen_client
            elif len(default_clients) == 1:
                short_name = default_clients[0]
            else:
                raise click.ClickException("No default client found. Please set a default client using 'mcp-serverman client modify <name> --default'")

        if short_name not in clients:
            raise click.ClickException(f"Client '{short_name}' not found.")

        client = clients[short_name]
        
        # Validate client config path exists
        config_path = Path(client["config_path"])
        if not config_path.exists():
            raise click.ClickException(
                f"Config file not found at {config_path} for client '{short_name}'. "
                "Please check the path or remove this client."
            )

        # Validate servers_key exists in client config
        with open(config_path) as f:
            try:
                client_config = json.load(f)
                if client["servers_key"] not in client_config:
                    client_config[client["servers_key"]] = {}
                    with open(config_path, 'w') as f:
                        json.dump(client_config, f, indent=2)
            except json.JSONDecodeError:
                raise click.ClickException(f"Invalid config file format for client '{short_name}'")

        return BaseConfigManager(config_path, servers_key=client["servers_key"])
    
    def add_client(self, short_name: str, name: str, config_path: str, 
                  servers_key: str, set_default: bool = False):
        """Add a new client."""
        if not self.validate_short_name(short_name):
            raise click.ClickException(
                "Invalid short name. Use only letters, numbers, underscores, and hyphens. "
                "Must start with a letter."
            )

        config_path = Path(config_path)
        if not config_path.exists():
            raise click.ClickException(f"Config file not found at {config_path}")

        # Verify the servers_key exists in the config file
        try:
            with open(config_path) as f:
                config = json.load(f)
                if servers_key not in config:
                    config[servers_key] = {}
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
        except json.JSONDecodeError:
            raise click.ClickException(f"Invalid JSON file at {config_path}")

        # Load current clients
        with open(self.clients_file) as f:
            clients = json.load(f)

        # Check if client already exists
        if short_name in clients:
            raise click.ClickException(f"Client '{short_name}' already exists")

        # Add new client
        clients[short_name] = {
            "name": name,
            "short_name": short_name,
            "config_path": str(config_path),
            "servers_key": servers_key,
            "is_default": 1 if set_default else 0
        }

        # If setting as default, unset others
        if set_default:
            for other_client in clients.values():
                if other_client["short_name"] != short_name:
                    other_client["is_default"] = 0

        # Save updated clients file
        with open(self.clients_file, 'w') as f:
            json.dump(clients, f, indent=2)

        click.echo(f"Added client '{name}' ({short_name})")

    def modify_client(self, short_name: str, **kwargs):
        """Modify an existing client."""
        if short_name == "system":
            raise click.ClickException("Cannot modify system client")

        with open(self.clients_file) as f:
            clients = json.load(f)

        if short_name not in clients:
            raise click.ClickException(f"Client '{short_name}' not found")

        client = clients[short_name]

        # Update provided fields
        if "name" in kwargs:
            client["name"] = kwargs["name"]
        if "config_path" in kwargs:
            path = Path(kwargs["config_path"])
            if not path.exists():
                raise click.ClickException(f"Config file not found at {path}")
            client["config_path"] = str(path)
        if "servers_key" in kwargs:
            client["servers_key"] = kwargs["servers_key"]
        if "is_default" in kwargs:
            if kwargs["is_default"]:
                # Unset other defaults
                for other_client in clients.values():
                    other_client["is_default"] = 0
                client["is_default"] = 1

        # Save updated clients file
        with open(self.clients_file, 'w') as f:
            json.dump(clients, f, indent=2)

        click.echo(f"Modified client '{short_name}'")

    def remove_client(self, short_name: str):
        """Remove a client."""
        if short_name == "system":
            raise click.ClickException("Cannot remove system client")

        with open(self.clients_file) as f:
            clients = json.load(f)

        if short_name not in clients:
            raise click.ClickException(f"Client '{short_name}' not found")

        if click.confirm(f"Are you sure you want to remove client '{short_name}'?"):
            del clients[short_name]
            with open(self.clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            click.echo(f"Removed client '{short_name}'")
        else:
            click.echo("Operation cancelled")

    def copy_servers(self, from_client: str, to_client: str, merge: bool = False, 
                    force: bool = False):
        """Copy server configurations between clients."""
        # Get source and target managers
        source_manager = self.get_client(from_client)
        target_manager = self.get_client(to_client)

        # Check if they're actually different
        if source_manager.config_path == target_manager.config_path:
            raise click.ClickException("Source and target clients are the same")

        # Get source server registry
        source_registry = source_manager._load_registry()
        target_registry = target_manager._load_registry()

        if merge:
            # Merge registries
            for server, versions in source_registry.items():
                if server in target_registry:
                    # Create a dictionary of existing versions by hash
                    existing_versions = {v.hash: v for v in target_registry[server]}
                    
                    # Process each version from source
                    for source_version in versions:
                        if source_version.hash in existing_versions:
                            # Compare timestamps if hash exists and is the same
                            existing_version = existing_versions[source_version.hash]
                            source_time = int(source_version.timestamp.replace('_', ''))
                            target_time = int(existing_version.timestamp.replace('_', ''))
                            
                            # Keep the newer version
                            if source_time > target_time:
                                # Replace the old version with the newer one
                                target_registry[server] = [
                                    source_version if v.hash == existing_version.hash else v 
                                    for v in target_registry[server]
                                ]
                        else:
                            # Add new version if hash doesn't exist
                            target_registry[server].append(source_version)
                else:
                    target_registry[server] = versions
        elif force:
            if click.confirm("This will overwrite the target registry. Continue?"):
                target_registry = source_registry
            else:
                click.echo("Operation cancelled")
                return
        else:
            # Only copy servers that don't exist in target
            for server, versions in source_registry.items():
                if server not in target_registry:
                    target_registry[server] = versions

        # Save target registry
        target_manager._save_registry(target_registry)
        click.echo(f"Copied servers from '{from_client}' to '{to_client}'")

        # Copy preset files
        preset_files = source_manager.history_dir.glob("preset-*.json")
        for preset_file in preset_files:
            target_preset = target_manager.history_dir / preset_file.name
            if not target_preset.exists() or force:
                with open(preset_file) as f:
                    preset_data = json.load(f)
                with open(target_preset, 'w') as f:
                    json.dump(preset_data, f, indent=2)
            elif merge:
                with open(preset_file) as f:
                    source_preset = json.load(f)
                with open(target_preset) as f:
                    target_preset_data = json.load(f)
                # Merge servers from source that don't exist in target
                for server, config in source_preset.get("mcpServers", {}).items():
                    if server not in target_preset_data.get("mcpServers", {}):
                        target_preset_data.setdefault("mcpServers", {})[server] = config
                with open(target_preset, 'w') as f:
                    json.dump(target_preset_data, f, indent=2)