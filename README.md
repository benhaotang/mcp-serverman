# mcp-serverman: A MCP Server Configuration Manager

A command-line tool to manage Claude MCP servers configuration.

> [!WARNING]
> This tool is still in development and may not be stable and subject to changes. And I always recommend making a manual backup of the mcp configuration before making any changes, although I tried to cover some error handling in the code, but it is definitely not inclusive.

## Installation

```bash
pip install git+https://github.com/benhaotang/mcp-serverman.git
```

## Usage

After installation, you can use the `mcp-serverman` command directly:

```bash
# Display help message
mcp-serverman
# List servers
mcp-serverman list
mcp-serverman list --enabled
# Enable/disable/remove server/server version
mcp-serverman enable <server_name> 
mcp-serverman disable <server_name>
mcp-serverman remove <server_name>
# Version control
mcp-serverman save <server_name> --comment <comment>
mcp-serverman change <server_name> --version <version>
# Preset/Profile management
mcp-serverman preset save <preset_name>
mcp-serverman preset load <preset_name>
mcp-serverman preset delete <preset_name>
```

For detailed usage instructions, see the [manual](Manual.md).

**I always recommend making a manual backup of the mcp configuration before making any changes, although I tried to cover some error handling in the code, but it is definitely not inclusive.**

## Development

To install the package in development mode, clone the repository and run:

```bash
pip install -e .
```

## Roadmap

- [ ] Add support for other MCP-Clients, e.g. [Cline](https://github.com/cline/cline) and [MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge)
- [ ] Integration with other MCP server install tools, e.g. [Smithery](https://smithery.ai/)

## License

MIT License [(LICENSE)](LICENSE)