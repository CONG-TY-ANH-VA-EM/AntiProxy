"""
⚙️ System Configuration Matrix.

Designation: Sys/Config
Purpose: Centralized management of environment variables and runtime constants.
Capabilities:
- Pydantic-based validation.
- Auto-loading from .env.
- Default path resolution for 'Hyperscale' directory topology.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define Root Paths
# Assumes this file is in system/config.py -> parent is system/ -> parent is root
ROOT_DIR = Path(__file__).parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
SYSTEM_DIR = ROOT_DIR / "system"

class MCPServerConfig(BaseSettings):
    """Configuration schema for a single MCP node."""
    name: str = Field(..., description="Unique identifier for the server node.")
    transport: str = Field("stdio", pattern="^(stdio|http|sse)$")
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    
    model_config = SettingsConfigDict(extra="ignore")

class Settings(BaseSettings):
    """
    Global Runtime Configuration.
    Reads from system env vars, then .env file, then defaults.
    """

    # --- Neural Link (Google Gemini) ---
    GOOGLE_API_KEY: str = Field(default="", description="Primary authentication key for Gemini 3.")
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash-exp"

    # --- Agent Identity ---
    AGENT_NAME: str = "Antigravity Recursive Core"
    DEBUG_MODE: bool = False

    # --- Cognitive Substrate (Memory) ---
    # Path relative to root, or absolute path
    MEMORY_FILE: str = str(ARTIFACTS_DIR / "memory" / "agent_memory.json")

    # --- MCP (Model Context Protocol) ---
    MCP_ENABLED: bool = Field(default=False, description="Master switch for external tool connectivity.")
    MCP_SERVERS_CONFIG: str = str(ROOT_DIR / ".antigravity" / "mcp_servers.json")
    MCP_CONNECTION_TIMEOUT: int = 30
    MCP_TOOL_PREFIX: str = "mcp_"

    # --- Fallback/Legacy LLM Support ---
    OPENAI_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"), 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Singleton Instantiation
settings = Settings()

# Validation hook to ensure critical directories exist
def ensure_directories() -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    (ARTIFACTS_DIR / "memory").mkdir(exist_ok=True)
    (ARTIFACTS_DIR / "logs").mkdir(exist_ok=True)
    (ARTIFACTS_DIR / "plans").mkdir(exist_ok=True)

ensure_directories()
