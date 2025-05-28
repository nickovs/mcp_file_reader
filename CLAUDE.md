# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) file reader service that extracts text content from files using Apache Tika. The service uses local deployment with automatic Tika server management, implements directory-based access control for security, and is packaged for installation using uv.

## Current Structure

- `src/mcp_file_reader` - Main MCP service implementation with automatic Tika management
- `requirements.txt` - Python dependencies (legacy, use pyproject.toml)
- `pyproject.toml` - Modern Python packaging configuration for uv
- `tests/` - Test files and test requirements
- `README.md` - Updated documentation for uv-based deployment

## Deployment

### Installation with uv (Recommended)
```bash
uv pip install .
```

## How It Works

1. **Automatic Tika Management**: When no `TIKA_URL` is provided, the service automatically starts a Tika Docker using the Python docker bindings.
2. **Directory Access Control**: Configurable allowed directories with path traversal protection
3. **Security Validation**: All file access requests are validated against allowed directories
4. **Clean Shutdown**: Automatically stops any Tika containers it started when the service exits
5. **Error Handling**: Graceful handling of Docker and Tika startup failures

## Security Features

- **Directory-based Access Control**: `MCP_ALLOWED_DIRECTORIES` environment variable
- **Path Traversal Protection**: Prevents `../` attacks and symlink exploits
- **Absolute Path Validation**: All paths are resolved to absolute paths before checking
- **Two MCP Tools**: `read_file_content` (with security) and `list_allowed_directories`

## Testing
- Test requirements in `tests/requirements.txt`
- Run tests with: `pytest tests/ -v`
- Manual testing: `bash run_tests.sh`

## Important Notes
- Service logs to stderr to avoid interfering with MCP stdio communication
- Requires Docker for automatic Tika management (unless providing custom TIKA_URL)
- Tika server URL is configurable via TIKA_URL environment variable
