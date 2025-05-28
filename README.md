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

## Installation and usage

Since this package is designed to be used as an MCP service, it is typically installed by
inserting an entry into the configuration of your MCP client. The examples below are for
the `claude_desktop_confoig.json` settings for the Claude Desktop app, but the general content
of the settings should be the same for other applications.

### Using uvx (Recommended)

Insert the `"file-reader"` stanza below into your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "uvx",
      "args": [
        "mcp-file-reader",
        "/Users/your_name/Desktop",
        "/Users/your_name/Downloads",
        "/Users/your_name/other_accessible_directory"
      ]
    }
  }
}
```

### Running from a local development copy

Check out the latest source using:
```bash
cd /Users/your_name/source_path
git clone https://github.com/nickovs/mcp_file_reader.git
```

Then insert the `"file-reader"` stanza below into your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--from",
        "/Users/your_name/source_path/mcp_file_reader",
        "mcp-file-reader",
        "/Users/your_name/Desktop",
        "/Users/your_name/Downloads",
        "/Users/your_name/other_accessible_directory"
      ]
    }
  }
}
```


## Manual Tika Configuration

If you prefer to manage Tika yourself, set the `TIKA_URL` environment variable:

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "uvx",
      "env": {
        "TIKA_URL": "http://some.tika.server:9998"
      },
      "args": [
        "mcp-file-reader",
        "/Users/your_name/Desktop",
        "/Users/your_name/Downloads",
        "/Users/your_name/other_accessible_directory"
      ]
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

# Multiple directories, space separated
export MCP_ALLOWED_DIRECTORIES="/Users/yourname/Documents /Users/yourname/Downloads"
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
   git clone https://github.com/nickovs/mcp_file_reader.git
   cd mcp_file_reader
   ```

2. **Install in development mode**:
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Run the service**:
   See the [example above](#running-from-a-local-development-copy) for running the code from 
   a local development copy.

### Testing

Run the test suite:

```bash
# Install test dependencies
uv pip install ".[dev]"

# Run tests
./run_tests.sh
```
