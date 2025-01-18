#!/usr/bin/env python3
import json
import re
from pathlib import Path
import datetime
import click
import platform
import hashlib
from pathlib import Path
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

class ClaudeConfigManager:
    def __init__(self):
        self.system = platform.system()
        self.config_path = self._get_config_path()
        self.history_dir = self._get_history_dir()
        self.servers_registry = self.history_dir / "servers_registry.json"
        self._ensure_history_dir()
        
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

    def _get_history_dir(self) -> Path:
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
        return server_name in config.get("mcpServers", {})

    def list_servers(self, mode: str = 'all') -> Dict[str, Dict[str, Any]]:
        """List servers based on mode ('all', 'enabled', 'disabled')."""
        config = self.read_config()
        current_servers = config.get("mcpServers", {})
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
                config.setdefault("mcpServers", {})
                config["mcpServers"][server_name] = version.config
                self.write_config(config)
                click.echo(f"Enabled server '{server_name}' with specified version")
            else:
                click.echo("Operation cancelled")
                return
        else:
            config["mcpServers"][server_name] = version.config
            self.write_config(config)
            click.echo(f"Changed configuration for server '{server_name}'")
    def save_server_state(self, server_name: str, comment: Optional[str] = None):
        """Save current state of a server."""
        config = self.read_config()
        if server_name not in config.get("mcpServers", {}):
            raise click.ClickException(f"Server '{server_name}' is not enabled")
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = comment or f"Saved at {timestamp}"
        
        self.add_server_version(
            server_name,
            config["mcpServers"][server_name],
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

    def save_preset(self, name: str):
        """Save current configuration as a preset."""
        if not self.is_valid_preset_name(name):
            raise click.ClickException(
                "Invalid preset name. Use only letters, numbers, underscores, and hyphens. "
                "Must start with a letter or number."
            )
            
        config = self.read_config()
        current_servers = config.get("mcpServers", {})
        
        # Create preset with hash versions
        preset_data = {"mcpServers": {}}
        for server_name, server_config in current_servers.items():
            # Get or create version for server
            versions = self.get_server_versions(server_name)
            if not versions:
                # Create initial state version if no version has set up
                self.add_server_version(
                    server_name,
                    server_config,
                    comment="Initial state"
                )
                versions = self.get_server_versions(server_name)
                
            current_hash = self._compute_hash(server_config)
            matching_version = next(
                (v for v in versions if v.hash == current_hash),
                versions[-1]  # Fallback to latest version
            )
            
            preset_data["mcpServers"][server_name] = {
                "config": server_config,
                "hash": matching_version.hash
            }
        
        preset_path = self.get_preset_path(name)
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
        config["mcpServers"] = {}
        registry = self._load_registry()
        
        # Track various issues that need handling
        missing_servers = {}
        version_conflicts = {}
        preset_modified = False
        
        # First pass: check for issues
        for server_name, server_data in preset_data["mcpServers"].items():
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
                del preset_data["mcpServers"][server_name]
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
                    preset_data["mcpServers"][server_name]["config"] = version.config
                    preset_data["mcpServers"][server_name]["hash"] = version.hash
                    preset_modified = True
                else:
                    if not click.confirm(f"Skip server '{server_name}'?"):
                        click.echo("Operation cancelled")
                        return
                    del preset_data["mcpServers"][server_name]
                    preset_modified = True
        
        # Save updated preset if any changes were made
        if preset_modified:
            with open(preset_path, 'w') as f:
                json.dump(preset_data, f, indent=2)
                click.echo("\nUpdated preset file with new selections")
        
        # Apply configuration
        config["mcpServers"] = {
            name: data["config"]
            for name, data in preset_data["mcpServers"].items()
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
                    server_count = len(data.get("mcpServers", {}))
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


@click.group()
def cli():
    """Claude Server Configuration Manager"""
    pass

@cli.command()
@click.option('--enabled', 'mode', flag_value='enabled', help="Show only enabled servers")
@click.option('--disabled', 'mode', flag_value='disabled', help="Show only disabled servers")
def list(mode):
    """List servers (default: all servers)."""
    manager = ClaudeConfigManager()
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
def enable(server_name, version):
    """Enable a specific server."""
    manager = ClaudeConfigManager()
    
    # If no version specified, show versions and prompt
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
            version = 1  # If only one version, use it automatically
    
    try:
        manager.change_server_config(server_name, version_number=version)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('server_name')
def disable(server_name):
    """Disable a specific server."""
    manager = ClaudeConfigManager()
    config = manager.read_config()
    
    if server_name not in config.get("mcpServers", {}):
        raise click.ClickException(f"Server '{server_name}' is not enabled")
    
    # Save current config if it has changed
    manager.add_server_version(
        server_name, 
        config["mcpServers"][server_name],
        comment=f"Configuration before disable at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    del config["mcpServers"][server_name]
    manager.write_config(config)
    click.echo(f"Disabled server: {server_name}")

@cli.command()
@click.argument('server_name')
@click.option('--list', 'list_versions', is_flag=True, help="List all versions of the server")
@click.option('--hash', help="Change to specific version by hash")
@click.option('--version', type=int, help="Change to specific version by number")
def change(server_name, list_versions, hash, version):
    """Change server configuration or list versions."""
    manager = ClaudeConfigManager()
    
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
def save(server_name, comment):
    """Save current state of a server."""
    manager = ClaudeConfigManager()
    try:
        manager.save_server_state(server_name, comment)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('server_name')
@click.option('--version', type=int, help="Version number to remove")
@click.option('--hash', help="Version hash to remove")
def remove(server_name, version, hash):
    """Remove a server version or entire server."""
    manager = ClaudeConfigManager()
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
def preset_save(name):
    """Save current configuration as a preset."""
    manager = ClaudeConfigManager()
    try:
        manager.save_preset(name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('load')
@click.argument('name')
def preset_load(name):
    """Load a preset configuration."""
    manager = ClaudeConfigManager()
    try:
        manager.load_preset(name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('delete')
@click.argument('name')
def preset_delete(name):
    """Delete a preset configuration."""
    manager = ClaudeConfigManager()
    try:
        manager.delete_preset(name)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@preset.command('list')
def preset_list():
    """List all available presets."""
    manager = ClaudeConfigManager()
    manager.list_presets()


if __name__ == '__main__':
    cli()