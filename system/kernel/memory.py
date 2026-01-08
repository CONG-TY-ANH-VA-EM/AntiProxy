"""
🧠 Cognitive Memory Substrate.

Designation: Sys/Kernel/Memory
Purpose: Manages long-term and short-term context for the Agent.
Capabilities:
- Persistent JSON storage in `artifacts/memory/`.
- Recursive context summarization.
- Context window management for LLM context limits.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Internal Imports
try:
    from system.config import settings
except ImportError:
    # Fallback for legacy imports
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from system.config import settings

class MemoryEntry(BaseModel):
    """A single interaction event in the cognitive stream."""
    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryState(BaseModel):
    """The complete persistent state of the Agent's memory."""
    summary: str = ""
    history: List[MemoryEntry] = Field(default_factory=list)

class MemoryManager:
    """
    Manages the Agent's cognitive history using a recursive summary buffer approach.
    Stores data in `artifacts/memory/agent_memory.json`.
    """

    def __init__(self, memory_file: Optional[str] = None) -> None:
        # Resolve memory path relative to project root if not absolute
        if memory_file:
            self.memory_path = Path(memory_file)
        else:
            # Default: artifacts/memory/agent_memory.json
            root_dir = Path(__file__).parent.parent.parent
            self.memory_path = root_dir / "artifacts" / "memory" / "agent_memory.json"

        # Ensure directory exists
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        self.state = MemoryState()
        self._load_memory()

    def _load_memory(self) -> None:
        """Loads memory from the JSON substrate using Pydantic for validation."""
        if not self.memory_path.exists():
            return

        try:
            content = self.memory_path.read_text(encoding='utf-8')
            if not content.strip():
                return

            data = json.loads(content)
            self.state = MemoryState.model_validate(data)
                
        except Exception as e:
            print(f"   [MEMORY] ⚠️ Load Error: {e}. Starting fresh.")
            self.state = MemoryState()

    def save_memory(self) -> None:
        """Persists the current cognitive state."""
        try:
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.state.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   [MEMORY] ❌ Write Error: {e}")

    def add_entry(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Injects a new interaction event into the stream."""
        entry = MemoryEntry(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.state.history.append(entry)
        self.save_memory()

    @property
    def history(self) -> List[MemoryEntry]:
        """Returns the raw event stream."""
        return self.state.history

    @property
    def summary(self) -> str:
        """Returns the current context summary."""
        return self.state.summary

    @summary.setter
    def summary(self, value: str) -> None:
        """Updates the current context summary."""
        self.state.summary = value
        self.save_memory()

    def _default_summarizer(self, old_entries: List[MemoryEntry], previous_summary: str) -> str:
        """Fallback deterministic summarizer."""
        lines: List[str] = []
        if previous_summary:
            lines.append(f"PREV_CTX: {previous_summary}")
        
        for entry in old_entries:
            lines.append(f"{entry.role}: {entry.content[:100]}...")
            
        return "\n".join(lines)

    def get_context_window(
        self,
        system_prompt: str,
        max_messages: int = 10,
        summarizer: Optional[Callable[[List[MemoryEntry], str], str]] = None
    ) -> List[Dict[str, str]]:
        """
        Constructs the Prompt Context Window for the LLM.
        Applies compression (summarization) if history exceeds `max_messages`.
        """
        if not system_prompt:
            raise ValueError("System prompt is required.")
        
        # Base System Instruction
        context: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        
        full_history = self.history
        
        # If history fits in window, return all
        if len(full_history) <= max_messages:
            return context + [entry.model_dump(include={"role", "content"}) for entry in full_history]

        # Slice history
        entries_to_summarize = full_history[:-max_messages]
        recent_entries = full_history[-max_messages:]
        
        # Execute Summary
        summarizer_fn = summarizer or self._default_summarizer
        try:
            self.summary = summarizer_fn(entries_to_summarize, self.summary)
        except Exception as e:
            print(f"   [MEMORY] ⚠️ Summary Failed: {e}")
        
        # Inject Summary
        if self.summary:
            context.append({
                "role": "model",
                "content": f"PREVIOUS CONTEXT SUMMARY:\n{self.summary}"
            })
            
        return context + [entry.model_dump(include={"role", "content"}) for entry in recent_entries]

    def clear_memory(self) -> None:
        """Performs a lobotomy (Factory Reset)."""
        self.state = MemoryState()
        self.save_memory()
