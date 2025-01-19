#!/usr/bin/env python3
import json
import re
from pathlib import Path
import datetime
import click
import platform
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@dataclass
class ServerVersion:
    timestamp: str
    config: Dict[str, Any]
    hash: str
    comment: Optional[str] = None

class BaseConfigManager:
    """Base configuration manager with common functionality"""
    def __init__(self, config_path: Path, servers_key: str = "mcpServers"):
        self.config_path = config_path
        self.servers_key = servers_key
        self.history_dir = self._get_history_dir()
        self.servers_registry = self.history_dir / "servers_registry.json"
        self._ensure_history_dir()

    def _get_history_dir(self) -> Path:
        """Get the directory for storing history and presets."""
        return self.config_path.parent / ".history"

    def _ensure_history_dir(self):
            """Initialize history directory and registry if needed."""
            self.history_dir.mkdir(parents=True, exist_ok=True)
            if not self.servers_registry.exists():
                self._save_registry({})

    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """Compute hash of server configuration."""
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]

    def _save_registry(self, registry: Dict[str, List[ServerVersion]]):
        """Save the servers registry."""
        registry_data = {
            server: [
                {
                    "timestamp": v.timestamp,
                    "config": v.config,
                    "hash": v.hash,
                    "comment": v.comment
                }
                for v in versions
            ]
            for server, versions in registry.items()
        }
        with open(self.servers_registry, 'w') as f:
            json.dump(registry_data, f, indent=2)

    def _load_registry(self) -> Dict[str, List[ServerVersion]]:
        """Load the servers registry."""
        if not self.servers_registry.exists():
            return {}
        with open(self.servers_registry) as f:
            data = json.load(f)
            return {
                server: [
                    ServerVersion(
                        timestamp=v["timestamp"],
                        config=v["config"],
                        hash=v["hash"],
                        comment=v.get("comment")
                    )
                    for v in versions
                ]
                for server, versions in data.items()
            }

    def read_config(self) -> Dict[str, Any]:
        """Read the current configuration file."""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            raise click.ClickException(f"Configuration file not found at {self.config_path}")

    def write_config(self, config: Dict[str, Any]):
        """Write configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def is_server_enabled(self, server_name: str) -> bool:
        """Check if a server is currently enabled."""
        config = self.read_config()
        return server_name in config.get(self.servers_key, {})

    def list_servers(self, mode: str = 'all') -> Dict[str, Dict[str, Any]]:
        """List servers based on mode ('all', 'enabled', 'disabled')."""
        config = self.read_config()
        current_servers = config.get(self.servers_key, {})
        registry = self._load_registry()
        
        servers = {}
        # Add currently enabled servers
        if mode in ['all', 'enabled']:
            for server_name, server_config in current_servers.items():
                servers[server_name] = {
                    "enabled": True,
                    "versions": len(registry.get(server_name, [])),
                    "current_hash": self._compute_hash(server_config)
                }
        
        # Add disabled servers
        if mode in ['all', 'disabled']:
            for server_name, versions in registry.items():
                if server_name not in current_servers:
                    servers[server_name] = {
                        "enabled": False,
                        "versions": len(versions),
                        "current_hash": None
                    }
        
        return servers

    def get_server_versions(self, server_name: str) -> List[ServerVersion]:
        """Get all versions of a server."""
        registry = self._load_registry()
        return registry.get(server_name, [])

    def add_server_version(self, server_name: str, config: Dict[str, Any], comment: Optional[str] = None):
        """Add a new version of a server to the registry if config has changed."""
        registry = self._load_registry()
        new_hash = self._compute_hash(config)
        
        # Check if this version already exists
        versions = registry.get(server_name, [])
        if versions and self._compute_hash(versions[-1].config) == new_hash:
            return  # Skip if config hasn't changed
            
        version = ServerVersion(
            timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            config=config,
            hash=new_hash,
            comment=comment
        )
        
        if server_name not in registry:
            registry[server_name] = []
        registry[server_name].append(version)
        self._save_registry(registry)

    def display_server_versions(self, server_name: str) -> int:
        """Display all versions of a server with detailed config. Returns number of versions."""
        versions = self.get_server_versions(server_name)
        if not versions:
            click.echo(f"No versions found for server '{server_name}'")
            return 0
        
        for i, version in enumerate(versions, 1):
            table = Table(show_header=False, title=f"Version {i}")
            table.add_row("Hash", version.hash)
            table.add_row("Timestamp", version.timestamp)
            if version.comment:
                table.add_row("Comment", version.comment)
            console.print(table)
            
            # Display config in a panel
            console.print(Panel(
                json.dumps(version.config, indent=2),
                title=f"Configuration",
                border_style="blue"
            ))
            console.print("\n")
        
        return len(versions)

    def change_server_config(self, server_name: str, version_hash: str = None, version_number: int = None):
        """Change server configuration to a specific version."""
        config = self.read_config()
        versions = self.get_server_versions(server_name)
        
        if not versions:
            raise click.ClickException(f"No versions found for server '{server_name}'")
        
        # Get the target version
        if version_number is not None:
            if not 1 <= version_number <= len(versions):
                raise click.ClickException(f"Invalid version number. Available range: 1-{len(versions)}")
            version = versions[version_number - 1]
        elif version_hash:
            version = next((v for v in versions if v.hash == version_hash), None)
            if not version:
                raise click.ClickException(f"Version {version_hash} not found for server '{server_name}'")
        else:
            raise click.ClickException("Either version number or hash must be specified")
        
        # Check if server is disabled
        if not self.is_server_enabled(server_name):
            if click.confirm(f"Server '{server_name}' is currently disabled. Would you like to enable it with this version?"):
                config.setdefault(self.servers_key, {})
                config[self.servers_key][server_name] = version.config
                self.write_config(config)
                click.echo(f"Enabled server '{server_name}' with specified version")
            else:
                click.echo("Operation cancelled")
                return
        else:
            config[self.servers_key][server_name] = version.config
            self.write_config(config)
            click.echo(f"Changed configuration for server '{server_name}'")
            
    def save_server_state(self, server_name: str, comment: Optional[str] = None):
        """Save current state of a server."""
        config = self.read_config()
        if server_name not in config.get(self.servers_key, {}):
            raise click.ClickException(f"Server '{server_name}' is not enabled")
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = comment or f"Saved at {timestamp}"
        
        self.add_server_version(
            server_name,
            config[self.servers_key][server_name],
            comment=comment
        )
        click.echo(f"Saved state for server '{server_name}' with comment: {comment}")

    def remove_server_version(self, server_name: str, version_hash: str = None, version_number: int = None):
        """Remove a specific version or entire server."""
        registry = self._load_registry()
        if server_name not in registry:
            raise click.ClickException(f"Server '{server_name}' not found in registry")
            
        versions = registry[server_name]
        
        if version_hash or version_number is not None:
            # Remove specific version
            if version_number is not None:
                if not 1 <= version_number <= len(versions):
                    raise click.ClickException(f"Invalid version number. Available range: 1-{len(versions)}")
                version_to_remove = versions[version_number - 1]
            else:
                version_to_remove = next((v for v in versions if v.hash == version_hash), None)
                if not version_to_remove:
                    raise click.ClickException(f"Version {version_hash} not found")
                    
            registry[server_name] = [v for v in versions if v.hash != version_to_remove.hash]
            if not registry[server_name]:  # If no versions left, remove server entry
                del registry[server_name]
        else:
            # Remove entire server
            if click.confirm(f"Are you sure you want to permanently remove server '{server_name}' and all its versions?"):
                del registry[server_name]
                click.echo(f"Removed server '{server_name}' and all its versions")
            else:
                click.echo("Operation cancelled")
                return
                
        self._save_registry(registry)

    def is_valid_preset_name(self, name: str) -> bool:
        """Check if a preset name is valid for all OS file systems."""
        # Basic file name validation that works across operating systems
        return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', name))

    def get_preset_path(self, name: str) -> Path:
        """Get the path for a preset file."""
        return self.history_dir / f"preset-{name}.json"

    def save_preset(self, name: str, force: bool = False):
        """Save current configuration as a preset."""
        if not self.is_valid_preset_name(name):
            raise click.ClickException(
                "Invalid preset name. Use only letters, numbers, underscores, and hyphens. "
                "Must start with a letter or number."
            )
            
        preset_path = self.get_preset_path(name)
        if preset_path.exists() and not force:
            if not click.confirm(f"Preset '{name}' already exists. Do you want to overwrite it?"):
                click.echo("Operation cancelled")
                return
        
        config = self.read_config()
        current_servers = config.get(self.servers_key, {})
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create preset with hash versions
        preset_data = {self.servers_key: {}}
        for server_name, server_config in current_servers.items():
            # Get or create version for server
            versions = self.get_server_versions(server_name)
            current_hash = self._compute_hash(server_config)
            
            # Check if current config matches any existing version
            matching_version = next(
                (v for v in versions if v.hash == current_hash),
                None
            )
            
            # If no matching version or no versions at all, create a new one
            if not matching_version:
                comment = f"Configuration saved for preset '{name}' at {timestamp}"
                self.add_server_version(
                    server_name,
                    server_config,
                    comment=comment
                )
                versions = self.get_server_versions(server_name)
                matching_version = versions[-1]  # Get the newly created version
            
            preset_data[self.servers_key][server_name] = {
                "config": server_config,
                "hash": matching_version.hash
            }
        
        with open(preset_path, 'w') as f:
            json.dump(preset_data, f, indent=2)
        
        click.echo(f"Saved preset '{name}'")

    def load_preset(self, name: str):
        """Load a preset configuration."""
        preset_path = self.get_preset_path(name)
        if not preset_path.exists():
            raise click.ClickException(f"Preset '{name}' not found")
            
        with open(preset_path) as f:
            preset_data = json.load(f)
            
        config = self.read_config()
        config[self.servers_key] = {}
        registry = self._load_registry()
        
        # Track various issues that need handling
        missing_servers = {}
        version_conflicts = {}
        preset_modified = False
        
        # First pass: check for issues
        for server_name, server_data in preset_data[self.servers_key].items():
            target_hash = server_data["hash"]
            
            # Check if server exists in registry
            if server_name not in registry:
                missing_servers[server_name] = server_data
                continue
                
            versions = self.get_server_versions(server_name)
            if not versions:
                version_conflicts[server_name] = {
                    "error": "No versions available",
                    "versions": []
                }
            elif not any(v.hash == target_hash for v in versions):
                version_conflicts[server_name] = {
                    "error": f"Version {target_hash} not found",
                    "versions": versions
                }
        
        # Handle missing servers
        for server_name, server_data in missing_servers.items():
            click.echo(f"\nServer '{server_name}' not found in registry.")
            choice = click.prompt(
                "Choose action",
                type=click.Choice(['restore', 'skip', 'cancel']),
                default='skip'
            )
            
            if choice == 'cancel':
                click.echo("Operation cancelled")
                return
            elif choice == 'restore':
                # Restore server with stored configuration
                registry[server_name] = [
                    ServerVersion(
                        timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                        config=server_data["config"],
                        hash=server_data["hash"],
                        comment="Restored from preset"
                    )
                ]
                self._save_registry(registry)
                click.echo(f"Restored server '{server_name}' from preset")
            else:  # if type skip
                click.echo(f"Skipping server '{server_name}'")
                del preset_data[self.servers_key][server_name]
                preset_modified = True
        
        # Handle version conflicts
        if version_conflicts:
            click.echo("\nSome servers require version selection:")
            for server_name, conflict in version_conflicts.items():
                click.echo(f"\nServer: {server_name}")
                click.echo(f"Error: {conflict['error']}")
                
                if conflict['versions']:
                    num_versions = self.display_server_versions(server_name)
                    version_num = click.prompt(
                        "Please select a version number",
                        type=click.IntRange(1, num_versions)
                    )
                    version = conflict['versions'][version_num - 1]
                    preset_data[self.servers_key][server_name]["config"] = version.config
                    preset_data[self.servers_key][server_name]["hash"] = version.hash
                    preset_modified = True
                else:
                    if not click.confirm(f"Skip server '{server_name}'?"):
                        click.echo("Operation cancelled")
                        return
                    del preset_data[self.servers_key][server_name]
                    preset_modified = True
        
        # Save updated preset if any changes were made
        if preset_modified:
            with open(preset_path, 'w') as f:
                json.dump(preset_data, f, indent=2)
                click.echo("\nUpdated preset file with new selections")
        
        # Apply configuration
        config[self.servers_key] = {
            name: data["config"]
            for name, data in preset_data[self.servers_key].items()
        }
        
        self.write_config(config)
        click.echo(f"\nLoaded preset '{name}'")
    
    def delete_preset(self, name: str):
        """Delete a preset configuration."""
        preset_path = self.get_preset_path(name)
        if not preset_path.exists():
            raise click.ClickException(f"Preset '{name}' not found")
            
        if click.confirm(f"Are you sure you want to delete preset '{name}'?"):
            preset_path.unlink()
            click.echo(f"Deleted preset '{name}'")
        else:
            click.echo("Operation cancelled")

    def list_presets(self):
        """List all available presets."""
        preset_files = self.history_dir.glob("preset-*.json")
        presets = []
        
        for preset_file in preset_files:
            name = preset_file.stem[7:]  # Remove 'preset-' prefix when reading the dir
            try:
                with open(preset_file) as f:
                    data = json.load(f)
                    server_count = len(data.get(self.servers_key, {}))
                    presets.append((name, server_count, preset_file.stat().st_mtime))
            except (json.JSONDecodeError, OSError):
                continue
        
        if not presets:
            click.echo("No presets found")
            return
            
        table = Table(title="Available Presets")
        table.add_column("Name")
        table.add_column("Servers")
        table.add_column("Last Modified")
        
        for name, server_count, mtime in sorted(presets, key=lambda x: x[0]):
            table.add_row(
                name,
                str(server_count),
                datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            )
        
        console.print(table)
    
class ClaudeConfigManager(BaseConfigManager):
    """Claude-Desktop specific configuration manager to keep the original functionality"""
    def __init__(self):
        self.system = platform.system()
        config_path = self._get_config_path()
        super().__init__(config_path, servers_key="mcpServers")
    
    def _get_config_path(self) -> Path:
        """Get the Claude configuration file path based on the OS."""
        if self.system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        elif self.system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif self.system == "Windows":
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        else:
            raise NotImplementedError(f"Unsupported operating system: {self.system}")

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
        """Get a config manager instance for a specific client."""
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


@click.group()
def cli():
    """Claude Server Configuration Manager"""
    pass

@cli.command()
@click.option('--enabled', 'mode', flag_value='enabled', help="Show only enabled servers")
@click.option('--disabled', 'mode', flag_value='disabled', help="Show only disabled servers")
@click.option('--client', help="Specify a client")
def list(mode, client):
    """List servers (default: all servers)."""
    manager = ClientManager().get_client(client)
    servers = manager.list_servers(mode or 'all')
    
    table = Table(title="Claude Servers")
    table.add_column("Server Name")
    table.add_column("Status")
    table.add_column("Versions")
    table.add_column("Current Hash")
    
    for server_name, info in sorted(servers.items()):
        table.add_row(
            server_name,
            "[green]enabled[/green]" if info["enabled"] else "[red]disabled[/red]",
            str(info["versions"]),
            info["current_hash"] or "N/A"
        )
    
    console.print(table)

@cli.command()
@click.argument('server_name')
@click.option('--version', type=int, help="Version number to enable")
@click.option('--client', help="Specify a client")
def enable(server_name, version, client):
    """Enable a specific server."""
    manager = ClientManager().get_client(client)
    
    if version is None:
        num_versions = manager.display_server_versions(server_name)
        if num_versions == 0:
            return
            
        if num_versions > 1:
            version = click.prompt(
                "Multiple versions available. Please specify version number",
                type=click.IntRange(1, num_versions)
            )
        else:
            version = 1
    
    try:
        manager.change_server_config(server_name, version_number=version)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('server_name')
@click.option('--client', help="Specify a client")
def disable(server_name, client):
    """Disable a specific server."""
    manager = ClientManager().get_client(client)
    config = manager.read_config()
    
    if server_name not in config.get(manager.servers_key, {}):
        raise click.ClickException(f"Server '{server_name}' is not enabled")
    
    manager.add_server_version(
        server_name, 
        config[manager.servers_key][server_name],
        comment=f"Configuration before disable at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    del config[manager.servers_key][server_name]
    manager.write_config(config)
    click.echo(f"Disabled server: {server_name}")

@cli.command()
@click.argument('server_name')
@click.option('--list', 'list_versions', is_flag=True, help="List all versions of the server")
@click.option('--hash', help="Change to specific version by hash")
@click.option('--version', type=int, help="Change to specific version by number")
@click.option('--client', help="Specify a client")
def change(server_name, list_versions, hash, version, client):
    """Change server configuration or list versions."""
    manager = ClientManager().get_client(client)
    
    if list_versions:
        manager.display_server_versions(server_name)
        return
    
    if hash or version:
        try:
            manager.change_server_config(server_name, version_hash=hash, version_number=version)
        except click.ClickException as e:
            click.echo(f"Error: {str(e)}", err=True)
    else:
        click.echo("Please specify either --list, --hash, or --version")

@cli.command()
@click.argument('server_name')
@click.option('--comment', help="Optional comment for the saved state")
@click.option('--client', help="Specify a client")
def save(server_name, comment, client):
    """Save current state of a server."""
    manager = ClientManager().get_client(client)
    try:
        manager.save_server_state(server_name, comment)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('server_name')
@click.option('--version', type=int, help="Version number to remove")
@click.option('--hash', help="Version hash to remove")
@click.option('--client', help="Specify a client")
def remove(server_name, version, hash, client):
    """Remove a server version or entire server."""
    manager = ClientManager().get_client(client)
    try:
        manager.remove_server_version(server_name, hash, version)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.group()
def preset():
    """Manage configuration presets."""
    pass

@preset.command('save')
@click.argument('name')
@click.option('--force', is_flag=True, help="Force overwrite if preset exists")
@click.option('--client', help="Client to manage")
def preset_save(name, force, client):
    """Save current configuration as a preset."""
    manager = ClientManager().get_client(client)
    try:
        manager.save_preset(name, force)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('load')
@click.argument('name')
@click.option('--client', help="Specify a client")
def preset_load(name, client):
    """Load a preset configuration."""
    manager = ClientManager().get_client(client)
    try:
        manager.load_preset(name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('delete')
@click.argument('name')
@click.option('--client', help="Specify a client")
def preset_delete(name, client):
    """Delete a preset configuration."""
    manager = ClientManager().get_client(client)
    try:
        manager.delete_preset(name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('list')
@click.option('--client', help="Specify a client")
def preset_list(client):
    """List all available presets."""
    manager = ClientManager().get_client(client)
    manager.list_presets()

# New client management commands
@cli.group()
def client():
    """Manage MCP server clients."""
    pass

@client.command('init')
def client_init():
    """Initialize client configuration."""
    manager = ClientManager()
    manager.initialize()

@client.command('list')
def client_list():
    """List all registered clients."""
    manager = ClientManager()
    try:
        manager.list_clients()
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@client.command('add')
@click.argument('short_name', required=False)
@click.option('--name', help="Client display name")
@click.option('--path', help="Path to client config file")
@click.option('--key', help="Key name for servers in config file")
@click.option('--default', is_flag=True, help="Set as default client")
def client_add(short_name, name, path, key, default):
    """Add a new client. If no options provided, runs in interactive mode."""
    manager = ClientManager()

    # If only short_name or part of required fields are provided without other required options
    if short_name and not all([name, path, key]):
        raise click.UsageError(
            "Missing required options. Use either:\n"
            "  - Interactive mode: mcp-serverman client add\n"
            "  - Full command: mcp-serverman client add <short_name> --name <name> --path <path> --key <key> [--default]"
        )

    # Check if we're going into an interactive mode when no options provided
    if not any([short_name, name, path, key]):
        click.echo("Running in interactive mode...")
        
        # Get and validate short name
        while True:
            short_name = click.prompt(
                "Enter client short name (used in CLI commands, e.g., 'claude', 'zed')"
            )
            if not manager.validate_short_name(short_name):
                click.echo(
                    "Invalid short name. Use only letters, numbers, underscores, and hyphens. "
                    "Must start with a letter."
                )
                continue
            try:
                # Open clients file to check if short_name exists
                with open(manager.clients_file) as f:
                    clients = json.load(f)
                if short_name in clients:
                    click.echo(f"Client '{short_name}' already exists. Please choose another name.")
                    continue
            except FileNotFoundError:
                # If clients file doesn't exist, that's fine
                pass
            break

        # Get display name
        name = click.prompt("Enter client display name (e.g., 'Claude Desktop', 'Zed Editor')")

        # Get and validate config path
        while True:
            path = click.prompt("Enter path to client config file")
            config_path = Path(path)
            
            # Check if path exists
            if not config_path.exists():
                click.echo(f"Path not found: {path}")
                continue
                
            # Check if it's a directory
            if config_path.is_dir():
                click.echo(f"Error: {path} is a directory, not a file")
                continue
                
            # Try to read and parse as JSON
            try:
                with open(config_path) as f:
                    json.load(f)  # Try to parse JSON
                break
            except json.JSONDecodeError:
                click.echo(f"Invalid JSON file at {path}")
            except Exception as e:
                click.echo(f"Error accessing file: {e}")

        # Get and validate servers key
        while True:
            key = click.prompt(
                "Enter servers key name in config file\n"
                "Examples:\n"
                "  - 'mcpServers' for Claude Desktop\n"
                "  - 'content_servers' for Zed\n"
                "  - 'mcp_servers' for MCP-Bridge\n"
                "Enter key"
            )
            try:
                with open(config_path) as f:
                    config = json.load(f)
                if key not in config:
                    if click.confirm(f"Key '{key}' not found in config file. Create it?"):
                        config[key] = {}
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        break
                    continue
                break
            except Exception as e:
                click.echo(f"Error reading config file: {e}")
                continue

        # Ask about default status
        default = click.confirm("Set as default client?")

    # Validate path before adding client in non-interactive mode
    elif path:
        config_path = Path(path)
        if not config_path.exists():
            raise click.ClickException(f"Path not found: {path}")
        if config_path.is_dir():
            raise click.ClickException(f"Error: {path} is a directory, not a file")
        try:
            with open(config_path) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise click.ClickException(f"Invalid JSON file at {path}")
        except Exception as e:
            raise click.ClickException(f"Error accessing file: {e}")

    try:
        manager.add_client(short_name, name, path, key, default)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@client.command('modify')
@click.argument('short_name')
@click.option('--name', help="New client display name")
@click.option('--path', help="New path to client config file")
@click.option('--key', help="New key name for servers in config file")
@click.option('--default', is_flag=True, help="Set as default client")
def client_modify(short_name, name, path, key, default):
    """Modify an existing client."""
    manager = ClientManager()
    try:
        kwargs = {}
        if name:
            kwargs['name'] = name
        if path:
            kwargs['config_path'] = path
        if key:
            kwargs['servers_key'] = key
        if default:
            kwargs['is_default'] = True
        manager.modify_client(short_name, **kwargs)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@client.command('remove')
@click.argument('short_name')
def client_remove(short_name):
    """Remove a client."""
    manager = ClientManager()
    try:
        manager.remove_client(short_name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@client.command('copy')
@click.option('--from', 'from_client', required=True, help="Source client")
@click.option('--to', 'to_client', required=True, help="Target client")
@click.option('--merge', is_flag=True, help="Merge configurations")
@click.option('--force', is_flag=True, help="Force overwrite")
def client_copy(from_client, to_client, merge, force):
    """Copy server configurations between clients."""
    manager = ClientManager()
    try:
        manager.copy_servers(from_client, to_client, merge, force)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    cli()