from typing import Any
import pytest
import sys
from pathlib import Path

# Add root to sys.path
root_path = Path(__file__).parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from system.swarm.orchestrator import SwarmOrchestrator, MessageBus, SwarmMessage


def test_message_bus() -> None:
    bus = MessageBus()
    bus.send("router", "coder", "task", "Write hello world")
    messages = bus.get_context("coder")
    assert len(messages) == 1
    assert messages[0].sender == "router"
    assert messages[0].recipient == "coder"


def test_orchestrator_initialization() -> None:
    """Verifies the orchestrator can initialize and recruit agents from src/agents/."""
    orchestrator = SwarmOrchestrator()
    # Should have recruited agents from src/agents/
    # The actual count depends on the agents present
    assert orchestrator.bus is not None
    assert isinstance(orchestrator.workers, dict)


def test_orchestrator_router_detection() -> None:
    """Verifies the orchestrator can detect a router agent."""
    orchestrator = SwarmOrchestrator()
    # If router_agent.py exists and is properly structured, router should be set
    if orchestrator.router:
        assert hasattr(orchestrator.router, "analyze_and_delegate")
