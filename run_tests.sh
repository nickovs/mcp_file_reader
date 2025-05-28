#!/bin/bash

# Test runner script for MCP File Reader
# Creates a temporary virtual environment, installs dependencies, and runs tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting MCP File Reader Test Suite${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}📁 Project root: ${PROJECT_ROOT}${NC}"

# Create temporary directory for testing
TEMP_DIR=$(mktemp -d -t mcp-file-reader-test-XXXXXX)
echo -e "${BLUE}🗂️  Created temporary directory: ${TEMP_DIR}${NC}"

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up temporary directory: ${TEMP_DIR}${NC}"
    rm -rf "$TEMP_DIR"
}

# Register cleanup to run on script exit
trap cleanup EXIT

cd "$TEMP_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed. Please install uv first.${NC}"
    echo -e "${YELLOW}Install with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Creating virtual environment with uv...${NC}"
uv venv test-env

echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source test-env/bin/activate

echo -e "${BLUE}⬇️  Installing mcp-file-reader from local source...${NC}"
uv pip install -e "$PROJECT_ROOT"

echo -e "${BLUE}⬇️  Installing test requirements...${NC}"
uv pip install -r "$PROJECT_ROOT/tests/requirements.txt"

echo -e "${BLUE}📋 Installed packages:${NC}"
uv pip list

# Check if Docker is available and running
echo -e "${BLUE}🐳 Checking Docker availability...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker is not installed. The test may fail if Tika server is needed.${NC}"
elif ! docker info &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker is not running. The test may fail if Tika server is needed.${NC}"
else
    echo -e "${GREEN}✅ Docker is available and running${NC}"
fi

echo -e "${BLUE}🧪 Running MCP File Reader tests...${NC}"
echo -e "${BLUE}Working directory for tests: ${PROJECT_ROOT}${NC}"

# Copy test files to temp directory for isolation
cp -r "$PROJECT_ROOT/test_files" ./ 2>/dev/null || echo -e "${YELLOW}⚠️  No test_files directory found${NC}"

# Run the test
cd "$PROJECT_ROOT"
python tests/test_mcp_client.py

echo -e "${GREEN}🎉 All tests completed successfully!${NC}"