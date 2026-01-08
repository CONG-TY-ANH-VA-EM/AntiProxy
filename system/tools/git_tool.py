"""
🛠️ Git Operations Tool.

Designation: Sys/Tools/Git
Purpose: Enables the Agent to perform version control operations.
Capabilities:
- git_status: Check working directory state.
- git_diff: specific file diffs or general diffs.
- git_commit: Commit changes with a message.
- git_log: View commit history.
"""

import subprocess
import shutil
from typing import List, Optional, Dict, Union, Any

def _run_git(args: List[str]) -> str:
    """Helper to run git commands safely."""
    if not shutil.which("git"):
        return "Error: git executable not found in PATH."
    
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=False  # We handle errors manually
        )
        if result.returncode != 0:
            return f"Git Error ({result.returncode}): {result.stderr.strip()}"
        return result.stdout.strip()
    except Exception as e:
        return f"Execution Error: {e}"

def git_status() -> str:
    """
    Returns the status of the repository.
    Equivalent to: git status
    """
    return _run_git(["status"])

def git_diff(filename: Optional[str] = None, staged: bool = False) -> str:
    """
    Shows changes in the working directory or staging area.
    
    Args:
        filename: Optional specific file to diff.
        staged: If True, shows changes that are staged for commit (--cached).
    """
    cmd = ["diff"]
    if staged:
        cmd.append("--cached")
    if filename:
        cmd.append(filename)
    
    return _run_git(cmd)

def git_commit(message: str, add_all: bool = False) -> str:
    """
    Commits changes to the repository.
    
    Args:
        message: The commit message.
        add_all: If True, stages all modified files before committing (-a).
    """
    cmd = ["commit", "-m", message]
    if add_all:
        cmd.insert(1, "-a")
        
    return _run_git(cmd)

def git_log(n: int = 5) -> str:
    """
    Shows the most recent commits.
    
    Args:
        n: Number of commits to show.
    """
    return _run_git(["log", f"-n {n}", "--oneline"])

def git_add(filename: str) -> str:
    """
    Stages a specific file.
    
    Args:
        filename: The file path to stage.
    """
    return _run_git(["add", filename])
