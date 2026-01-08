# Plan: Initialization & Architectural Singularity Step 1

**ID:** `plan_initialization`
**Objective:** Refactor Kernel into a State Machine and enforce Pydantic rigor.

## Strategy
1. **Memory:** Transition from raw JSON to Pydantic models.
2. **Kernel:** Decouple the OODA loop into discrete state handlers.
3. **Safety:** Implement regression tests in `sys/tests/`.

## Tactical Steps
- `sys/kernel/memory.py`: Define `MemoryEntry` and `MemoryState`.
- `sys/kernel/agent.py`: Introduce `AgentState` transitions.
- `sys/tests/`: Add baseline unit tests.

## Verification
- `pytest sys/tests/`
- `mypy sys/kernel/`
