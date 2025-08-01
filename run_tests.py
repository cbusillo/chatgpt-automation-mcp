#!/usr/bin/env python3
"""Test runner for ChatGPT MCP"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_unit_tests():
    """Run unit tests"""
    print("\n=== Running Unit Tests ===")
    cmd = [sys.executable, "-m", "pytest", "tests/test_browser_controller.py", "-v"]
    result = subprocess.run(cmd)
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests (requires browser)"""
    print("\n=== Running Integration Tests ===")
    print("Note: This requires Chrome to be installed and will open a browser window")
    cmd = [sys.executable, "-m", "pytest", "tests/test_integration.py", "--integration", "-v"]
    result = subprocess.run(cmd)
    return result.returncode == 0


def run_auto_enable_tests():
    """Run auto-enable web search tests"""
    print("\n=== Running Auto-Enable Web Search Tests ===")
    success = True
    
    # Run keyword detection tests
    cmd = [sys.executable, "tests/test_auto_enable_search.py"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        success = False
    
    # Run server integration tests  
    cmd = [sys.executable, "tests/test_server_auto_enable.py"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        success = False
        
    return success


def run_specific_test(test_name):
    """Run a specific test by name"""
    print(f"\n=== Running Test: {test_name} ===")
    cmd = [sys.executable, "-m", "pytest", "-k", test_name, "-v"]
    result = subprocess.run(cmd)
    return result.returncode == 0


def run_coverage():
    """Run tests with coverage report"""
    print("\n=== Running Tests with Coverage ===")
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=src/chatgpt_automation_mcp",
        "--cov-report=html",
        "--cov-report=term",
        "tests/test_browser_controller.py",
        "-v"
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\nCoverage report saved to htmlcov/index.html")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run ChatGPT MCP tests")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (requires browser)"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run specific test by name"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (unit + integration)"
    )
    parser.add_argument(
        "--auto-enable",
        action="store_true",
        help="Run auto-enable web search tests"
    )
    
    args = parser.parse_args()
    
    # Default to unit tests if nothing specified
    if not any([args.integration, args.unit, args.coverage, args.test, args.all, getattr(args, 'auto_enable', False)]):
        args.unit = True
    
    success = True
    
    if args.test:
        success = run_specific_test(args.test)
    elif args.coverage:
        success = run_coverage()
    elif args.all:
        success = run_unit_tests() and run_integration_tests()
    elif getattr(args, 'auto_enable', False):
        success = run_auto_enable_tests()
    else:
        if args.unit:
            success = run_unit_tests()
        if args.integration:
            success = success and run_integration_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()