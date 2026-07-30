"""Selects the files of a directory tree that go into a bundle."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

DEFAULT_EXCLUDED_DIRS = {"bin", "obj", ".git", ".vs", ".idea", "node_modules",
                         "__pycache__", ".venv", "TestResults", "target"}


def add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """Add --ext and --exclude-dir, shared by every command that scans a directory."""
    parser.add_argument("--ext", type=lambda v: {e.strip().lstrip(".").lower() for e in v.split(",") if e.strip()},
                        default=set(), help="only these extensions, comma separated (e.g. cs,csproj,pdf)")
    parser.add_argument("--exclude-dir", type=lambda v: {d.strip().strip("/") for d in v.split(",") if d.strip()},
                        default=set(), help="extra directory names or relative paths to skip")


def list_files(src: Path, extensions: set[str], excluded: set[str], skip: Path | None = None) -> list[str]:
    """Relative POSIX paths of all files to bundle, sorted.

    Inside a git repository the files come from ``git ls-files`` so .gitignore
    applies; otherwise the tree is walked. Build output directories are always
    skipped. ``skip`` excludes one file, e.g. the bundle being written into SRC.
    """
    excluded = DEFAULT_EXCLUDED_DIRS | excluded
    skip_resolved = skip.resolve() if skip else None
    result = []
    for relative in _git_files(src) or _walk_files(src, excluded):
        parts = relative.split("/")
        if any(p in excluded for p in parts[:-1]) or any(relative.startswith(e + "/") for e in excluded):
            continue
        if extensions and Path(relative).suffix.lstrip(".").lower() not in extensions:
            continue
        path = src / relative
        if path.is_file() and path.resolve() != skip_resolved:
            result.append(relative)
    return sorted(result)


def _git_files(src: Path) -> list[str]:
    """Tracked and untracked-but-not-ignored files; empty outside a git repo."""
    try:
        run = subprocess.run(["git", "-C", str(src), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [p for p in run.stdout.decode("utf-8").split("\0") if p]


def _walk_files(src: Path, excluded: set[str]) -> list[str]:
    files = []
    for directory, subdirs, names in os.walk(src):
        subdirs[:] = [d for d in subdirs if d not in excluded]
        base = Path(directory).relative_to(src)
        files += [(base / n).as_posix() for n in names]
    return files
