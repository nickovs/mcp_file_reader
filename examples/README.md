# MCP Server Configuration Examples

This directory contains sample MCP server configuration files for different deployment modes.

## Configuration Files

### `server_config_uv_installation.json` (Recommended)
Use this when you've installed the service using uv. This is the simplest configuration.

**Prerequisites:**
1. Install the service: `uv pip install .` or `uv pip install /path/to/mcp_file_reader`
2. Ensure Docker is installed and running (for automatic Tika management)

### `server_config_local_development.json`
Use this for local development without installing the package.

**Prerequisites:**
1. Install dependencies: `uv pip install -e ".[dev]"`
2. Ensure Docker is installed and running (for automatic Tika management)

### `server_config_custom_tika.json`
Use this when you want to manage your own Tika server instance.

**Prerequisites:**
1. Install the service: `uv pip install .`
2. Start your own Tika server: `docker run -p 9998:9998 apache/tika:latest-full`

## Usage Instructions

1. Choose the appropriate configuration file for your deployment mode
2. Copy the contents to your MCP client's server configuration file (typically `server_config.json`)
3. Update any file paths to match your local setup
4. Restart your MCP client to load the new configuration

## Path Configuration

**Important:** You may need to update paths in these configuration files:

- For development mode, replace `/path/to/mcp_file_reader` with the actual absolute path to this project
- All configurations use absolute file paths when calling the `read_file_content` tool
- For Windows users, use forward slashes or properly escaped backslashes in paths

## How It Works

### Automatic Tika Management (Default)
- The service automatically detects if Tika is running on localhost:9998
- If not found, it starts a Tika Docker container as a subprocess
- When the service stops, it automatically cleans up the Tika container
- No manual Tika management required

### Custom Tika Configuration
- Set the `TIKA_URL` environment variable to use an existing Tika server
- The service will use your Tika instance instead of starting its own
- Useful for shared Tika servers or custom configurations

## File Access and Security

The service reads files directly from your filesystem using absolute paths, with directory-based access control:

### Basic File Access
```json
{
  "name": "read_file_content",
  "arguments": {
    "file_path": "/Users/yourname/Documents/document.pdf"
  }
}
```

### Directory Access Control

By default, the service can only access files in the current working directory. To allow access to specific directories, set the `MCP_ALLOWED_DIRECTORIES` environment variable:

```json
{
  "servers": {
    "mcp-file-reader": {
      "command": "mcp-file-reader",
      "env": {
        "MCP_ALLOWED_DIRECTORIES": "/Users/yourname/Documents:/Users/yourname/Downloads"
      }
    }
  }
}
```

### List Allowed Directories

You can check which directories are accessible using the `list_allowed_directories` tool:

```json
{
  "name": "list_allowed_directories",
  "arguments": {}
}
```

### Security Features

- **Path Traversal Protection**: Prevents access outside allowed directories via `../` attacks
- **Symlink Protection**: Resolves symlinks and validates final paths
- **Absolute Path Requirement**: All file paths must be absolute
- **Access Denied Errors**: Clear error messages when access is denied

## Testing

After configuring your MCP client:

1. Test that the service is available in your MCP client
2. Try reading a test file using the `read_file_content` tool
3. Verify that text extraction works correctly

For debugging, you can run the simple test:
```bash
python scripts/simple_mcp_test.py
```

## Troubleshooting

### Common Issues

1. **"mcp-file-reader command not found"**:
   - Ensure you've installed the package: `uv pip install .`
   - Check that the installation location is in your PATH

2. **"Docker not found" errors**:
   - Ensure Docker is installed and running
   - Try using the custom Tika configuration instead

3. **Tika startup failures**:
   - Check that port 9998 is available
   - Verify Docker has permission to bind to ports
   - Use custom Tika configuration as a workaround