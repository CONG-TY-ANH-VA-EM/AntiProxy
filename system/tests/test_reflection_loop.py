from typing import Any
import pytest
from unittest.mock import MagicMock
from system.kernel.agent import GeminiAgent, AgentState

@pytest.fixture
def agent() -> Any:
    agent = GeminiAgent()
    # Mock the client to avoid actual API calls
    agent.client = MagicMock()
    # Mock _call_gemini to return predictable responses
    agent._call_gemini = MagicMock(return_value="Reflection Insight") # type: ignore
    return agent

def test_reflection_failure(agent: Any) -> None:
    """Test that failure triggers CRITICAL ANALYSIS."""
    # Simulate a failed state
    agent.state.observation = "Error: Tool execution failed"
    agent.state.mission_objective = "Test Mission"
    agent.state.current_task = "Test Task"
    agent.state.decision = "Use Tool X"
    
    agent.reflect()
    
    # Verify the prompt contained failure-specific language
    call_args = agent._call_gemini.call_args[0][0]
    assert "Perform a CRITICAL ANALYSIS" in call_args
    assert "Analyze why it failed" in call_args
    
    # Verify memory storage
    last_memory = agent.memory.history[-1]
    assert last_memory.role == "system"
    assert "REFLECTION (CRITICAL ANALYSIS)" in last_memory.content

def test_reflection_success(agent: Any) -> None:
    """Test that success triggers REINFORCEMENT."""
    # Simulate a success state
    agent.state.observation = "Operation completed successfully."
    
    agent.reflect()
    
    # Verify the prompt contained success-specific language
    call_args = agent._call_gemini.call_args[0][0]
    assert "Perform a REINFORCEMENT" in call_args
    assert "Analyze why it succeeded" in call_args
    
    # Verify memory storage
    last_memory = agent.memory.history[-1]
    assert last_memory.role == "system"
    assert "REFLECTION (REINFORCEMENT)" in last_memory.content
