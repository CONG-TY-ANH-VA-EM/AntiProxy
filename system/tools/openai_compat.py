"""
🤖 OpenAI Protocol Bridge.

Designation: Sys/Tools/OpenAICompat
Purpose: Enables the Agent to consult external LLMs (GPT-4, Claude, Llama 3) 
         via the standard OpenAI Chat Completion API.
"""

import requests # type: ignore
import json
from typing import Optional, List, Dict, Any, Union

# Internal Imports
try:
    from system.config import settings
except ImportError:
    # Fallback if running standalone
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from system.config import settings


def consult_external_llm(
    query: str,
    system_instruction: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Consults an external OpenAI-compatible LLM for a second opinion or specialized task.

    Use this tool when:
    1. You need a different perspective (e.g., asking GPT-4 to review Gemini's code).
    2. You need to access a local model via Ollama (set OPENAI_BASE_URL to localhost).

    Args:
        query: The main question or task description.
        system_instruction: The persona or constraints for the external model.
        model: (Optional) Specific model identifier. Defaults to config settings.
        temperature: Creativity setting (0.0 = deterministic, 1.0 = creative).

    Returns:
        String containing the external model's response.
    """
    base_url = settings.OPENAI_BASE_URL
    api_key = settings.OPENAI_API_KEY
    target_model = model or settings.OPENAI_MODEL

    # Validation
    if not base_url:
        return "Error: OPENAI_BASE_URL is not configured in settings."
    
    # Normalize URL
    if not base_url.endswith("/v1"):
        endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"
    else:
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
    
    # Correction for Ollama/LocalAI which might not use /v1/chat/completions strictly
    # If the user provided the full path, respect it.
    if "chat/completions" in base_url:
        endpoint = base_url

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else ""
    }

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": query}
        ],
        "temperature": temperature,
        "max_tokens": 1024
    }

    try:
        # Timeout set to 60s for slower local models
        response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            return f"Error: API returned status {response.status_code}\nResponse: {response.text}"

        data = response.json()
        
        # Safe extraction
        choices = data.get("choices", [])
        if not choices:
            return "Error: No choices returned in API response."
            
        content = choices[0].get("message", {}).get("content", "")
        
        if not content:
            return "Error: Empty content received."
            
        return str(content)

    except requests.exceptions.Timeout:
        return "Error: External LLM request timed out (60s)."
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to {base_url}. Is the server running?"
    except json.JSONDecodeError:
        return f"Error: Invalid JSON response from server.\nRaw: {response.text[:200]}"
    except Exception as e:
        return f"Error: Unexpected failure calling external LLM: {str(e)}"
