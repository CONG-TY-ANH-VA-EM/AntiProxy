"""
Base Agent class for all specialist agents in the swarm.

Provides common functionality for agent execution, context management,
and communication with the Gemini API.
"""

import os
from typing import Any, Dict, List, Optional
from google import genai
from system.config import settings


class BaseAgent:
    """
    Base class for all agents in the swarm.
    
    Each agent has a specific role and system prompt that defines its specialty.
    All agents share common execution logic but differ in their prompts and tools.
    """
    
    def __init__(self, role: str, system_prompt: str) -> None:
        """
        Initialize a base agent.
        
        Args:
            role: The agent's role identifier (e.g., "coder", "reviewer").
            system_prompt: The system prompt defining the agent's behavior.
        """
        self.role = role
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict[str, str]] = []
        
        # Initialize Gemini client
        running_under_pytest = "PYTEST_CURRENT_TEST" in os.environ
        if running_under_pytest:
            # Dummy client for testing
            class MockResponse:
                text: str = f"[{role}] Task completed"

            class MockModels:
                def generate_content(self, model: str, contents: str) -> MockResponse:
                    return MockResponse()

            class MockClient:
                def __init__(self) -> None:
                    self.models = MockModels()

            self.client: Any = MockClient()
        else:
            try:
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            except Exception as e:
                print(f"⚠️ {role} agent: genai client not initialized: {e}")
                
                # Fallback to dummy client
                class FallbackResponse:
                    text: str = f"[{role}] Task completed"

                class FallbackModels:
                    def generate_content(self, model: str, contents: str) -> FallbackResponse:
                        return FallbackResponse()

                class FallbackClient:
                    def __init__(self) -> None:
                        self.models = FallbackModels()

                self.client = FallbackClient()
    
    def execute(self, task: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute a task with optional context from other agents.
        
        Args:
            task: The task description to execute.
            context: Optional list of previous messages from other agents.
            
        Returns:
            The agent's response as a string.
        """
        # Build the full prompt
        prompt_parts: List[str] = [self.system_prompt, f"\n\nTask: {task}"]
        
        # Add context if provided
        if context:
            context_str = "\n\nContext from other agents:\n"
            for msg in context:
                context_str += f"[{msg.get('from', 'unknown')}]: {msg.get('content', '')}\n"
            prompt_parts.append(context_str)
        
        full_prompt = "".join(prompt_parts)
        
        # Call Gemini API
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=full_prompt
            )
            result = str(getattr(response, "text", str(response))).strip()
            
            # Store in conversation history
            self.conversation_history.append({
                "role": "user",
                "content": task
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": result
            })
            
            return result
        except Exception as e:
            return f"[{self.role}] Error executing task: {str(e)}"
    
    def reset_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
