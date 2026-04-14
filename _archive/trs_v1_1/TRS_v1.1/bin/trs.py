#!/usr/bin/env python3
"""
TRS-506: Unified CLI entry point with improved help.

Usage:
    python bin/trs.py --help
    python bin/trs.py validate v0.2.8
    python bin/trs.py propose new env.test.tag "Test Tag"
    python bin/trs.py release v0.2.9

Provides a single entry point to all TRS commands with consistent
help and documentation.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
BIN_DIR = REPO_ROOT / "bin"


# Command definitions
COMMANDS = {
    "validate": {
        "script": "validate_registry.py",
        "help": "Validate registry schema and invariants",
        "args": ["version"],
    },
    "diff": {
        "script": "diff_registry.py",
        "help": "Compare two registry versions for breaking changes",
        "args": ["old_version", "new_version"],
    },
    "release": {
        "script": "release.py",
        "help": "Create a new release with validation gates",
        "args": ["version"],
    },
    "contracts": {
        "script": "generate_contracts.py",
        "help": "Regenerate consumer contracts from registry",
        "args": ["version"],
    },
    "merge": {
        "script": "merge_proposals.py",
        "help": "Merge approved proposals into registry",
        "args": ["version"],
    },
    "propose": {
        "script": "propose_cli.py",
        "help": "Submit and manage tag proposals",
        "args": ["subcommand", "..."],
    },
    "keys": {
        "script": "../bin/keys.py",
        "help": "Manage API keys",
        "args": ["subcommand", "..."],
    },
    "batch": {
        "script": "batch.py",
        "help": "Batch import/export tags",
        "args": ["subcommand", "..."],
    },
    "backup": {
        "script": "backup.py",
        "help": "Backup and restore database",
        "args": ["subcommand", "..."],
    },
    "docs": {
        "script": "generate_docs.py",
        "help": "Generate documentation from registry",
        "args": ["version"],
    },
    "changelog": {
        "script": "changelog.py",
        "help": "Generate changelog between versions",
        "args": ["old_version", "new_version"],
    },
    "duplicates": {
        "script": "find_duplicates.py",
        "help": "Find duplicate and similar tags",
        "args": ["version"],
    },
    "lint": {
        "script": "lint_registry.py",
        "help": "Lint registry for style issues",
        "args": ["version"],
    },
}


def print_main_help():
    """Print main help message."""
    print("""
TRS - Tag Registry Service CLI
==============================

A unified command-line interface for managing the tag registry.

USAGE:
    trs <command> [args...]
    trs --help
    trs <command> --help

COMMANDS:

  Registry Management:
    validate    Validate registry schema and invariants
    diff        Compare two registry versions
    lint        Check registry for style issues
    duplicates  Find duplicate and similar tags

  Release Workflow:
    release     Create a new release with validation gates
    contracts   Regenerate consumer contracts
    changelog   Generate changelog between versions
    docs        Generate documentation from registry

  Proposal Workflow:
    propose     Submit and manage tag proposals
    merge       Merge approved proposals into registry

  Administration:
    keys        Manage API keys
    batch       Batch import/export tags
    backup      Backup and restore database

EXAMPLES:

    # Validate the current registry
    trs validate v0.2.8

    # Check for breaking changes
    trs diff v0.2.7 v0.2.8

    # Create a new release
    trs release v0.2.9

    # Submit a new tag proposal
    trs propose new env.test.tag "Test Tag" --value-type ordinal

    # Export all tags to JSON
    trs batch export v0.2.8 --output tags.json

For more information on a specific command:
    trs <command> --help
""")


def run_command(command: str, args: list[str]) -> int:
    """Run a TRS command."""
    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print(f"Run 'trs --help' for usage.")
        return 1
    
    cmd_info = COMMANDS[command]
    script_path = SCRIPTS_DIR / cmd_info["script"]
    
    # Handle relative paths (like ../bin/keys.py)
    if ".." in cmd_info["script"]:
        script_path = SCRIPTS_DIR / cmd_info["script"]
        script_path = script_path.resolve()
    
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return 1
    
    # Run the script
    result = subprocess.run(
        [sys.executable, str(script_path)] + args,
        cwd=REPO_ROOT,
    )
    
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print_main_help()
        return 0
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # Handle help
    if command in ("--help", "-h", "help"):
        print_main_help()
        return 0
    
    # Handle version
    if command in ("--version", "-V"):
        print("TRS CLI v0.0.5")
        return 0
    
    # Run command
    return run_command(command, args)


if __name__ == "__main__":
    sys.exit(main())
