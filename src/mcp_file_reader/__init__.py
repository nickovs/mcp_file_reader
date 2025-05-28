#!/usr/bin/env python3
"""
MCP File Reader Service

An MCP (Model Context Protocol) service that extracts text content from files using Apache Tika.
Provides secure, directory-controlled file reading with automatic Tika server management.

Features:
- Automatic Tika Docker container management
- Directory-based access control with path traversal protection
- Support for various file formats through Apache Tika
- Clean shutdown and resource management
- Security validation for all file access requests

Usage:
    mcp-file-reader [--tika-url URL] [--image IMAGE] [DIRECTORIES...]

Environment Variables:
    TIKA_URL: Remote Tika service URL (optional)
    TIKA_IMAGE: Docker image to use for Tika (optional)
    MCP_ALLOWED_DIRECTORIES: Space-separated list of allowed directories
"""

import logging
import os
import shlex
import sys
import time
import atexit

from dataclasses import dataclass
from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import List

import click
import docker
from docker.models.containers import Container

import httpx
from mcp.server.fastmcp import Context, FastMCP

# Configure logging to stderr to avoid interfering with MCP stdio communication
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Default Tika Docker image with full feature set
DEFAULT_TIKA_IMAGE = "apache/tika:latest-full"

# Global reference to Docker container for cleanup
docker_container: Container | None = None

@dataclass
class ConfigGlobals:
    """Global configuration for the MCP service.
    
    Attributes:
        tika_url: URL of remote Tika service (if using external service)
        tika_image: Docker image name for Tika container (if using local container)
        allowed_dirs: List of directories that file access is restricted to
    """
    tika_url: str
    tika_image: str
    allowed_dirs: List[Path]


# Global configuration instance
config: ConfigGlobals | None = None


@dataclass
class AppContext:
    """Runtime application context for MCP session.
    
    Provides access to Tika service and directory access control.
    
    Attributes:
        tika_url: URL of the Tika service to use for text extraction
        allowed_dirs: List of directories that file access is permitted within
    """
    tika_url: str
    allowed_dirs: List[Path]

    def path_allowed(self, path: Path | str) -> bool:
        """Check if a file path is within allowed directories.
        
        Performs security validation including:
        - Path normalization and resolution
        - Check against all allowed directories
        - Protection against path traversal attacks
        
        Args:
            path: File path to validate (string or Path object)
            
        Returns:
            True if path is within allowed directories, False otherwise
        """
        if not isinstance(path, Path):
            path = Path(path)
        # Resolve to absolute path to prevent path traversal attacks
        path = path.resolve()
        
        # Check if path is within any allowed directory
        for allowed_dir in self.allowed_dirs:
            if path.is_relative_to(allowed_dir):
                return True
        return False

def check_allowed_directories(allowed_dirs: List[str] | None = None) -> List[Path]:
    """Validate and normalize allowed directories for file access control.
    
    Processes directory list from command line arguments or environment variables,
    ensuring all paths are valid, accessible directories.
    
    Args:
        allowed_dirs: List of directory paths to allow access to.
                     If None, reads from MCP_ALLOWED_DIRECTORIES env var.
                     If env var is empty, defaults to current directory.
    
    Returns:
        List of validated Path objects for allowed directories
        
    Security Notes:
        - All paths are resolved to absolute paths
        - Symlinks are resolved to prevent bypass attempts
        - Non-existent directories are filtered out with warnings
    """
    if not allowed_dirs:
        # Check environment variable for allowed directories
        allowed_dirs_env = os.getenv("MCP_ALLOWED_DIRECTORIES", "")
        if allowed_dirs_env:
            # Use shlex to properly handle quoted paths with spaces
            allowed_dirs = shlex.split(allowed_dirs_env)
        else:
            # Default to current directory if no configuration provided
            allowed_dirs = ['.']

    checked_dirs = []

    # Normalize and validate each directory path
    for dir_path in allowed_dirs:
        dir_path = dir_path.strip()
        if dir_path:
            try:
                # Convert to absolute path and resolve any symlinks for security
                abs_path = Path(dir_path).resolve()
                if abs_path.is_dir():
                    checked_dirs.append(abs_path)
                else:
                    logger.warning(f"Allowed directory does not exist: {dir_path}")
            except Exception as e:
                logger.warning(f"Invalid directory path {dir_path}: {e}")

    return checked_dirs


