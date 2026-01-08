import io
import contextlib
from typing import Dict, Any, List

def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Executes Python code in a controlled ephemeral environment for calculation and logic.
    Adapted from CodeSandboxSkill.
    
    Args:
        code: The python code to execute.
    """
    print("📦 [SANDBOX] Executing code snippet...")
    
    # Safety restrictions (Basic)
    forbidden = ["import os", "import subprocess", "open(", "delete", "remove"]
    for bad in forbidden:
        if bad in code:
            return {"status": "error", "error": f"Security Violation: '{bad}' is forbidden."}
    
    # Capture stdout
    buffer = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(buffer):
            # Using a limited global scope
            safe_globals = {"__builtins__": __builtins__, "print": print, "range": range, "len": len}
            exec(code, safe_globals)
            
        output = buffer.getvalue()
        print(f"   Output size: {len(output)} chars")
        return {
            "status": "success",
            "output": output,
            "code_executed": code
        }
    except Exception as e:
        print(f"❌ [SANDBOX] Failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
