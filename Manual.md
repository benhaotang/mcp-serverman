> [!WARNING]
> This tool is still in development and may not be stable and subject to changes. 

> [!IMPORTANT]  
> I always recommend making a manual backup of the mcp configuration before making any changes. Although I tried to cover some error handling in the code, it is definitely not inclusive.

# Installation

1. Install the package with pip:
```bash
pip install mcp-serverman 
```
or from GitHub (for the latest debug version):
```bash
pip install git+https://github.com/benhaotang/mcp-serverman.git
```
2. Check available functions with:
```bash
$ mcp-serverman
Usage: mcp-serverman [OPTIONS] COMMAND [ARGS]...

  Claude Server Configuration Manager

Options:
  --help  Show this message and exit.

Commands:
  change   Change server configuration or list versions.
  disable  Disable a specific server.
  enable   Enable a specific server.
  list     List servers (default: all servers).
  preset   Manage configuration presets.
  remove   Remove a server version or entire server.
  save     Save current state of a server.
```
3. Initialize client management system (required for the first time since version 0.1.9):
```bash
mcp-serverman client init
```

**I always recommend making a manual backup of the mcp configuration before making any changes. Although I tried to cover some error handling in the code, it is definitely not inclusive.**

# Storage Structure

Everything is stored in the official Claude config directory under '.history' folder
```
- Claude Config directory
   - .history
      - servers_registry.json # a comprehensive list of all servers with their versions
      - preset-xxx.json # stored presets also in proper mcp config format for easy modification
      - preset-xxx.json
      - ...
   - claude_desktop_config.json
   - ...
```

# Commands

## List Servers
Display all servers and their current status:
```bash
mcp-serverman list           # Show all servers
mcp-serverman list --enabled  # Show only enabled servers
mcp-serverman list --disabled # Show only disabled servers
```

The output shows in a table format of following columns:
- Server name
- Status (enabled/disabled)
- Number of versions stored
- Current configuration hash (for enabled servers)

## Enable Server
Enable a server with a specific version:
```bash
# Interactive mode for version selection
mcp-serverman enable <server_name>
# Specific version           
mcp-serverman enable <server_name> --version <number>
# Specific version by hash
mcp-serverman enable <server_name> --hash <hash>
```

When enabling a server:
- The server config is added to the Claude mcp json configuration file.

## Disable Server
Disable an active server:
```bash
mcp-serverman disable <server_name>
```

When disabling a server:
- The current configuration is saved as a new version if it differs from the last saved version
- The server is removed from the Claude mcp json configuration file.

## Change Server Configuration
View or change server configurations:
```bash
# Interactive mode for version selection
mcp-serverman change <server_name>
# List all versions of a server
mcp-serverman change <server_name> --list
# Change to a specific version by number
mcp-serverman change <server_name> --version <number>
# Change to a specific version by hash
mcp-serverman change <server_name> --hash <hash>
```

The output shows in a series of tables with following columns:
- Version number
- Hash
- Timestamp
- Comment (if any)
- Full configuration

## Save Server State
Save the current config of a server as a version:
```bash
# Save without comment, a timestamp will be saved instead
mcp-serverman save <server_name>
# Save with custom comment
mcp-serverman save <server_name> --comment "Your comment here"
```

## Remove Server Version
Remove a specific version or the entire server:
```bash
# Remove specific version by number
mcp-serverman remove <server_name> --version <number>
# Remove specific version by hash
mcp-serverman remove <server_name> --hash <hash>
# Remove entire server FOREVER (will prompt for confirmation)
mcp-serverman remove <server_name>
```

When removing:
- Removing a specific version keeps other versions intact
- Removing the last version of a server will prompt to remove the entire server
- Removing an entire server requires confirmation and is irreversible

## Preset/Profile Management system
Manage configuration presets for multiple servers:

### Save Preset/Profile
Save current server configurations as a preset (in /path/to/claude_confg/.history/preset-preset_name.json):

```bash
# preset_name MUST be a valid filename without spaces
mcp-serverman preset save <preset_name>
```

What is saved?
- All currently enabled servers and their configurations
- Version hashes for servers

### Load Preset/Profile
```bash
mcp-serverman preset load <preset_name>
```
If a server or a server version in the preset is not found, you will be asked to change to another version or restore it from a preset file.

> [!TIP]
> - All preset files are stored in the Claude config directory under '.history' folder, in the format of:
> ```json
> "xxx": {
>      "config": {
>        "command": "xxx",
>        "args": [
>          "xxx"
>        ],
>        "env": {
>          "xxx": "xxx"
>        }
>      },
>      "hash": "xxxxxxxx"
>     }
> ```
> - You can manually edit the preset files to change configurations or add new ones.
> - You can also use preset files to restore on a fresh Claude installation.

### Delete Preset/Profile
```bash
mcp-serverman preset delete <preset_name>
```

### List Presets/Profiles
```bash
mcp-serverman preset list
```

The output shows in a table format:
- Preset name
- Number of servers included
- Last modified timestamp

## Client Management Extension (since version 0.1.9)

All previous commands now support a `--client` option to specify which client's configuration to manage. If not specified, the default client will be used.

