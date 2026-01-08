# Kernel Alpha: State Machine Edition
import json
import time
import os
import sys
import asyncio
import inspect
import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Literal
from datetime import datetime

# External dependencies
from google import genai
from pydantic import BaseModel, Field

# Internal dependencies
try:
    from system.config import settings
    from system.kernel.memory import MemoryManager, MemoryEntry
except ImportError:
    # Fallback for when running directly or in different path structure
    root = Path(__file__).parent.parent.parent
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from system.config import settings
    from system.kernel.memory import MemoryManager, MemoryEntry

class AgentState(BaseModel):
    """Represents the current cognitive state of the Agent."""
    phase: Literal["BOOT", "OBSERVE", "ORIENT", "DECIDE", "ACT", "REFLECT", "IDLE"] = "BOOT"
    mission_objective: str = "Idle"
    tools_loaded: int = 0
    mcp_active: bool = False
    last_thought: str = ""
    current_task: Optional[str] = None
    observation: Optional[str] = None
    decision: Optional[str] = None

class GeminiAgent:
    """
    The Executive Kernel of the Antigravity Recursive Core (ARC).
    Operates as a pure State Machine following the OODA Loop.
    """

    def __init__(self) -> None:
        self.state = AgentState()
        self.settings = settings
        self.memory = MemoryManager()
        self.mcp_manager: Optional[Any] = None
        
        # Paths
        self.root_dir = Path(__file__).parent.parent.parent
        self.artifacts_dir = self.root_dir / "artifacts"
        self.logs_dir = self.artifacts_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 1. Boot Sequence
        self.transition("BOOT")
        self._boot_sequence()

        # 2. Tool Loading
        self.available_tools: Dict[str, Callable[..., Any]] = self._load_tools()
        self.state.tools_loaded = len(self.available_tools)

        # 3. MCP Initialization
        if self.settings.MCP_ENABLED:
            self._initialize_mcp()

        # 4. Neural Link (Client) Initialization
        self.client = self._initialize_client()
        self.transition("IDLE")

    def transition(self, next_phase: Literal["BOOT", "OBSERVE", "ORIENT", "DECIDE", "ACT", "REFLECT", "IDLE"]) -> None:
        """Governs state transitions."""
        print(f"🔄 [STATE] Transitioning: {self.state.phase} -> {next_phase}")
        self.state.phase = next_phase

    def _boot_sequence(self) -> None:
        """Initializes the Agent's identity and governs alignment."""
        print("\n🚀 SYSTEM BOOT: Antigravity Recursive Core")
        
        # Load Mission
        mission_path = self.root_dir / "mission.md"
        if mission_path.exists():
            content = mission_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "Current Objective:" in line:
                    self.state.mission_objective = line.split("Current Objective:")[1].strip()
                    break
        
        print(f"   🎯 Current Objective: {self.state.mission_objective}")

    def _initialize_client(self) -> Any:
        """Initializes the Gemini Client with fallback for CI/CD environments."""
        running_under_pytest = "PYTEST_CURRENT_TEST" in os.environ

        if running_under_pytest:
            return self._create_mock_client()
        
        try:
            return genai.Client(api_key=self.settings.GOOGLE_API_KEY)
        except Exception as e:
            print(f"   ⚠️ Connection Failure: {e}")
            return self._create_mock_client()

    def _create_mock_client(self) -> Any:
        """Creates a dummy client for testing/offline mode."""
        class MockResponse:
            text: str = "I have executed the requested operation based on internal simulation."
        
        class MockModels:
            def generate_content(self, model: str, contents: str) -> MockResponse:
                return MockResponse()
        
        class MockClient:
            models = MockModels()
            
        return MockClient()

    def _initialize_mcp(self) -> None:
        """Initialize MCP (Model Context Protocol) integration."""
        try:
            from system.kernel.mcp_client import MCPClientManagerSync
            from system.tools.mcp_tools import _set_mcp_manager

            self.mcp_manager = MCPClientManagerSync()
            if self.mcp_manager:
                self.mcp_manager.initialize()
                _set_mcp_manager(self.mcp_manager._async_manager)

                mcp_tools = self.mcp_manager.get_all_tools_as_callables()
                if mcp_tools:
                    self.available_tools.update(mcp_tools)
                    self.state.mcp_active = True
                    print(f"   🔧 MCP Active: {len(mcp_tools)} remote tools linked.")

        except Exception as e:
            print(f"   ⚠️ MCP Init Error: {e}")

    def _load_tools(self) -> Dict[str, Callable[..., Any]]:
        """Dynamically mounts tools from system/tools/."""
        tools: Dict[str, Callable[..., Any]] = {}
        tools_dir = self.root_dir / "system" / "tools"
        
        if not tools_dir.exists():
            return tools

        for tool_file in tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"): continue
            
            try:
                module_name = tool_file.stem
                spec = importlib.util.spec_from_file_location(f"system.tools.{module_name}", tool_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module, inspect.isfunction):
                        if not name.startswith("_") and obj.__module__ == module.__name__:
                            tools[name] = obj
            except Exception as e:
                print(f"   ⚠️ Failed to mount tool {tool_file.name}: {e}")
        
        return tools

    def _log_thought(self, stage: str, content: str) -> None:
        """Persists internal monologue to artifacts."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"thought_stream_{timestamp}.md"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"## [{stage}] {datetime.now().isoformat()}\n")
            f.write(f"{content}\n\n")

    def _call_gemini(self, prompt: str) -> str:
        """Executes a neural query against the Gemini Substrate."""
        try:
            response = self.client.models.generate_content(
                model=self.settings.GEMINI_MODEL_NAME,
                contents=prompt,
            )
            text = getattr(response, "text", None) or getattr(response, "content", "")
            return str(text).strip()
        except Exception as e:
            return f"Error: Neural Link Unstable ({e})."

    def _extract_tool_call(self, response_text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parses the 'Decision' phase for actionable tool calls."""
        cleaned = response_text.strip()
        try:
            if "{" in cleaned and "}" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                json_str = cleaned[start:end]
                payload = json.loads(json_str)
                if isinstance(payload, dict):
                    action = payload.get("action") or payload.get("tool")
                    args = payload.get("args") or payload.get("input") or {}
                    if action: return str(action), args
        except: pass
        return None, {}

    def observe(self, task: str) -> None:
        """Phase 1: Ingest input and mission context."""
        self.transition("OBSERVE")
        self.state.current_task = task
        self.memory.add_entry("user", task)
        print(f"👀 [OBSERVE] Task Ingested: {task}")

    def orient(self) -> None:
        """Phase 2: Load memory and tool schemas."""
        self.transition("ORIENT")
        tool_list = "\n".join([f"- {n}: {f.__doc__}" for n, f in self.available_tools.items()])
        self.state.last_thought = f"Loaded {self.state.tools_loaded} tools. Constructing context..."
        
        system_prompt = (
            "IDENTITY: Hyperscale Engineering Agent (ARC).\n"
            "PROTOCOL: recursive_self_improvement_v1.\n"
            f"AVAILABLE TOOLS:\n{tool_list}\n\n"
            "INSTRUCTION: To use a tool, output JSON: {\"action\": \"tool_name\", \"args\": {...}}.\n"
            "Otherwise, provide the final answer."
        )
        
        self.current_context: List[Dict[str, str]] = self.memory.get_context_window(
            system_prompt=system_prompt,
            max_messages=10,
            summarizer=lambda x, y: self._call_gemini(f"Summarize these memory entries: {x}")
        )

    def decide(self) -> Tuple[Optional[str], Dict[str, Any]]:
        """Phase 3: Query neural core for next action."""
        self.transition("DECIDE")
        formatted_context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in self.current_context])
        final_prompt = f"{formatted_context}\n\nUSER TASK: {self.state.current_task}"
        
        print("⚡ [DECIDE] Querying Neural Core...")
        decision = self._call_gemini(final_prompt)
        self.state.decision = decision
        self._log_thought("DECISION", decision)
        
        return self._extract_tool_call(decision)

    def act(self, tool_name: Optional[str], tool_args: Dict[str, Any]) -> None:
        """Phase 4: Execute tool or return final response."""
        self.transition("ACT")
        
        if not tool_name:
            print("🏁 [ACT] No tool call detected. Finalizing response.")
            self.state.observation = self.state.decision
            return
        
        observation: str = ""
        print(f"🛠️ [ACT] Invoking: {tool_name}")
        tool_fn = self.available_tools.get(tool_name)
        
        if tool_fn:
            try:
                result = tool_fn(**tool_args)
                observation = str(result)
            except Exception as e:
                observation = f"Tool Failure: {e}"
        else:
            observation = "Error: Tool not found."

        self.state.observation = observation
        self.memory.add_entry("assistant", str(self.state.decision))
        self.memory.add_entry("tool", f"Observation from {tool_name}: {observation}", metadata={"tool": tool_name})
        
        # Second act: Synthesis
        print("🧪 [ACT] Synthesizing tool output...")
        synthesis_prompt = (
            f"TASK: {self.state.current_task}\n"
            f"DECISION: {self.state.decision}\n"
            f"TOOL_OUTPUT: {observation}\n"
            "INSTRUCTION: Provide the final answer based on the tool output."
        )
        final_answer = self._call_gemini(synthesis_prompt)
        self.state.observation = final_answer
        self.memory.add_entry("assistant", final_answer)

    def reflect(self) -> None:
        """Phase 5: Post-action audit and self-learning."""
        self.transition("REFLECT")
        
        observation_text = str(self.state.observation).lower() if self.state.observation else ""
        is_failure = "error" in observation_text or "failed" in observation_text or "failure" in observation_text
        
        reflection_type = "CRITICAL ANALYSIS" if is_failure else "REINFORCEMENT"
        
        prompt = (
            f"GOAL: {self.state.mission_objective}\n"
            f"TASK: {self.state.current_task}\n"
            f"DECISION: {self.state.decision}\n"
            f"OUTCOME: {self.state.observation}\n"
            f"INSTRUCTION: Perform a {reflection_type}. "
            f"{'Analyze why it failed and propose a fix.' if is_failure else 'Analyze why it succeeded and consolidate the strategy.'}"
        )
        
        print(f"🪞 [REFLECT] Generating {reflection_type}...")
        insight = self._call_gemini(prompt)
        
        self._log_thought("REFLECTION", insight)
        self.memory.add_entry("system", f"REFLECTION ({reflection_type}): {insight}")
        
        self.transition("IDLE")

    def run(self, task: str) -> None:
        """Orchestrates the OODA loop."""
        print(f"\n▶️ EXECUTION START: {task}")
        try:
            self.observe(task)
            self.orient()
            tool_name, tool_args = self.decide()
            self.act(tool_name, tool_args)
            self.reflect()
            print(f"\n🏁 EXECUTION FINISH. Result:\n{self.state.observation}")
        except Exception as e:
            print(f"❌ EXECUTION FAILED: {e}")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Cleanup Protocol."""
        if self.mcp_manager:
            self.mcp_manager.shutdown()
        print("💤 System Offline.")

if __name__ == "__main__":
    agent = GeminiAgent()
    task = sys.argv[1] if len(sys.argv) > 1 else "Perform system diagnostic."
    agent.run(task)
