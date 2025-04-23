"""Tests for cargo.mcp.server functionality."""

import asyncio
import os
import pathlib
import pytest
import tempfile
import unittest.mock as mock

from cargo.mcp.server.server import (
    cargo_check,
    cargo_clippy,
    cargo_build,
    cargo_test,
    cargo_fmt,
    cargo_doc,
    cargo_run,
    cargo_tarpaulin,
)


class MockContext:
    """Mock Context for testing."""
    pass


class TestCargoTools:
    """Test suite for Cargo tools."""

    def setup_method(self):
        """Set up test environment."""
        self.ctx = MockContext()
        # Create a temporary directory with basic Cargo.toml for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cargo_toml_path = pathlib.Path(self.temp_dir.name) / "Cargo.toml"
        with open(self.cargo_toml_path, "w") as f:
            f.write("""
[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
            """)

    def teardown_method(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_cargo_path_validation(self):
        """Test path validation for all tools."""
        invalid_path = "/non/existent/path"
        
        # Test each tool with an invalid path
        tools = [
            cargo_clippy,
            cargo_check,
            cargo_build,
            cargo_test,
            cargo_fmt,
            cargo_doc,
            cargo_run,
            cargo_tarpaulin,
        ]
        
        for tool in tools:
            result = await tool(self.ctx, invalid_path)
            assert result["success"] is False
            assert "not a valid Rust project" in result["error"]
            assert result["data"] is None

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_clippy_success(self, mock_subprocess):
        """Test cargo_clippy with successful execution."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Output text", b"")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_clippy(self.ctx, self.temp_dir.name)
        
        # Verify the result
        assert result["success"] is True
        assert "Clippy completed successfully" in result["data"]["message"]
        assert "Output text" in result["data"]["output"]
        assert result["data"]["project_path"] == self.temp_dir.name
        
        # Verify the mock was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert call_args[0] == "cargo"
        assert call_args[1] == "clippy"

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_clippy_warnings(self, mock_subprocess):
        """Test cargo_clippy with warnings in output."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"", b"warning: unused variable")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_clippy(self.ctx, self.temp_dir.name)
        
        # Verify the result
        assert result["success"] is True
        assert "Clippy completed with warnings/errors" in result["data"]["message"]
        assert "warning: unused variable" in result["data"]["output"]

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_check_success(self, mock_subprocess):
        """Test cargo_check with successful execution."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Checking crate", b"")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_check(self.ctx, self.temp_dir.name)
        
        # Verify the result
        assert result["success"] is True
        assert "Cargo check completed successfully" in result["data"]["message"]
        assert "Checking crate" in result["data"]["output"]

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_fmt_check_mode(self, mock_subprocess):
        """Test cargo_fmt in check-only mode."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        # Return non-zero to simulate formatting issues found
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Formatting issues detected")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_fmt(self.ctx, self.temp_dir.name, check_only=True)
        
        # Verify the result
        assert result["success"] is True  # Should be success even with formatting issues
        assert "Formatting issues detected" in result["data"]["message"]
        assert result["data"]["needs_formatting"] is True
        
        # Verify the mock was called with --check
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert "--check" in call_args

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_build_release_mode(self, mock_subprocess):
        """Test cargo_build with release mode."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Compiling in release mode", b"")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_build(self.ctx, self.temp_dir.name, release=True)
        
        # Verify the result
        assert result["success"] is True
        assert "release" in result["data"]["build_mode"]
        
        # Verify the release flag was passed
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert "--release" in call_args

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_test_with_name_filter(self, mock_subprocess):
        """Test cargo_test with test name filter."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (
            b"test result: ok. 5 passed; 0 failed", 
            b""
        )
        mock_subprocess.return_value = process_mock
        
        test_name = "integration_test"
        result = await cargo_test(self.ctx, self.temp_dir.name, test_name=test_name)
        
        # Verify the result
        assert result["success"] is True
        
        # Verify test name was passed
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert test_name in call_args

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    @mock.patch("builtins.open")
    @mock.patch("pathlib.Path")
    async def test_cargo_doc_package_extraction(self, mock_path, mock_open, mock_subprocess):
        """Test cargo_doc package name extraction."""
        # Configure mocks
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Documentation generated", b"")
        mock_subprocess.return_value = process_mock
        
        # Mock the Cargo.toml reading
        mock_file = mock.MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__iter__.return_value = ["name = \"test-project\""]
        mock_open.return_value = mock_file
        
        # Mock the Path operations
        mock_path_instance = mock.MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        result = await cargo_doc(self.ctx, "/fake/path")
        
        # Verify the result
        assert result["success"] is True
        assert "package_doc_path" in result["data"]
        # The package name should have been extracted
        assert "test-project" in str(result["data"]["package_doc_path"])

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_run_output_separation(self, mock_subprocess):
        """Test cargo_run output separation."""
        # Configure the mock with realistic cargo run output
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (
            b"   Compiling test-crate v0.1.0\n" + 
            b"    Finished dev [unoptimized + debuginfo] target(s)\n" +
            b"     Running `target/debug/test-crate`\n" +
            b"Program output line 1\n" +
            b"Program output line 2",
            b""
        )
        mock_subprocess.return_value = process_mock
        
        result = await cargo_run(self.ctx, self.temp_dir.name)
        
        # Verify the result
        assert result["success"] is True
        assert "compilation_output" in result["data"]
        assert "program_output" in result["data"]
        
        # Check compilation output has the compilation lines
        assert "Compiling" in result["data"]["compilation_output"]
        assert "Running `target" in result["data"]["compilation_output"]
        
        # Check program output has only the program output lines
        assert "Program output line 1" in result["data"]["program_output"]
        assert "Program output line 2" in result["data"]["program_output"]
        assert "Compiling" not in result["data"]["program_output"]
    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_tarpaulin_format_mapping(self, mock_subprocess):
        """Test cargo_tarpaulin format mapping."""
        # Configure the mock
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"30.02% coverage", b"")
        mock_subprocess.return_value = process_mock
        
        result = await cargo_tarpaulin(self.ctx, self.temp_dir.name, output_format="text")
        
        # Verify the result
        assert result["success"] is True
        
        # Verify format mapping from "text" to "Stdout"
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert call_args[0] == "cargo"
        assert call_args[1] == "tarpaulin"
        assert call_args[2] == "--out"
        assert call_args[3] == "Stdout"

    @pytest.mark.asyncio
    @mock.patch("asyncio.create_subprocess_exec")
    async def test_cargo_tarpaulin_coverage_extraction(self, mock_subprocess):
        """Test cargo_tarpaulin coverage percentage extraction."""
        # Configure the mock with realistic coverage output
        process_mock = mock.AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (
            b"Some testing output\n" +
            b"42.50% coverage, 250/500 lines covered\n" +
            b"More output",
            b""
        )
        mock_subprocess.return_value = process_mock
        
        result = await cargo_tarpaulin(self.ctx, self.temp_dir.name)
        
        # Verify the result
        assert result["success"] is True
        assert "coverage_data" in result["data"]
        assert "coverage_percent" in result["data"]["coverage_data"]
        # Check that the correct percentage was extracted
        assert result["data"]["coverage_data"]["coverage_percent"] == 42.50
        