```bash
# Example: List servers for a specific client
mcp-serverman list --client cline

# Example: Save preset for a specific client
mcp-serverman preset save mypreset --client claude
```

### Initialize Client Management

This is a global initialize or reset the client management system(**required for the first time since version 0.1.9**):
```bash
mcp-serverman client init
```

The global initialization file is stored in the user config location:
  - Linux: `~/.config/mcp-serverman/`
  - Windows: `~/mcp-serverman/`
  - MacOS: `~/Library/Application Support/mcp-serverman/`

### List Clients
Display all registered clients and their status:
```bash
mcp-serverman client list
```

The output shows in a table format with following columns:
- Short Name (used in CLI commands)
- Name (display name)
- Config Path
- Servers Key
- Status (default/system)

### Add New Client
Add a new client configuration:
```bash
# Interactive mode
mcp-serverman client add
# Direct mode
mcp-serverman client add short_name --name "Display Name" --path "/path/to/config.json" --key "mcpServers" [--default]
```

Options:
- `--name`: Display name for the client
- `--path`: Path to client's config file
- `--key`: Key name for servers in config file (e.g., "mcpServers" for Claude)
- `--default`: Set as default client

### Modify Client
Modify an existing client's configuration:
```bash
mcp-serverman client modify short_name [options]
```

Options:
- `--name`: Change display name
- `--path`: Change config file path
- `--key`: Change servers key name
- `--default`: Set as default client

Note: The "system" client cannot be modified.

### Remove Client
Remove a client from management:
```bash
mcp-serverman client remove short_name
```

Note: The "system" client cannot be removed.

### Copy Client Configuration
Copy or merge server configurations and presets between clients:
```bash
mcp-serverman client copy --from source_client --to target_client [options]
```

Options:
- `--merge`: Merge configurations instead of copying
  - When merging, for servers with same version hash, will only keep the one with newer timestamp
- `--force`: Force overwrite target configuration

> [!TIP]
> - This will not modify the original target client configurations for safety reasons. 
> - You can then restore to the target client with a preset or server save state made from source client.
> - In this way, you can always use the system client as a backup or a template for new clients.

### Examples

1. Initialize and add a new client:
```bash
# Initialize client management
mcp-serverman client init

# Add cline as a client
mcp-serverman client add cline --name "Roo Cline" --path "/home/$(whoami)/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json" --key "mcpServers"
```

2. Copy configurations between clients:
```bash
# Copy Claude's servers to cline
mcp-serverman client copy --from claude --to cline

# Merge configurations with newer versions
mcp-serverman client copy --from claude --to cline --merge
```

3. Switch default client:
```bash
# Set cline as default client
mcp-serverman client modify cline --default

# Now commands will use cline by default
mcp-serverman list  # Lists cline's mcp servers
```

## Version Control

The tool maintains a version history of server configurations:
- New versions are only created when configurations actually change
- Each version has a unique hash for identification
- Timestamps and optional comments help track changes
- All versions are preserved and can be restored at any time (**if servers_registry.json is not corrupted**)

## Examples

1. Enable a server interactively:
```bash
$ mcp-serverman change playwright --list
                             Version 1                             
┌───────────┬─────────────────────────────────────────────────────┐
│ Hash      │ 027e4f89                                            │
│ Timestamp │ 20250118_181306                                     │
│ Comment   │ Configuration before disable at 2025-01-18 18:13:06 │
└───────────┴─────────────────────────────────────────────────────┘
╭───────────────── Configuration ───────────────────╮
│ {                                                 │
│   "command": "npx",                               │
│   "args": [                                       │
│     "-y",                                         │
│     "@executeautomation/playwright-mcp-server"    │
│   ]                                               │
│ }                                                 │
╰───────────────────────────────────────────────────


                             Version 2                             
┌───────────┬─────────────────────────────────────────────────────┐
│ Hash      │ 0dcc54ea                                            │
│ Timestamp │ 20250118_182054                                     │
│ Comment   │ Configuration before disable at 2025-01-18 18:20:54 │
└───────────┴─────────────────────────────────────────────────────┘
╭───────────────── Configuration ───────────────────╮
│ {                                                 │
│   "command": "npx",                               │
│   "args": [                                       │
│     "-y",                                         │
│     "@executeautomation/playwright-mcp-server"    │
│     "-config",                                    │
│     "config.cfg"                                  │
│   ]                                               │
│ }                                                 │
╰───────────────────────────────────────────────────┘

Multiple versions available. Please specify version number: 1
Enabled server: playwright
```

2. Change server configuration:
```bash
$ mcp-serverman change playwright --list
[displays all versions]
$ mcp-serverman change playwright --version 2
Server 'playwright' is currently disabled. Would you like to enable it with this version? [y/N]: y
Enabled server 'playwright' with specified version
```

3. List all servers:
```bash
$ mcp-serverman list
┌─────────────┬──────────┬──────────┬───────────────┐
│ Server Name │ Status   │ Versions │ Current Hash  │
├─────────────┼──────────┼──────────┼───────────────┤
│ playwright  │ enabled  │ 2        │ abc123def     │
└─────────────┴──────────┴──────────┴───────────────┘
```