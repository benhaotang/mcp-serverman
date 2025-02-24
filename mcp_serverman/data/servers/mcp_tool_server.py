import datetime
from mcp.server.fastmcp import FastMCP
from mcp_serverman.client import ClientManager

mcp = FastMCP("MCP Tool Server")

@mcp.tool()
def list_servers(client: str = None) -> dict:
    """
    List all servers (enabled and disabled).
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    # 'all' mode returns both enabled and disabled servers
    return manager.list_servers(mode='all')

@mcp.tool()
def enable_server(server_name: str, version: int = None, client: str = None) -> str:
    """
    Enable a specified server.
    If version is not provided, version 1 will be used.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    try:
        result = manager.enable_server_noninteractive(server_name, version_number=version)
        return f"{result}, please restart the client to apply changes."
    except Exception as e:
        return f"Error enabling server '{server_name}': {str(e)}"

@mcp.tool()
def disable_server(server_name: str, client: str = None) -> str:
    """
    Disable a specified server.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    config = manager.read_config()
    if server_name not in config.get(manager.servers_key, {}):
        return f"Server '{server_name}' is not enabled."
    try:
        # Save current state before disabling
        manager.add_server_version(
            server_name,
            config[manager.servers_key][server_name],
            comment=f"Configuration before disable (via tool server) at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        del config[manager.servers_key][server_name]
        manager.write_config(config)
        return f"Disabled server '{server_name}', please restart the client to apply changes."
    except Exception as e:
        return f"Error disabling server '{server_name}': {str(e)}"

@mcp.tool()
def save_server(server_name: str, comment: str = None, client: str = None) -> str:
    """
    Save the current state of a server.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    try:
        manager.save_server_state(server_name, comment)
        return f"Server state saved successfully for '{server_name}'."
    except Exception as e:
        return f"Error saving server state: {str(e)}"

@mcp.tool()
def save_profile(profile_name: str, client: str = None) -> str:
    """
    Save the current configuration as a profile (preset) under the given name.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    try:
        # Force overwrite for simplicity; adjust as needed
        manager.save_preset(profile_name, force=True)
        return f"Profile '{profile_name}' saved successfully."
    except Exception as e:
        return f"Error saving profile '{profile_name}': {str(e)}"

@mcp.tool()
def load_profile(profile_name: str, client: str = None) -> str:
    """
    Load a profile (preset) into the current configuration.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
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
            result = manager.enable_server_noninteractive(server, version_number=ver)
            results[server] = result
        except Exception as e:
            results[server] = f"Error: {str(e)}"
    return f"{results}, please restart the client to apply changes."

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
                comment=f"Configuration before disable (bulk operation) at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            del config[manager.servers_key][server]
            manager.write_config(config)
            results[server] = "Disabled successfully, please restart the client to apply changes."
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

@mcp.tool()
def list_server_versions(server_name: str, client: str = None) -> dict:
    """
    List all available versions for the given server.
    Returns a dictionary with the server name and a list of versions.
    If no state is ever saved, the list will be empty.
    Each version includes its index, hash, timestamp, comment, and config content.
    The optional 'client' parameter uses the default client if not specified.
    """
    manager = ClientManager().get_client(client)
    try:
        versions = manager.get_server_versions(server_name)
        version_list = []
        for idx, version in enumerate(versions, start=1):
            version_list.append({
                "index": idx,
                "hash": version.hash,
                "timestamp": version.timestamp,
                "comment": version.comment#,
                # "config": version.config  # Uncomment this if you prefer to return the full config.
            })
        return {"server": server_name, "versions": version_list}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
