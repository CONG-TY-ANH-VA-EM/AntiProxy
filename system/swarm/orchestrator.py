"""
🐝 Distributed Intelligence Orchestration.

Designation: Sys/Swarm/Orchestrator
Purpose: Implements the Router-Worker pattern for parallel task execution.
Capabilities:
- Dynamic Worker Discovery.
- Message Bus for context sharing.
- Fault-tolerant delegation loop.
"""

import importlib
import importlib.util
import pkgutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, cast
from datetime import datetime
from pydantic import BaseModel, Field

# Internal Imports
# We assume standard agents are in system/swarm/agents/
# If they don't exist yet, we'll need to create stubs or handle gracefully.
AGENTS_PACKAGE = "system.swarm.agents"

class SwarmMessage(BaseModel):
    """Schema for inter-agent communication."""
    sender: str
    recipient: str
    msg_type: str = Field(pattern="^(task|result|error|query)$")
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class MessageBus:
    """Synchronous Event Bus for Swarm Context."""
    
    def __init__(self) -> None:
        self._ledger: List[SwarmMessage] = []
    
    def send(self, sender: str, recipient: str, msg_type: str, content: str) -> None:
        msg = SwarmMessage(
            sender=sender, 
            recipient=recipient, 
            msg_type=msg_type, 
            content=str(content)
        )
        self._ledger.append(msg)
    
    def get_context(self, agent_name: str) -> List[SwarmMessage]:
        """Retrieves messages where the agent is sender or recipient."""
        return [m for m in self._ledger if m.sender == agent_name or m.recipient == agent_name]
    
    def dump(self) -> List[Dict[str, Any]]:
        return [m.model_dump() for m in self._ledger]
    
    def clear(self) -> None:
        self._ledger = []

class SwarmOrchestrator:
    """
    The Hive Mind Controller.
    Manages the lifecycle of specialized sub-agents.
    """
    
    def __init__(self) -> None:
        print("   🐝 Initializing Swarm Intelligence Grid...")
        self.bus = MessageBus()
        self.workers: Dict[str, Any] = {}
        self.router: Any = None
        
        self._recruit_agents()

    def _recruit_agents(self) -> None:
        """
        Dynamically discovers and loads agent classes from system/swarm/agents/.
        Allows the system to 'grow' new agents without code changes here.
        """
        # Define path to agents directory
        root = Path(__file__).parent.parent.parent
        agents_dir = root / "src" / "agents"
        
        if not agents_dir.exists():
            print(f"   ⚠️ Swarm Barracks Empty: {agents_dir} not found.")
            return

        # Add parent dir to sys.path to allow imports
        if str(root) not in sys.path:
            sys.path.append(str(root))

        for file_path in agents_dir.glob("*_agent.py"):
            module_name = file_path.stem
            try:
                # Import module: system.swarm.agents.coder_agent
                full_module_name = f"src.agents.{module_name}"
                spec = importlib.util.spec_from_file_location(full_module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find class ending in 'Agent'
                    for attr_name in dir(module):
                        if attr_name.endswith("Agent") and attr_name != "BaseAgent":
                            agent_class = getattr(module, attr_name)
                            instance = agent_class()
                            
                            # Router is special
                            if "Router" in attr_name:
                                self.router = instance
                                print(f"      👑 Router Online: {attr_name}")
                            else:
                                # Infer role from filename: coder_agent -> coder
                                role = module_name.replace("_agent", "")
                                self.workers[role] = instance
                                print(f"      👷 Worker Online: {role.upper()}")
                                
            except Exception as e:
                print(f"   ⚠️ Failed to recruit {module_name}: {e}")

    def execute(self, task: str, verbose: bool = True) -> str:
        """
        Main Swarm Execution Loop.
        1. Router decomposes task.
        2. Workers execute sub-tasks.
        3. Router synthesizes results.
        """
        if not self.router:
            return "Error: Swarm Router not initialized."

        if verbose: print(f"   🐝 Swarm Activation: {task}")
        
        # 1. Delegation Phase
        try:
            delegation_plan: List[Dict[str, str]] = self.router.analyze_and_delegate(task)
        except Exception as e:
            return f"Router Panic: {e}"

        results: List[str] = []
        
        # 2. Execution Phase
        for step in delegation_plan:
            worker_role = step.get('agent', '')
            sub_task = step.get('task', '')
            
            worker = self.workers.get(worker_role)
            if not worker:
                err = f"Error: Worker '{worker_role}' unavailable."
                results.append(err)
                continue
            
            if verbose: print(f"      👉 Delegating to [{worker_role.upper()}]: {sub_task}")
            
            self.bus.send("router", worker_role, "task", sub_task)
            
            try:
                # Pass context if supported
                ctx = self.bus.get_context(worker_role)
                # Convert context to expected format for agents
                agent_ctx = [{"from": m.sender, "content": m.content} for m in ctx]
                
                # Execute
                outcome = str(worker.execute(sub_task, context=agent_ctx))
                    
                results.append(outcome)
                self.bus.send(worker_role, "router", "result", outcome)
                
            except Exception as e:
                err = f"Worker {worker_role} Failed: {e}"
                results.append(err)
                self.bus.send(worker_role, "router", "error", err)

        # 3. Synthesis Phase
        if verbose: print("      🔄 Synthesizing Intelligence...")
        try:
            final_output = str(self.router.synthesize_results(delegation_plan, results))
        except Exception as e:
            final_output = f"Synthesis Failed: {e}. Raw Results: {results}"
            
        return final_output

    def reset(self) -> None:
        self.bus.clear()
        # Reset internal state of agents if they have it
        if self.router and hasattr(self.router, "reset"):
            getattr(self.router, "reset")()
        for w in self.workers.values():
            if hasattr(w, "reset"):
                getattr(w, "reset")()
