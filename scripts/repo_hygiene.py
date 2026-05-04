#!/usr/bin/env python3
"""Basic repository hygiene checks.

This is intentionally not a linter. It only blocks files that usually mean
someone committed local machine output, unresolved merge content, or a large
artifact in an active source path.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DISALLOWED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
DISALLOWED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".env",
    ".env.local",
}
DISALLOWED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".swp",
    ".swo",
}
LOCAL_ENV_SUFFIXES = (
    ".local",
)

TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}
SKIP_TEXT_SCAN_PREFIXES = (
    "_archive/",
    "frontend/node_modules/",
    "frontend/dist/",
)

MAX_ACTIVE_FILE_BYTES = 10 * 1024 * 1024
LARGE_FILE_ALLOWED_PREFIXES = (
    "_archive/",
    "backend/database/",
    "backend/science/data/",
    "frontend/node_modules/",
    "frontend/dist/",
)

CONFLICT_MARKER_RE = re.compile(r"^(<{7} |={7}$|>{7} )")


def git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def has_local_env_name(path: str, name: str) -> bool:
    if name == ".env.example":
        return False
    if name.startswith(".env.") and name.endswith(LOCAL_ENV_SUFFIXES):
        return True
    return path.endswith("/.env") or path.endswith("/.env.local")


def is_text_candidate(path: str) -> bool:
    if path.startswith(SKIP_TEXT_SCAN_PREFIXES):
        return False
    return Path(path).suffix.lower() in TEXT_SUFFIXES


def is_large_file_allowed(path: str) -> bool:
    return path.startswith(LARGE_FILE_ALLOWED_PREFIXES)


def check_path_hygiene(paths: list[str], failures: list[str]) -> None:
    for path in paths:
        if path.startswith("_archive/"):
            continue

        p = Path(path)
        parts = set(p.parts)
        name = p.name
        suffix = p.suffix

        bad_dirs = sorted(parts & DISALLOWED_DIR_NAMES)
        if bad_dirs:
            failures.append(f"tracked cache directory artifact: {path}")
            continue

        if name in DISALLOWED_FILE_NAMES or suffix in DISALLOWED_SUFFIXES:
            failures.append(f"tracked local/generated file: {path}")
            continue

        if has_local_env_name(path, name):
            failures.append(f"tracked local environment file: {path}")


def check_file_sizes(paths: list[str], failures: list[str]) -> None:
    for path in paths:
        if is_large_file_allowed(path):
            continue
        full_path = REPO_ROOT / path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            if size > MAX_ACTIVE_FILE_BYTES:
                failures.append(
                    f"large active file: {path} ({size} bytes; archive or document it)"
                )


def check_conflict_markers(paths: list[str], failures: list[str]) -> None:
    for path in paths:
        if not is_text_candidate(path):
            continue

        full_path = REPO_ROOT / path
        try:
            lines = full_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        marker_hits = []
        for line_no, line in enumerate(lines, start=1):
            if CONFLICT_MARKER_RE.match(line):
                marker_hits.append(str(line_no))

        if marker_hits:
            failures.append(
                f"merge conflict marker(s): {path}:{', '.join(marker_hits[:5])}"
            )


def main() -> int:
    paths = git_ls_files()
    failures: list[str] = []

    check_path_hygiene(paths, failures)
    check_file_sizes(paths, failures)
    check_conflict_markers(paths, failures)

    if failures:
        print("Repository hygiene check failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
