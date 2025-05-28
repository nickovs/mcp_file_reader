# MCP File Reader

A Model Context Protocol (MCP) service that extracts text content from files using Apache Tika. This service provides a single tool that can read various file formats (PDF, Word, Excel, PowerPoint, images with OCR, and more) and return their text content.

## Features

- **File Content Extraction**: Reads files and extracts text using Apache Tika
- **Multiple Format Support**: Supports PDF, DOCX, XLSX, PPTX, images, and many other formats
- **Automatic Tika Management**: Automatically starts and manages Tika server when needed
- **Simple Deployment**: Easy installation and setup using uv
- **Directory Access Control**: Configurable allowed directories for secure file access
- **Path Traversal Protection**: Prevents access outside allowed directories via path traversal attacks
- **Environment Configuration**: Configurable Tika server endpoint and allowed directories
- **Error Handling**: Comprehensive error handling for missing files, network issues, etc.

## Installation

### Using uv (Recommended)

```bash
# Install the package
uv pip install .

# Or install directly from the repository
uv pip install git+https://github.com/your-org/mcp-file-reader.git
```

### Using pip

```bash
# Install the package
pip install .

# Or install in development mode
pip install -e .
```

## Usage

### Quick Start

The service automatically manages Tika for you. Simply run:

```bash
mcp-file-reader
```

The service will:
1. Check if Tika is already running on localhost:9998
2. If not found, automatically start a Tika Docker container
3. Begin accepting MCP requests

### Manual Tika Configuration

If you prefer to manage Tika yourself, set the `TIKA_URL` environment variable:

```bash
# Start your own Tika server
docker run -p 9998:9998 apache/tika:latest-full

# Run the MCP service with custom Tika URL
export TIKA_URL=http://localhost:9998
mcp-file-reader
```

## MCP Client Configuration

To use this service with an MCP-enabled client (like Claude Desktop), add the following to your `server_config.json`:

### Basic Configuration

```json
{
  "servers": {
    "mcp-file-reader": {
      "command": "mcp-file-reader"
    }
  }
}
```

### With Custom Tika URL

```json
{
  "servers": {
    "mcp-file-reader": {
      "command": "mcp-file-reader",
      "env": {
        "TIKA_URL": "http://localhost:9998"
      }
    }
  }
}
```

### Development Configuration

```json
{
  "servers": {
    "mcp-file-reader": {
      "command": "python",
      "args": ["/path/to/mcp_file_reader/src/mcp_file_reader.py"]
    }
  }
}
```

## Available Tools

### `read_file_content`

Extracts text content from a file using Apache Tika. The file must be within an allowed directory.

**Parameters:**
- `file_path` (string, required): Absolute path to the file to read and extract text from. Must be within allowed directories.

**Example:**
```json
{
  "name": "read_file_content",
  "arguments": {
    "file_path": "/Users/yourname/Documents/document.pdf"
  }
}
```

**Returns:**
- Success: The extracted text content
- Error: Error message describing what went wrong (access denied, file not found, etc.)

### `list_allowed_directories`

Lists the directories that this service is allowed to access.

**Parameters:**
- None

**Example:**
```json
{
  "name": "list_allowed_directories",
  "arguments": {}
}
```

**Returns:**
- JSON object containing the list of allowed directories and a description

## Supported File Formats

Thanks to Apache Tika, this service supports:
- **Documents**: PDF, DOC, DOCX, RTF, ODT
- **Spreadsheets**: XLS, XLSX, ODS, CSV
- **Presentations**: PPT, PPTX, ODP
- **Images**: PNG, JPG, GIF, TIFF (with OCR)
- **Text**: TXT, XML, HTML, JSON
- **Archives**: ZIP, TAR, 7Z (extracts text from contained files)
- **And many more...**

## Configuration

### Environment Variables

- `TIKA_URL`: URL of the Apache Tika server (optional, defaults to auto-managed Tika)
- `MCP_ALLOWED_DIRECTORIES`: Colon, semicolon, or comma-separated list of directories that the service is allowed to access (optional, defaults to current working directory)

**Examples:**
```bash
# Single directory
export MCP_ALLOWED_DIRECTORIES="/Users/yourname/Documents"

# Multiple directories (colon-separated on Unix)
export MCP_ALLOWED_DIRECTORIES="/Users/yourname/Documents:/Users/yourname/Downloads"

# Multiple directories (semicolon-separated)
export MCP_ALLOWED_DIRECTORIES="/Users/yourname/Documents;/Users/yourname/Downloads"

# Multiple directories (comma-separated)
export MCP_ALLOWED_DIRECTORIES="/Users/yourname/Documents,/Users/yourname/Downloads"
```

### Security Model

The service implements directory-based access control:

1. **Allowed Directories**: Files can only be accessed if they are within configured allowed directories
2. **Path Traversal Protection**: Prevents access to files outside allowed directories via `../` or symlink attacks
3. **Absolute Path Requirement**: All file paths must be absolute paths
4. **Default Access**: If no directories are configured, only the current working directory is accessible

### Requirements

- **Python**: 3.8 or higher
- **Docker**: Required for automatic Tika management (if not providing custom `TIKA_URL`)

## Development

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcp_file_reader
   ```

2. **Install in development mode**:
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Run the service**:
   ```bash
   python src/mcp_file_reader.py
   ```

### Testing

Run the test suite:

```bash
# Install test dependencies
uv pip install ".[dev]"

# Run tests
pytest tests/ -v
```

### Manual Testing

```bash
# Test the service
python scripts/simple_mcp_test.py
```

## How It Works

1. **Automatic Tika Management**: When started, the service checks if Tika is running on the default port (9998)
2. **Auto-Start**: If no Tika server is found and no `TIKA_URL` is provided, it automatically starts a Tika Docker container
3. **File Processing**: When a file read request comes in, it sends the file to Tika for text extraction
4. **Clean Shutdown**: When the service stops, it automatically shuts down any Tika containers it started

## Error Handling

The service handles various error conditions:
- **File not found**: Returns clear error message
- **Path is directory**: Validates that path points to a file
- **Tika server errors**: Handles and reports Tika service failures
- **Network timeouts**: 30-second timeout for Tika requests
- **Permission errors**: Reports file access permission issues
- **Docker errors**: Reports issues starting Tika container

## Security Considerations

- No file modification or deletion capabilities
- Service only reads files from the local filesystem
- Automatically manages Tika server lifecycle for security
- Ensure Docker is properly secured in production environments

## Troubleshooting

### Common Issues

1. **"Docker not found" errors**:
   - Ensure Docker is installed and running
   - Check that `docker` command is available in PATH
   - Try providing a custom `TIKA_URL` to use external Tika

2. **"File not found" errors**:
   - Ensure files exist at the specified absolute path
   - Verify file permissions are readable by the service

3. **Tika connection errors**:
   - Check that port 9998 is available for automatic Tika startup
   - Verify Docker has permission to bind to ports
   - Try using a custom `TIKA_URL` with external Tika

4. **MCP communication issues**:
   - Ensure no extra output is being sent to stdout (service logs to stderr)
   - Check that the MCP client is using the correct configuration

### Logs

The service logs to stderr to avoid interfering with MCP stdio communication:

```bash
# View logs while running
mcp-file-reader 2> mcp-file-reader.log

# Or redirect stderr to see logs
python src/mcp_file_reader.py 2>&1 | grep -v "^{"
```

## License

This project is open source. Please check individual dependencies for their respective licenses.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request