#!/usr/bin/env python3
# This file handles all cli operations
import json
from pathlib import Path
import datetime
import click
from rich.console import Console
from rich.table import Table
from pkg_resources import resource_filename

from .config import BaseConfigManager,ClaudeConfigManager
from .client import ClientManager

console = Console()


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

def get_mcp_executable():
    """Find the mcp executable installed with this package."""
    import shutil
    mcp_path = shutil.which('mcp')
    if not mcp_path:
        raise click.ClickException("Could not find mcp executable. Is mcp package installed?")
    return mcp_path

@cli.command('companion')
@click.option('--client', help='Client to configure')
def client_register_server(client):
    """Register this package's companion MCP server to let Claude/LLM manage mcp-server configurations"""
    manager = ClientManager().get_client(client)
    try:
        # Get the installed path of mcp_tool_server.py
        server_path = resource_filename('mcp_serverman', 'data/servers/mcp_tool_server.py')
        # Get the mcp executable path
        mcp_path = get_mcp_executable()
        
        # Configure the server
        config = manager.read_config()
        config.setdefault(manager.servers_key, {})
        config[manager.servers_key]['mcp-serverman'] = {
            "command": mcp_path,
            "args": ["run", server_path]
        }
        manager.write_config(config)
        click.echo("MCP server registered successfully.")
    except Exception as e:
        click.echo(f"Error registering MCP server: {str(e)}", err=True)

if __name__ == '__main__':
    cli()