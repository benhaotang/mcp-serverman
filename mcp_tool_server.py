from mcp.server.fastmcp import FastMCP
from mcp_serverman.client import ClientManager

mcp = FastMCP("MCP Tool Server")

@mcp.tool()
def list_servers() -> dict:
    """
    List all servers (enabled and disabled).
    """
    manager = ClientManager().get_client()
    # 'all' mode returns both enabled and disabled servers
    return manager.list_servers(mode='all')

@mcp.tool()
def enable_server(server_name: str, version: int = None) -> str:
    """
    Enable a specified server.
    If version is not provided, version 1 will be used.
    """
    manager = ClientManager().get_client()
    try:
        if version is None:
            # Instead of prompting, default to version 1 (or add your own logic)
            version = 1
        manager.change_server_config(server_name, version_number=version)
        return f"Enabled server '{server_name}' with version {version}."
    except Exception as e:
        return f"Error enabling server '{server_name}': {str(e)}"

@mcp.tool()
def disable_server(server_name: str) -> str:
    """
    Disable a specified server.
    """
    manager = ClientManager().get_client()
    config = manager.read_config()
    if server_name not in config.get(manager.servers_key, {}):
        return f"Server '{server_name}' is not enabled."
    try:
        # Save current state before disabling
        manager.add_server_version(
            server_name,
            config[manager.servers_key][server_name],
            comment="Configuration before disable (via tool server)"
        )
        del config[manager.servers_key][server_name]
        manager.write_config(config)
        return f"Disabled server '{server_name}'."
    except Exception as e:
        return f"Error disabling server '{server_name}': {str(e)}"

@mcp.tool()
def save_profile(profile_name: str) -> str:
    """
    Save the current configuration as a profile (preset) under the given name.
    """
    manager = ClientManager().get_client()
    try:
        # Force overwrite for simplicity; adjust as needed
        manager.save_preset(profile_name, force=True)
        return f"Profile '{profile_name}' saved successfully."
    except Exception as e:
        return f"Error saving profile '{profile_name}': {str(e)}"

@mcp.tool()
def load_profile(profile_name: str) -> str:
    """
    Load a profile (preset) into the current configuration.
    """
    manager = ClientManager().get_client()
    try:
        manager.load_preset(profile_name)
        return f"Profile '{profile_name}' loaded successfully. Please restart the client to apply changes."
    except Exception as e:
        return f"Error loading profile '{profile_name}': {str(e)}"

@mcp.tool()
def enable_servers(server_names: list, version: int = None, client: str = None) -> dict:
    """
    Bulk enable servers given an array of server names.
    If version is not provided, defaults to 1.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    results = {}
    for server in server_names:
        try:
            ver = version if version is not None else 1
            manager.change_server_config(server, version_number=ver)
            results[server] = f"Enabled with version {ver}"
        except Exception as e:
            results[server] = f"Error: {str(e)}"
    return results

@mcp.tool()
def disable_servers(server_names: list, client: str = None) -> dict:
    """
    Bulk disable servers given an array of server names.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    results = {}
    config = manager.read_config()
    for server in server_names:
        if server not in config.get(manager.servers_key, {}):
            results[server] = "Server is not enabled"
            continue
        try:
            manager.add_server_version(
                server,
                config[manager.servers_key][server],
                comment="Configuration before disable (bulk operation)"
            )
            del config[manager.servers_key][server]
            manager.write_config(config)
            results[server] = "Disabled successfully"
        except Exception as e:
            results[server] = f"Error: {str(e)}"
    return results

@mcp.tool()
def list_clients() -> dict:
    """
    List all registered clients.
    """
    import json
    manager = ClientManager()
    try:
        with open(manager.clients_file) as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def set_default_client(client_short_name: str) -> str:
    """
    Set the specified client as the default client.
    """
    manager = ClientManager()
    try:
        manager.modify_client(client_short_name, is_default=True)
        return f"Client '{client_short_name}' set as default."
    except Exception as e:
        return f"Error setting default client: {str(e)}"

if __name__ == "__main__":
    mcp.run()
