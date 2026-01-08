# 📐 Engineering Standard Operating Procedures (SOP)

## 1. Architectural Topology & Segregation

**CRITICAL:** You operate in two distinct modes. Code style depends on the target directory.

### A. The Kernel (`sys/`)
*   **Purpose:** Recursive Self-Improvement.
*   **Constraint:** Logic here must be **Stateless** and **Idempotent**.
*   **Interactions:** Use `sys/tools/` for all side effects (I/O, Network). The Kernel (`agent.py`) is a pure decision router.

### B. The Workspace (`workspace/`)
*   **Purpose:** Product Delivery (The Client's App).
*   **Constraint:** **Zero Vendor Lock-in**. Code here MUST NOT import from `sys/`.
*   **Dependency:** Must utilize a local `requirements.txt`.

---

## 2. Pythonic Rigor & Type Safety

We adhere to **Python 3.12+** standards. Code must pass `mypy --strict`.

### 2.1. Strict Typing (No `Any`)
Every function, method, and class attribute MUST have type hints.
*   **Forbidden:** `def process(data):` (Implicit `Any` is banned).
*   **Mandatory:** `def process(data: dict[str, int]) -> bool:`
*   **Reasoning:** LLMs rely on type signatures to understand tool inputs/outputs without hallucinations.

### 2.2. Documentation as Interface
Docstrings are not comments; they are **Prompt Context** for the AI.
*   **Format:** Google Style Guide.
*   **Requirement:** Every tool function in `sys/tools/` MUST explain *when* to use it and *what* edge cases exist.

```python
def query_database(query: str) -> list[Record]:
    """Executes a read-only SQL query against the internal DB.

    Args:
        query: Valid SQL SELECT statement.

    Returns:
        List of Record objects containing rows.

    Raises:
        DatabaseConnectionError: If the socket is closed.
    """
```

---

## 3. Data Interchange & Schema Validation

### 3.1. Pydantic First (Protocol Buffers for AI)
Never pass raw dictionaries or unstructured tuples for complex logic. Use `pydantic` (v2) models.

*   **Why:** It ensures the Agent generates valid JSON that matches the code's expectations.
*   **Rule:** All Tool arguments should effectively be Pydantic models.

```python
from pydantic import BaseModel, Field

class AnalysisRequest(BaseModel):
    ticker: str = Field(..., description="The stock symbol, e.g., AAPL")
    period: str = Field("1mo", description="Time period for analysis")

def analyze_stock(request: AnalysisRequest) -> AnalysisResult:
    ...
```

### 3.2. Structured Returns
Tools must never return raw strings (unless it's a simple log). Return structured objects to allow the Agent to reason about the result.

*   **Bad:** `return "Error: File not found"`
*   **Good:** `return ToolResult(success=False, error="File not found", metadata={"path": ...})`

---

## 4. Resilience & Cognitive Patterns

### 4.1. Graceful Degradation
*   **Prohibition:** Tools must NEVER crash the main event loop.
*   **Pattern:** Catch expectations locally and return a failure state.
*   **Log:** Log the traceback to `artifacts/logs/error.log`, but return a clean error message to the LLM context.

### 4.2. Asynchronous Core
*   Prefer `async/await` for all I/O bound operations (Network/Disk).
*   The Agent's kernel is capable of parallel execution; blocking code bottlenecks the swarm.

---

## 5. Testing & Verification

### 5.1. The "Mutation Proof" Rule
*   You are not allowed to modify `sys/kernel/` without adding a corresponding test in `sys/tests/`.
*   Tests must be atomic and mock external API calls.

### 5.2. Linter Compliance
*   Code should adhere to `ruff` or `black` formatting standards.
*   Clean code reduces token usage and improves LLM comprehension during introspection.
