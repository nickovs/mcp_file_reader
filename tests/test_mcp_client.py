#!/usr/bin/env python3
"""
MCP File Reader Service Test Client

Comprehensive test suite for the MCP File Reader service using the official MCP SDK.
Tests all core functionality including connection, tool listing, directory access control,
file reading capabilities, and security features.

This test client:
- Connects to the MCP service via stdio transport
- Validates tool availability and functionality
- Tests file reading on various file formats
- Verifies directory access control and security measures
- Provides detailed test results and error reporting
- Tracks test results and exits with appropriate return codes

Usage:
    python test_mcp_client.py

Requirements:
    - MCP service must be installed and available as 'mcp-file-reader' command
    - Test files should be present in '../test_files/' directory
    - Docker must be available for Tika container management
"""

import asyncio
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPFileReaderTester:
    """Test client for MCP File Reader service using the official MCP SDK.
    
    Provides a high-level interface for testing MCP service functionality,
    handling connection management, tool invocation, and result processing.
    
    Attributes:
        session: Active MCP client session (None when disconnected)
        exit_stack: Async context manager for resource cleanup
    """
    
    def __init__(self):
        """Initialize the test client with no active connections."""
        self.session = None
        self.exit_stack = None
    
    async def connect_to_service(self, working_dir: str):
        """Connect to the MCP file reader service.
        
        Establishes a stdio-based connection to the MCP service, configures
        allowed directories, and initializes the client session.
        
        Args:
            working_dir: Directory path to set as allowed for file access
            
        Raises:
            Exception: If connection or initialization fails
        """
        # Configure environment to restrict file access to working directory
        env = os.environ.copy()
        env["MCP_ALLOWED_DIRECTORIES"] = working_dir
        
        # Configure server parameters for stdio transport
        server_params = StdioServerParameters(
            command="mcp-file-reader",  # Command to start the MCP service
            args=[],  # No additional command line arguments
            env=env   # Environment with directory restrictions
        )
        
        # Set up async context management for clean resource handling
        self.exit_stack = AsyncExitStack()
        
        # Establish stdio transport connection to the service
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        
        # Create MCP client session over the stdio transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        # Initialize the MCP session (handshake, capability negotiation)
        await self.session.initialize()
    
    async def list_tools(self):
        """List available tools from the MCP service.
        
        Returns:
            List of tool objects with names and descriptions
            
        Raises:
            Exception: If not connected to service
        """
        if not self.session:
            raise Exception("Not connected to service")
        
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a specific tool with given arguments.
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Tool response object containing results or error information
            
        Raises:
            Exception: If not connected to service or tool call fails
        """
        if not self.session:
            raise Exception("Not connected to service")
        
        response = await self.session.call_tool(tool_name, arguments or {})
        return response
    
    async def close(self):
        """Close the connection and clean up resources.
        
        Properly shuts down the MCP session and releases all resources
        including stdio transport and any background processes.
        """
        if self.exit_stack:
            await self.exit_stack.aclose()


async def test_mcp_file_reader_service():
    """Comprehensive test suite for the MCP file reader service.
    
    Performs a complete validation of the MCP service including:
    1. Connection and initialization
    2. Tool discovery and validation
    3. Directory access control verification
    4. Recursive file reading functionality across multiple file types
    5. Security testing with restricted directory access
    6. Access control validation across directory boundaries
    
    Returns:
        tuple: (total_tests, passed_tests) for exit code determination
    
    Test results are printed to stdout with success/failure indicators.
    Attempts to complete all tests even if some fail.
    """
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent.resolve()
    working_dir = str(project_root)
    test_files_dir = project_root / "test_files"
    
    print(f"Testing MCP service with working directory: {working_dir}")
    print(f"Test files directory: {test_files_dir}")
    
    # Initialize test tracking
    total_tests = 0
    passed_tests = 0
    
    # Create MCP client
    client = MCPFileReaderTester()
    
    try:
        # Test 1: Connect to the service
        print("\n1. Testing MCP connection and initialization...")
        total_tests += 1
        try:
            await client.connect_to_service(working_dir)
            print("✓ MCP connection and initialization successful")
            passed_tests += 1
        except Exception as e:
            print(f"✗ MCP connection failed: {e}")
            return total_tests, passed_tests
        
        # Test 2: List available tools
        print("\n2. Testing tool listing...")
        total_tests += 1
        try:
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            expected_tools = ["list_allowed_directories", "read_file_content"]
            
            # Verify all expected tools are available
            missing_tools = [tool for tool in expected_tools if tool not in tool_names]
            if missing_tools:
                print(f"✗ Missing expected tools: {missing_tools}")
            else:
                print(f"✓ Found expected tools: {tool_names}")
                passed_tests += 1
        except Exception as e:
            print(f"✗ Tool listing failed: {e}")
        
        # Test 3: Check allowed directories
        print("\n3. Testing directory access control...")
        total_tests += 1
        try:
            dirs_response = await client.call_tool("list_allowed_directories")
            
            # Extract directory list from response (handle different response formats)
            allowed_dirs_response = dirs_response.content[0].text if hasattr(dirs_response.content[0], 'text') else str(dirs_response.content[0])
            
            print(f"✓ Allowed directories: {allowed_dirs_response}")
            
            # Parse response format (could be JSON list or single string)
            if isinstance(allowed_dirs_response, str):
                if allowed_dirs_response.startswith('['):
                    import json
                    allowed_dirs_list = json.loads(allowed_dirs_response)
                else:
                    # Single directory as string
                    allowed_dirs_list = [allowed_dirs_response]
            else:
                allowed_dirs_list = allowed_dirs_response
            
            # Verify that our working directory is properly configured as allowed
            working_dir_found = any(Path(d).resolve() == Path(working_dir).resolve() for d in allowed_dirs_list)
            if not working_dir_found:
                print(f"✗ Working directory {working_dir} not found in allowed directories: {allowed_dirs_list}")
            else:
                print("✓ Current working directory is accessible")
                passed_tests += 1
        except Exception as e:
            print(f"✗ Directory access control test failed: {e}")
        
        # Test 4: Test file reading on all test files (recursive)
        print(f"\n4. Testing file reading on all files in {test_files_dir} (recursive)...")
        total_tests += 1
        
        file_reading_passed = False
        try:
            if not test_files_dir.exists():
                print(f"⚠ Test files directory {test_files_dir} does not exist")
                test_files = []
            else:
                # Discover all test files recursively, excluding hidden files
                test_files = []
                for file_path in test_files_dir.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        test_files.append(file_path)
                
                if not test_files:
                    print(f"⚠ No test files found in {test_files_dir}")
            
            if test_files:
                print(f"Found {len(test_files)} test files: {[f.relative_to(test_files_dir) for f in test_files]}")
                
                successful_reads = 0
                failed_reads = 0
                
                for test_file in test_files:
                    relative_path = test_file.relative_to(test_files_dir)
                    try:
                        print(f"\n  Testing file: {relative_path}")
                        
                        # Try to read the file
                        read_response = await client.call_tool("read_file_content", {
                            "path": str(test_file)
                        })
                        
                        # Extract content from response
                        content = read_response.content[0].text if hasattr(read_response.content[0], 'text') else str(read_response.content[0])
                        
                        if content.startswith("Error:"):
                            print(f"    ✗ Failed to read {relative_path}: {content[:100]}...")
                            failed_reads += 1
                        else:
                            content_preview = content[:100].replace('\n', ' ').strip()
                            print(f"    ✓ Successfully read {relative_path} ({len(content)} chars): {content_preview}...")
                            successful_reads += 1
                            
                    except Exception as e:
                        print(f"    ✗ Exception reading {relative_path}: {e}")
                        failed_reads += 1
                
                print(f"\n✓ File reading summary: {successful_reads} successful, {failed_reads} failed")
                # Test passes if at least one file was successfully read and no failures
                if successful_reads > 0 and failed_reads == 0:
                    file_reading_passed = True
            else:
                # No test files found - consider this a pass (not a failure of the service)
                file_reading_passed = True
                
        except Exception as e:
            print(f"✗ File reading test failed: {e}")
        
        if file_reading_passed:
            passed_tests += 1
        
        # Test 5: Test access control (try to read outside allowed directory)
        print("\n5. Testing access control with unauthorized path...")
        total_tests += 1
        
        access_control_passed = False
        try:
            # Attempt to read a file outside the allowed directory tree
            unauthorized_path = "/etc/passwd"  # Common system file outside project scope
            access_response = await client.call_tool("read_file_content", {
                "path": unauthorized_path
            })
            
            # Check if access was properly denied
            content = access_response.content[0].text if hasattr(access_response.content[0], 'text') else str(access_response.content[0])
            if "Access denied" in content or "Error:" in content:
                print("✓ Access control working - unauthorized access blocked")
                access_control_passed = True
            else:
                print(f"✗ Security issue - unauthorized file was read: {content[:50]}...")
        except Exception as e:
            print(f"✓ Access control working - request rejected with exception: {e}")
            access_control_passed = True
        
        if access_control_passed:
            passed_tests += 1
        
        print(f"\n🎉 Basic tests completed: {passed_tests}/{total_tests} passed")
        
    finally:
        # Clean up: close the connection
        await client.close()
    
    # Test 6: Access control with restricted directory
    print("\n6. Testing access control with restricted sub-directory...")
    total_tests += 1
    
    restricted_access_passed = False
    test_sub_dir = test_files_dir / "test_sub_dir"
    if not test_sub_dir.exists():
        print(f"⚠ Test sub-directory {test_sub_dir} does not exist, skipping restricted access tests")
        # Consider this a pass since it's not a service failure
        restricted_access_passed = True
    else:
        # Create new client for restricted access test
        restricted_client = MCPFileReaderTester()
        
        try:
            # Connect with restricted directory access (only test_sub_dir)
            print(f"\nConnecting with restricted access to: {test_sub_dir}")
            await restricted_client.connect_to_service(str(test_sub_dir))
            print("✓ Connected with restricted directory access")
            
            # Get all test files again for access control testing
            all_test_files = []
            for file_path in test_files_dir.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    all_test_files.append(file_path)
            
            if not all_test_files:
                print("⚠ No test files found for access control testing")
                restricted_access_passed = True
            else:
                # Categorize files by access expectation
                accessible_files = [f for f in all_test_files if f.is_relative_to(test_sub_dir)]
                restricted_files = [f for f in all_test_files if not f.is_relative_to(test_sub_dir)]
                
                print(f"\nTesting {len(accessible_files)} files that should be accessible:")
                accessible_success = 0
                accessible_fail = 0
                
                for test_file in accessible_files:
                    relative_path = test_file.relative_to(test_files_dir)
                    try:
                        read_response = await restricted_client.call_tool("read_file_content", {
                            "path": str(test_file)
                        })
                        
                        content = read_response.content[0].text if hasattr(read_response.content[0], 'text') else str(read_response.content[0])
                        
                        if content.startswith("Error:"):
                            print(f"    ✗ Unexpected failure reading {relative_path}: {content[:100]}...")
                            accessible_fail += 1
                        else:
                            content_preview = content[:50].replace('\n', ' ').strip()
                            print(f"    ✓ Successfully read {relative_path}: {content_preview}...")
                            accessible_success += 1
                            
                    except Exception as e:
                        print(f"    ✗ Exception reading {relative_path}: {e}")
                        accessible_fail += 1
                
                print(f"\nTesting {len(restricted_files)} files that should be blocked:")
                blocked_success = 0
                blocked_fail = 0
                
                for test_file in restricted_files:
                    relative_path = ""
                    try:
                        relative_path = test_file.relative_to(test_files_dir)
                        read_response = await restricted_client.call_tool("read_file_content", {
                            "path": str(test_file)
                        })
                        
                        content = read_response.content[0].text if hasattr(read_response.content[0], 'text') else str(read_response.content[0])
                        
                        if "Access denied" in content or content.startswith("Error:"):
                            print(f"    ✓ Correctly blocked access to {relative_path}")
                            blocked_success += 1
                        else:
                            print(f"    ✗ Security issue: {relative_path} was accessible when it should be blocked")
                            blocked_fail += 1
                            
                    except Exception as e:
                        print(f"    ✓ Access blocked via exception for {relative_path}: {e}")
                        blocked_success += 1
                
                print(f"\n✓ Access control test summary:")
                print(f"  Accessible files: {accessible_success} success, {accessible_fail} failed")
                print(f"  Restricted files: {blocked_success} correctly blocked, {blocked_fail} security issues")
                
                if blocked_fail == 0 and accessible_fail == 0:
                    print("✓ Access control working correctly - no security issues detected")
                    restricted_access_passed = True
                else:
                    print(f"✗ Security concerns detected: {blocked_fail} files were accessible when they should be blocked")
        
        finally:
            # Clean up restricted client
            await restricted_client.close()
    
    if restricted_access_passed:
        passed_tests += 1
    
    # Final test summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    print(f"{'='*60}")
    
    if passed_tests == total_tests:
        print("✓ All tests passed successfully!")
    else:
        failed_tests = total_tests - passed_tests
        print(f"✗ {failed_tests} test(s) failed")
    
    return total_tests, passed_tests


def main():
    """Main entry point for the comprehensive test suite.
    
    Runs the full async test suite for the MCP File Reader service including:
    - Basic functionality tests with full directory access
    - Recursive file discovery and reading tests
    - Access control validation with restricted directory permissions
    
    Test results are printed to stdout with clear success/failure indicators.
    Exits with code 0 if all tests pass, 1 if any tests fail.
    """
    try:
        total_tests, passed_tests = asyncio.run(test_mcp_file_reader_service())
        
        # Exit with appropriate code
        if passed_tests == total_tests:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()