@atexit.register
def docker_cleanup() -> None:
    """Clean up Docker container on service shutdown.
    
    Ensures that any Tika Docker container started by this service
    is properly stopped when the service exits, preventing dangling containers.
    """
    if docker_container:
        logger.warning("Cleaning up dangling docker container")
        docker_container.stop(timeout=5)
        logger.warning("Container removed")


@asynccontextmanager
async def make_app_context(server: FastMCP) -> AsyncIterator[AppContext]:
    """Create application context with Tika service management.
    
    Manages the lifecycle of either a remote Tika service connection or
    a local Docker container running Tika. Provides clean startup and
    shutdown handling.
    
    Args:
        server: FastMCP server instance (unused but required by interface)
        
    Yields:
        AppContext: Configured application context with Tika URL and allowed directories
        
    Raises:
        Exception: If configuration is invalid or Tika service cannot be started
        ValueError: If both tika_url and tika_image are specified
    """
    global config
    global docker_container

    _ = server  # Unused parameter

    if config is None:
        raise Exception("Internal error: No config set")

    # Validate configuration - cannot specify both URL and image
    if config.tika_image and config.tika_url:
        raise ValueError("Cannot specify both tika_url and tika_image")

    # Set default image if neither URL nor image specified
    if not config.tika_image and not config.tika_url:
        config.tika_image = DEFAULT_TIKA_IMAGE

    container = None

    # Use external Tika service if URL provided
    if config.tika_url is not None:
        logger.info("Using remote Tika service: %s", config.tika_url)
        ctx = AppContext(tika_url=config.tika_url, allowed_dirs=config.allowed_dirs)
        yield ctx
    else:
        # Start local Tika Docker container
        try:
            logger.info("Starting Docker Tika service: %s", config.tika_image)
            client = docker.from_env()
            
            # Run Tika container with automatic port mapping
            container = client.containers.run(
                config.tika_image,
                detach=True,
                remove=True,  # Auto-remove when stopped
                ports={
                    '9998/tcp': None  # Map to random host port
                }
            )
            docker_container = container

            logger.debug("Started container %s", container.id)

            # Wait for container to be ready and get assigned port
            for i in range(10):
                time.sleep(1)
                container.reload()
                
                # Check if container is running and port is assigned
                if (
                        container.status == "running" and
                        (ports := container.attrs['NetworkSettings']['Ports']) and
                        '9998/tcp' in ports and
                        len(ports['9998/tcp']) and
                        'HostPort' in ports['9998/tcp'][0]
                ):
                    break
                logger.info("Waiting for container startup, status: %s", container.status)
            else:
                raise Exception("Failed to start Docker Tika service within timeout")

            # Extract the assigned host port
            port = container.attrs['NetworkSettings']['Ports']['9998/tcp'][0]['HostPort']
            logger.info("Tika service available on port %s", port)
            
            yield AppContext(tika_url=f"http://localhost:{port}", allowed_dirs=config.allowed_dirs)
        finally:
            # Clean up Docker container
            if container:
                logger.info("Stopping Docker Tika service")
                container.stop(timeout=5)
            docker_container = None


# Initialize FastMCP server with application context management
mcp = FastMCP("mcp-file-reader", lifespan=make_app_context)


