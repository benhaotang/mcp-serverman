# mcp-serverman: A MCP Server Configuration Manager

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-serverman)](https://pypi.org/project/mcp-serverman/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-serverman)](https://pypi.org/project/mcp-serverman/) ![](https://badge.mcpx.dev 'MCP') ![](https://badge.mcpx.dev?type=server&features=tools 'MCP server with features') ![PyPI - License](https://img.shields.io/pypi/l/mcp-serverman)


A command-line tool to manage Claude MCP servers configuration with version control and profiling.

> [!IMPORTANT]  
> I always recommend making a manual backup of the mcp configuration before making any changes. Although I tried to cover some error handling in the code, it is definitely not inclusive.

## :floppy_disk:Installation

```bash
pip install mcp-serverman 
```
or from GitHub for the latest debug version:
```bash
pip install git+https://github.com/benhaotang/mcp-serverman.git
```
Should be available on Windows, Linux(tested) and MacOS. If the path for a certain platform is wrong, open an issue.

## :computer:Usage

After installation, you can use the `mcp-serverman` command directly in terminal:

```bash
# Display help message
mcp-serverman
# Initialize Client configuration(one time and must be done before using other commands, since 0.1.9)
mcp-serverman client init
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
# Multiple client support(since 0.1.9)
mcp-serverman client list
mcp-serverman client add <short_name> --name "Display Name" --path "/path/to/config.json" --key "mcpServers" [--default]
mcp-serverman client remove <short_name>
mcp-serverman client modify <short_name> --default
mcp-serverman client copy --from <short_name> --to <short_name> --merge
# Register companion mcp server to let Claude/LLM manage for you(since 0.2.1)
mcp-serverman companion [--client <client>]
```

For detailed usage instructions, see the [manual](https://github.com/benhaotang/mcp-serverman/blob/main/Manual.md).

## :wrench:Development

To install the package in development mode, clone the repository and run:

```bash
pip install -e .
```

## :checkered_flag:Roadmap

- [x] Add support for other MCP-Clients, e.g. [Cline](https://github.com/cline/cline) and [MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) (since 0.1.9)
- [x] Update the code to be more modular and easier to maintain (since v0.2.0)
- [x] Added our own mcp-server to let Claude/LLM manage for you (since 0.2.1)
- [ ] Better error handling tests
- ~~Integration with other MCP server install tools, e.g. Smithery, or with predefined installation templates (should iron out safety issues first)~~ We have so many mcp marketplaces now, just use [mcp-installer](https://github.com/anaisbetts/mcp-installer) package and instruct the model to install it for you.
- ~~Maybe a Web UI via Flask?~~

## License

MIT License [(LICENSE)](https://github.com/benhaotang/mcp-serverman/blob/main/LICENSE)
