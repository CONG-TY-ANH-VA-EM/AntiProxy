import pytest
from typing import Any
import os
import json
import sys
from pathlib import Path

# Add root to sys.path and discovery
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from system.kernel.memory import MemoryManager, MemoryEntry, MemoryState

@pytest.fixture
def temp_memory_file(tmp_path: Any) -> Any:
    return tmp_path / "test_memory.json"

def test_memory_entry_creation() -> None:
    entry = MemoryEntry(role="user", content="hello")
    assert entry.role == "user"
    assert entry.content == "hello"
    assert entry.timestamp is not None

def test_memory_persistence(temp_memory_file: Any) -> None:
    mm = MemoryManager(memory_file=str(temp_memory_file))
    mm.add_entry(role="user", content="test message")
    
    # Reload memory
    mm2 = MemoryManager(memory_file=str(temp_memory_file))
    assert len(mm2.history) == 1
    assert mm2.history[0].role == "user"
    assert mm2.history[0].content == "test message"

def test_context_window_summarization(temp_memory_file: Any) -> None:
    mm = MemoryManager(memory_file=str(temp_memory_file))
    for i in range(15):
        mm.add_entry(role="user", content=f"message {i}")
    
    context = mm.get_context_window(system_prompt="You are a helper", max_messages=10)
    
    # context should be: [system, summary_model, recent_10]
    assert len(context) == 12
    assert context[0]["role"] == "system"
    assert context[1]["role"] == "model"
    assert "PREVIOUS CONTEXT SUMMARY" in context[1]["content"]
    assert len(context[2:]) == 10
    assert context[-1]["content"] == "message 14"

def test_clear_memory(temp_memory_file: Any) -> None:
    mm = MemoryManager(memory_file=str(temp_memory_file))
    mm.add_entry(role="user", content="bye")
    mm.clear_memory()
    assert len(mm.history) == 0
    assert mm.summary == ""
