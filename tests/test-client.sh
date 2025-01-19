#!/bin/bash
set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# Print step information
step() {
    echo -e "\n${GREEN}Step: $1${NC}"
}

# Create test directory
TEST_DIR="./testtemp"
mkdir -p "$TEST_DIR"

# Create sample MCP config file
step "Creating sample MCP config file"
cat > "$TEST_DIR/test_config.json" << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@executeautomation/playwright-mcp-server"
      ]
    }
  }
}
EOF

echo "Created test config at $TEST_DIR/test_config.json"

# Initialize MCP server manager
step "Initializing MCP server manager"
mcp-serverman client init

# Add test client
step "Adding test client"
mcp-serverman client add test --name "Test Client" --path "$TEST_DIR/test_config.json" --key "mcpServers"

# List all clients
step "Listing all clients"
mcp-serverman client list

# List servers in test client
step "Listing servers in test client"
mcp-serverman list --client test

# Copy config from Claude
step "Copying config from Claude"
mcp-serverman client copy --from claude --to test --merge

# Save a default preset from Claude
step "Saving default preset from Claude"
mcp-serverman preset save default --client claude

# List and load the default preset
step "Loading default preset"
mcp-serverman preset list --client test
mcp-serverman preset load default --client test

# Modify config and save new preset
step "Modifying config and saving new preset"
sed -i 's/"-y"/"-t"/g' "$TEST_DIR/test_config.json"
mcp-serverman preset save default --client test
cat "$TEST_DIR/.history/preset-default.json"

# Copy from Claude again to test merge
step "Copying from Claude again to test merge"
mcp-serverman client copy --from claude --to test --merge

# Display merged registry
step "Displaying merged registry"
echo "Contents of servers_registry.json:"
cat "$TEST_DIR/.history/servers_registry.json"

# Remove test client
step "Removing test client"
mcp-serverman client remove test

# Clean up
step "Cleaning up"
rm -rf "$TEST_DIR"

echo -e "\n${GREEN}Test completed successfully!${NC}"