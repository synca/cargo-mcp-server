import os
import pathlib
import asyncio
import subprocess
from mcp.server.fastmcp import Context, FastMCP

mcp = FastMCP("Cargo")

# TOOLS

@mcp.tool()
async def cargo_clippy(ctx: Context, path: str, args: list[str] | None = None, default_args: list[str] | None = None) -> dict:
    """Run cargo clippy on a Rust project
    
    Executes clippy linter on the specified Rust project path.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        args: Optional list of additional arguments to pass to clippy
             Examples: ["--no-deps", "--workspace", "--", "-D", "warnings"]
        default_args: Optional list of default arguments to use instead of built-in defaults
                     If provided, these replace the standard arguments completely
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the operation completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the result
                "output": str,   # Combined stdout/stderr output from clippy
                "project_path": str  # Path to the project that was linted
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Define standard arguments if no default_args provided
        standard_args = ["--all-targets", "--all-features", "--", "-W", "clippy::all"]
        
        # Build the command with appropriate defaults
        clippy_cmd = ["cargo", "clippy"]
        
        # Add either custom default_args or standard_args
        if default_args is not None:
            clippy_cmd.extend(default_args)
        else:
            # Add standard arguments except warnings if overridden by user args
            base_args = standard_args[:3]  # Everything before the warning flags
            clippy_cmd.extend(base_args)
            
            # Add warning flags only if not overridden
            if not args or not any(arg.startswith("-W") for arg in args):
                clippy_cmd.extend(standard_args[3:])  # Just the warning flags
        
        # Add any additional user arguments
        if args:
            clippy_cmd.extend(args)
            
        # Run cargo clippy with arguments
        process = await asyncio.create_subprocess_exec(
            *clippy_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Clippy warnings are typically on stderr but the process still returns 0
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Check if there are clippy warnings in the output
        if "warning:" in combined_output or "error:" in combined_output:
            return {
                "success": True,  # Still considered success since cargo completed
                "data": {
                    "message": "Clippy completed with warnings/errors",
                    "output": combined_output,
                    "project_path": path
                },
                "error": None
            }
        elif process.returncode == 0:
            return {
                "success": True,
                "data": {
                    "message": "Clippy completed successfully with no issues",
                    "output": combined_output if combined_output.strip() else "No issues found",
                    "project_path": path
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Clippy found issues: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run clippy: {str(e)}"
        }


@mcp.tool()
async def cargo_check(ctx: Context, path: str, args: list[str] | None = None) -> dict:
    """Run cargo check on a Rust project
    
    Checks a package for errors without building it.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        args: Optional list of additional arguments to pass to cargo check
             Examples: ["--all-features", "--workspace", "--lib"]
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the operation completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the result
                "output": str,   # Combined stdout/stderr output
                "project_path": str  # Path to the project that was checked
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        check_cmd = ["cargo", "check", "--all-targets", "--all-features"]
        
        # Add any additional user arguments
        if args:
            check_cmd.extend(args)
            
        # Run cargo check with arguments
        process = await asyncio.create_subprocess_exec(
            *check_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Check if there are warnings or errors in the output
        if "warning:" in combined_output or "error:" in combined_output:
            return {
                "success": True,  # Still considered success unless cargo fails
                "data": {
                    "message": "Cargo check completed with warnings/errors",
                    "output": combined_output,
                    "project_path": path
                },
                "error": None
            }
        elif process.returncode == 0:
            return {
                "success": True,
                "data": {
                    "message": "Cargo check completed successfully with no issues",
                    "output": combined_output if combined_output.strip() else "No issues found",
                    "project_path": path
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Cargo check failed: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo check: {str(e)}"
        }


@mcp.tool()
async def cargo_build(ctx: Context, path: str, release: bool = False, args: list[str] | None = None) -> dict:
    """Build a Rust project
    
    Compiles a package and all of its dependencies.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        release: Whether to build in release mode (optimized, no debug info)
        args: Optional list of additional arguments to pass to cargo build
             Examples: ["--workspace", "--all-features", "--lib"]
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the operation completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the result
                "output": str,   # Combined stdout/stderr output
                "project_path": str,  # Path to the project that was built
                "build_mode": str  # Either "debug" or "release"
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        build_cmd = ["cargo", "build"]
        
        # Add release flag if specified
        if release:
            build_cmd.append("--release")
        
        # Add any additional user arguments
        if args:
            build_cmd.extend(args)
            
        # Run cargo build with arguments
        process = await asyncio.create_subprocess_exec(
            *build_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        if process.returncode == 0:
            build_mode = "release" if release else "debug"
            return {
                "success": True,
                "data": {
                    "message": f"Cargo build ({build_mode}) completed successfully",
                    "output": combined_output if combined_output.strip() else "Build completed without output",
                    "project_path": path,
                    "build_mode": build_mode
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Cargo build failed: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo build: {str(e)}"
        }


@mcp.tool()
async def cargo_test(ctx: Context, path: str, args: list[str] | None = None, test_name: str | None = None) -> dict:
    """Run tests for a Rust project
    
    Executes all unit and integration tests for a package.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        args: Optional list of additional arguments to pass to cargo test
             Examples: ["--release", "--no-fail-fast", "--verbose"]
        test_name: Optional name pattern to filter tests to run
                  If provided, only tests containing this string in their name will run
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether all tests passed
            "data": {        # Present regardless of success
                "message": str,  # Summary message about the test results
                "output": str,   # Combined stdout/stderr output from tests
                "project_path": str,  # Path to the project that was tested
                "test_summary": {  # Summary statistics about test results
                    "total_tests": int,  # Total number of tests run
                    "passed": int,       # Number of passing tests
                    "failed": int,       # Number of failing tests (if any)
                    "status": str        # Overall status: "passed" or "failed"
                }
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        test_cmd = ["cargo", "test"]
        
        # Add test name pattern if specified
        if test_name:
            test_cmd.append(test_name)
        
        # Add any additional user arguments
        if args:
            test_cmd.extend(args)
            
        # Run cargo test with arguments
        process = await asyncio.create_subprocess_exec(
            *test_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Parse test results to provide more structured information
        test_summary = {}
        if "test result: ok" in combined_output:
            # Extract test count and success status
            for line in combined_output.splitlines():
                if "test result: ok." in line:
                    parts = line.split()
                    test_summary["total_tests"] = int(parts[3])
                    test_summary["passed"] = int(parts[3])
                    test_summary["status"] = "passed"
                    break
                elif "test result: FAILED" in line:
                    parts = line.split()
                    fail_stats = parts[parts.index("failed,") - 1]
                    pass_stats = parts[parts.index("passed,") - 1]
                    test_summary["total_tests"] = int(fail_stats) + int(pass_stats)
                    test_summary["passed"] = int(pass_stats)
                    test_summary["failed"] = int(fail_stats)
                    test_summary["status"] = "failed"
                    break
        
        if process.returncode == 0:
            return {
                "success": True,
                "data": {
                    "message": "All tests passed successfully",
                    "output": combined_output,
                    "project_path": path,
                    "test_summary": test_summary
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": {
                    "message": "Some tests failed",
                    "output": combined_output,
                    "project_path": path,
                    "test_summary": test_summary
                },
                "error": "Test execution failed"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo test: {str(e)}"
        }


@mcp.tool()
async def cargo_fmt(ctx: Context, path: str, check_only: bool = False, args: list[str] | None = None) -> dict:
    """Format Rust code using rustfmt
    
    Formats Rust code according to style guidelines using rustfmt.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        check_only: If True, checks if code is formatted correctly without modifying it
                   When True, the tool only reports formatting issues without making changes
        args: Optional list of additional arguments to pass to cargo fmt
             Examples: ["--manifest-path=path/to/Cargo.toml", "--all"]
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the operation completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the formatting status
                "needs_formatting": bool,  # Whether code needs formatting
                "output": str,   # Detailed output showing formatting differences (if any)
                "project_path": str  # Path to the project that was formatted
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        fmt_cmd = ["cargo", "fmt"]
        
        # Add check flag if specified
        if check_only:
            fmt_cmd.append("--check")
        
        # Add any additional user arguments
        if args:
            fmt_cmd.extend(args)
            
        # Run cargo fmt with arguments
        process = await asyncio.create_subprocess_exec(
            *fmt_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # In check mode, a non-zero exit code means formatting issues were found
        if check_only and process.returncode != 0:
            return {
                "success": True,  # We're just checking, so this is still a "successful" operation
                "data": {
                    "message": "Formatting issues detected",
                    "needs_formatting": True,
                    "output": combined_output,
                    "project_path": path
                },
                "error": None
            }
        elif process.returncode == 0:
            message = "Code is properly formatted" if check_only else "Code successfully formatted"
            return {
                "success": True,
                "data": {
                    "message": message,
                    "needs_formatting": False,
                    "output": combined_output if combined_output.strip() else "No output",
                    "project_path": path
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Cargo fmt failed: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo fmt: {str(e)}"
        }


@mcp.tool()
async def cargo_doc(ctx: Context, path: str, open_docs: bool = False, args: list[str] | None = None) -> dict:
    """Generate documentation for a Rust project
    
    Builds documentation for the local package and all dependencies.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        open_docs: Whether to open the documentation in a browser after building
                  When True, it will try to open the generated docs in the default browser
        args: Optional list of additional arguments to pass to cargo doc
             Examples: ["--no-deps", "--document-private-items", "--lib"]
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the operation completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the documentation generation
                "output": str,   # Combined stdout/stderr output from cargo doc
                "project_path": str,  # Path to the project that was documented
                "doc_path": str,      # Path to the generated documentation root
                "package_doc_path": str | None  # Path to this specific package's docs
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        doc_cmd = ["cargo", "doc"]
        
        # Add open flag if specified
        if open_docs:
            doc_cmd.append("--open")
        
        # Add any additional user arguments
        if args:
            doc_cmd.extend(args)
            
        # Run cargo doc with arguments
        process = await asyncio.create_subprocess_exec(
            *doc_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Determine the path to the generated documentation
        target_doc_path = pathlib.Path(path) / "target" / "doc"
        
        if process.returncode == 0:
            # Try to extract the package name from Cargo.toml to provide a more specific doc path
            package_name = None
            try:
                with open(cargo_toml_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith("name"):
                            package_name = line.split("=")[1].strip().strip('"').strip("'")
                            break
            except Exception:
                # Not critical if we can't get the package name
                pass
                
            return {
                "success": True,
                "data": {
                    "message": "Documentation successfully generated",
                    "output": combined_output if combined_output.strip() else "No output",
                    "project_path": path,
                    "doc_path": str(target_doc_path),
                    "package_doc_path": str(target_doc_path / package_name) if package_name else None
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Cargo doc failed: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo doc: {str(e)}"
        }


@mcp.tool()
async def cargo_run(ctx: Context, path: str, args: list[str] | None = None, release: bool = False, bin: str | None = None) -> dict:
    """Run a Rust project binary
    
    Compiles and runs the main binary or a specified binary.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        args: Optional list of arguments to pass to the binary
             These are arguments for the binary itself, not for cargo
        release: Whether to run in release mode (optimized, no debug info)
        bin: Optional name of a specific binary to run
             For projects with multiple binaries, specifies which one to run
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the execution completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the execution
                "output": str,   # Combined stdout/stderr from both compilation and program
                "compilation_output": str | None,  # Cargo output during compilation
                "program_output": str,  # Output from the executed program
                "project_path": str,  # Path to the project that was run
                "binary": str | None,  # Name of the binary that was run, if specified
                "mode": str  # Either "release" or "debug"
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        run_cmd = ["cargo", "run"]
        
        # Add release flag if specified
        if release:
            run_cmd.append("--release")
            
        # Add specific binary if specified
        if bin:
            run_cmd.extend(["--bin", bin])
        
        # Add -- separator before arguments to the binary
        if args:
            run_cmd.append("--")
            run_cmd.extend(args)
            
        # Run cargo run with arguments
        process = await asyncio.create_subprocess_exec(
            *run_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Separate compilation output from program output
        program_output = ""
        compilation_output = ""
        
        if "Finished" in combined_output and "Running" in combined_output:
            # Try to separate compilation from program output
            lines = combined_output.splitlines()
            running_line_idx = None
            
            for i, line in enumerate(lines):
                if "Running ` target" in line:
                    running_line_idx = i
                    break
            
            if running_line_idx is not None:
                compilation_output = "\n".join(lines[:running_line_idx+1])
                program_output = "\n".join(lines[running_line_idx+1:])
        
        if process.returncode == 0:
            return {
                "success": True,
                "data": {
                    "message": "Program executed successfully",
                    "output": combined_output,
                    "compilation_output": compilation_output if compilation_output else None,
                    "program_output": program_output if program_output else combined_output,
                    "project_path": path,
                    "binary": bin,
                    "mode": "release" if release else "debug"
                },
                "error": None
            }
        else:
            # Determine if it's a compilation error or runtime error
            if "error: could not compile" in combined_output:
                error_type = "compilation"
                error_message = "Failed to compile the program"
            else:
                error_type = "runtime"
                error_message = "Program execution failed"
                
            return {
                "success": False,
                "data": {
                    "output": combined_output,
                    "compilation_output": compilation_output if compilation_output else None,
                    "program_output": program_output if program_output else None,
                    "project_path": path,
                    "binary": bin,
                    "mode": "release" if release else "debug",
                    "error_type": error_type
                },
                "error": f"{error_message}: {stderr.decode()}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo run: {str(e)}"
        }


@mcp.tool()
async def cargo_tarpaulin(ctx: Context, path: str, args: list[str] | None = None, output_format: str = "text") -> dict:
    """Run code coverage analysis using cargo-tarpaulin
    
    Measures code coverage of tests in a Rust project.
    
    Args:
        path: Path to a Rust project containing a Cargo.toml file
        args: Optional list of additional arguments to pass to tarpaulin
             Examples: ["--workspace", "--exclude-files=**/tests/**", "--fail-under=80"]
        output_format: Format for the coverage report (case insensitive)
                     Valid values: "text", "json", "xml", "html", "lcov"
                     - "text" outputs to console (using tarpaulin's "Stdout" format)
                     - other formats generate a file in the project directory
    
    Returns:
        A dictionary with the following structure:
        {
            "success": bool,  # Whether the coverage analysis completed successfully
            "data": {        # Present only if success is True
                "message": str,  # Summary message about the coverage analysis
                "output": str,   # Combined stdout/stderr output from tarpaulin
                "project_path": str,  # Path to the project that was analyzed
                "coverage_data": {  # Coverage statistics and file information
                    "coverage_percent": float,  # Overall coverage percentage (if available)
                    "output_file": str  # Path to the output file (for non-text formats)
                },
                "format": str  # The format that was used for the report
            },
            "error": str | None  # Error message if success is False, otherwise None
        }
    """
    # Validate the path contains a Cargo.toml file
    cargo_toml_path = pathlib.Path(path) / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {
            "success": False,
            "data": None,
            "error": f"Path '{path}' is not a valid Rust project (no Cargo.toml found)"
        }
        
    try:
        # Build the command
        tarpaulin_cmd = ["cargo", "tarpaulin"]
        
        # Add output format
        # Tarpaulin expects capitalized format names
        format_mapping = {
            "text": "Stdout",
            "json": "Json",
            "xml": "Xml",
            "html": "Html",
            "lcov": "Lcov"
        }
        
        if output_format.lower() in format_mapping:
            capitalized_format = format_mapping[output_format.lower()]
            tarpaulin_cmd.extend(["--out", capitalized_format])
        else:
            valid_formats = list(format_mapping.keys())
            return {
                "success": False,
                "data": None,
                "error": f"Invalid output format '{output_format}'. Must be one of: {', '.join(valid_formats)}"
            }
        
        # Add any additional user arguments
        if args:
            tarpaulin_cmd.extend(args)
            
        # Run cargo tarpaulin with arguments
        process = await asyncio.create_subprocess_exec(
            *tarpaulin_cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stderr_output = stderr.decode()
        stdout_output = stdout.decode()
        combined_output = stdout_output + "\n" + stderr_output
        
        # Parse the coverage results
        coverage_data = {}
        
        # Try to extract the coverage percentage from output
        coverage_pct = None
        if "% coverage" in combined_output:
            for line in reversed(combined_output.splitlines()):
                if "% coverage" in line:
                    try:
                        coverage_pct = float(line.split("%")[0].strip())
                        coverage_data["coverage_percent"] = coverage_pct
                        break
                    except (ValueError, IndexError):
                        pass
        
        # Output files that would be generated
        output_file = None
        if output_format.lower() != "text":
            if output_format.lower() == "json":
                output_file = "cobertura.json"
            elif output_format.lower() == "xml":
                output_file = "cobertura.xml"
            elif output_format.lower() == "html":
                output_file = "tarpaulin-report.html"
            elif output_format.lower() == "lcov":
                output_file = "lcov.info"
            
            if output_file:
                output_path = pathlib.Path(path) / output_file
                coverage_data["output_file"] = str(output_path)
        
        if "error:" in combined_output.lower() or process.returncode != 0:
            return {
                "success": False,
                "data": {
                    "output": combined_output,
                    "project_path": path,
                    "coverage_data": coverage_data if coverage_data else None
                },
                "error": f"Tarpaulin execution failed: {stderr.decode()}"
            }
        else:
            return {
                "success": True,
                "data": {
                    "message": "Coverage analysis completed successfully",
                    "output": combined_output,
                    "project_path": path,
                    "coverage_data": coverage_data,
                    "format": output_format.lower()
                },
                "error": None
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to run cargo tarpaulin: {str(e)}"
        }
