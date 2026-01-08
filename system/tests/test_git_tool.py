from typing import Generator
import pytest
from unittest.mock import patch, MagicMock
from system.tools import git_tool

@pytest.fixture
def mock_subprocess() -> Generator[MagicMock, None, None]:
    with patch("subprocess.run") as mock:
        yield mock

def test_git_status(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "On branch main\nnothing to commit"
    
    result = git_tool.git_status()
    
    assert "On branch main" in result
    mock_subprocess.assert_called_with(
        ["git", "status"], 
        capture_output=True, 
        text=True, 
        check=False
    )

def test_git_diff(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "diff output"
    
    # Test general diff
    result = git_tool.git_diff()
    assert result == "diff output"
    mock_subprocess.assert_called_with(
        ["git", "diff"],
        capture_output=True, text=True, check=False
    )
    
    # Test specific file diff
    git_tool.git_diff("file.txt")
    mock_subprocess.assert_called_with(
        ["git", "diff", "file.txt"],
        capture_output=True, text=True, check=False
    )
    
    # Test staged diff
    git_tool.git_diff(staged=True)
    mock_subprocess.assert_called_with(
        ["git", "diff", "--cached"],
        capture_output=True, text=True, check=False
    )

def test_git_commit(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "[main 1234567] commit message"
    
    # Test normal commit
    git_tool.git_commit("test commit")
    mock_subprocess.assert_called_with(
        ["git", "commit", "-m", "test commit"],
        capture_output=True, text=True, check=False
    )
    
    # Test commit -a
    git_tool.git_commit("test commit", add_all=True)
    mock_subprocess.assert_called_with(
        ["git", "commit", "-a", "-m", "test commit"],
        capture_output=True, text=True, check=False
    )

def test_git_log(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "1234567 commit 1\nabcdefg commit 2"
    
    result = git_tool.git_log(2)
    assert "commit 1" in result
    mock_subprocess.assert_called_with(
        ["git", "log", "-n 2", "--oneline"],
        capture_output=True, text=True, check=False
    )

def test_git_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = "fatal: not a git repository"
    
    result = git_tool.git_status()
    assert "Git Error (1): fatal: not a git repository" in result
