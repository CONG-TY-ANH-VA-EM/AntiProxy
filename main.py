import sys
import os
from pathlib import Path

# Ensure 'system' is in python path
root_dir = Path(__file__).parent.resolve()
sys.path.append(str(root_dir))

def main():
    """
    Standard Entrypoint for the Antigravity Agent.
    """
    from system.kernel.agent import GeminiAgent
    
    # Check for prompt arg
    task = "Assess internal system health."
    if len(sys.argv) > 1:
        task = sys.argv[1]
        
    print(f"🤖 Antigravity Agent Kernel Initializing...")
    print(f"📋 Task: {task}")
    
    agent = GeminiAgent()
    agent.run(task)

if __name__ == "__main__":
    main()
