"""
📁 File System Traversal Tool.

Designation: Sys/Tools/FileSystem
Purpose: Provides file system operations for the Agent.
Capabilities:
- List directory contents recursively.
- Read file contents.
- Search for patterns in files.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Schema for file metadata."""
    path: str
    name: str
    is_dir: bool
    size_bytes: int = 0
    extension: str = ""


def list_files(
    directory: str,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    max_depth: int = 3
) -> List[Dict[str, Any]]:
    """
    Lists files and directories in a given path.

    Args:
        directory: The root directory to scan.
        recursive: If True, scan subdirectories.
        extensions: Filter by file extensions (e.g., [".py", ".md"]).
        max_depth: Maximum recursion depth.

    Returns:
        List of file metadata dictionaries.
    """
    root = Path(directory)
    if not root.exists():
        return [{"error": f"Directory not found: {directory}"}]

    results: List[Dict[str, Any]] = []

    def _scan(current: Path, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            for item in current.iterdir():
                info = FileInfo(
                    path=str(item),
                    name=item.name,
                    is_dir=item.is_dir(),
                    size_bytes=item.stat().st_size if item.is_file() else 0,
                    extension=item.suffix if item.is_file() else ""
                )

                if extensions and item.is_file():
                    if info.extension not in extensions:
                        continue

                results.append(info.model_dump())

                if recursive and item.is_dir():
                    _scan(item, depth + 1)

        except PermissionError:
            results.append({"error": f"Permission denied: {current}"})

    _scan(root, 0)
    return results


def read_file(file_path: str, max_lines: int = 500) -> str:
    """
    Reads the content of a text file.

    Args:
        file_path: Absolute path to the file.
        max_lines: Maximum number of lines to return.

    Returns:
        File contents as a string, or an error message.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            truncated = lines[:max_lines]
            return "\n".join(truncated) + f"\n\n... [Truncated: {len(lines) - max_lines} more lines]"
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


def search_pattern(
    directory: str,
    pattern: str,
    extensions: Optional[List[str]] = None,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Searches for a text pattern in files within a directory.

    Args:
        directory: The root directory to search.
        pattern: The text pattern to search for.
        extensions: Filter by file extensions.
        max_results: Maximum number of matching lines to return.

    Returns:
        List of match results with file path, line number, and content.
    """
    root = Path(directory)
    if not root.exists():
        return [{"error": f"Directory not found: {directory}"}]

    results: List[Dict[str, Any]] = []

    for file_path in root.rglob("*"):
        if len(results) >= max_results:
            break

        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern in line:
                    results.append({
                        "file": str(file_path),
                        "line_number": int(i),
                        "content": str(line.strip()[:200])
                    })
                    if len(results) >= max_results:
                        break
        except Exception:
            continue

    return results