@mcp.tool("list_allowed_directories")
async def list_allowed_directories(ctx: Context) -> List[str]:
    """List directories that this service is allowed to access.
    
    Returns the configured list of directories that file reading operations
    are restricted to. This helps clients understand the scope of available
    file access.
    
    Args:
        ctx: MCP request context
        
    Returns:
        List of absolute directory paths as strings
    """
    app_ctx = ctx.request_context.lifespan_context
    return [str(dir_path) for dir_path in app_ctx.allowed_dirs]


@mcp.tool("read_file_content")
async def read_file_content(path: str, ctx: Context) -> str:
    """Extract text content from a file using Apache Tika.
    
    Reads a file from the filesystem and extracts its text content using
    Apache Tika, which supports a wide variety of file formats including
    PDF, Word documents, images with OCR, and many others.
    
    Security features:
    - Path validation against allowed directories
    - Protection against path traversal attacks
    - File existence and type validation
    
    Args:
        path: Absolute or relative path to the file to read
        ctx: MCP request context containing application state
        
    Returns:
        Extracted text content from the file, or error message if operation fails
        
    Supported file types:
        PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, TXT, RTF, HTML, XML,
        images (with OCR), and many other formats supported by Apache Tika
    """
    app_ctx = ctx.request_context.lifespan_context

    path_obj = Path(path)

    # Security validation: check if path is within allowed directories
    if not app_ctx.path_allowed(path_obj):
        return f"Error: Access denied. File '{path}' not within allowed directories: {[str(d) for d in app_ctx.allowed_dirs]}"
    
    # File existence and type validation
    if not path_obj.exists():
        return f"Error: File '{path}' does not exist"
    if not path_obj.is_file():
        return f"Error: Path '{path}' is not a regular file"

    try:
        # Read file content as binary data for Tika
        with open(path, "rb") as f:
            file_content = f.read()

        # Send file to Tika service for text extraction
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{app_ctx.tika_url}/tika",
                content=file_content,
                headers={"Accept": "text/plain"},  # Request plain text output
                timeout=30.0,  # 30 second timeout for large files
            )

            if response.status_code == 200:
                extracted_text = response.text
                logger.debug(f"Successfully extracted {len(extracted_text)} characters from {path}")
                return extracted_text
            else:
                error_msg = f"Tika extraction failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return error_msg

    except Exception as e:
        error_msg = f"Error reading text from file {path}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Error details:", exc_info=e)
        return error_msg


@click.command()
@click.option(
    "-u", "--tika-url",
    default=None,
    envvar='TIKA_URL',
    type=str,
    help="Remote Tika service URL (if not provided, starts local Docker container)"
)
@click.option(
    "--image",
    default=None,
    envvar='TIKA_IMAGE',
    type=str,
    help="Docker image for local Tika service (default: apache/tika:latest-full)"
)
@click.argument(
    "directories",
    nargs=-1,
    type=click.Path(exists=True),
    required=False,
    envvar=""
)
def main_sync(tika_url: str, image: str, directories: List[str]):
    """MCP service for extracting text content from files using Apache Tika.
    
    This service provides secure file reading capabilities with directory-based
    access control. It automatically manages a local Tika Docker container or
    connects to a remote Tika service.
    
    DIRECTORIES: Optional list of directories to allow file access within.
                If not provided, uses MCP_ALLOWED_DIRECTORIES environment variable
                or defaults to current directory.
    
    Examples:
        # Start with current directory access
        mcp-file-reader
        
        # Allow access to specific directories
        mcp-file-reader /home/user/documents /tmp
        
        # Use remote Tika service
        mcp-file-reader --tika-url https://tika.example.com:9998
        
        # Use specific Docker image
        mcp-file-reader --image apache/tika:2.9.1-full
    """
    global config

    # Initialize global configuration
    config = ConfigGlobals(
        tika_url=tika_url,
        allowed_dirs=check_allowed_directories(directories),
        tika_image=image,
    )
    
    # Start the MCP server
    mcp.run()


if __name__ == "__main__":
    main_sync()
