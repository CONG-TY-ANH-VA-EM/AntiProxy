---
description: how to troubleshoot urgent issues
---

# Triage Master (The "911" Operator)
*Adapted from COS v3.0 Workflow Triage Master*

**Objective:** Route the issue to the correct workflow in < 30 seconds.

## Phase 1: The Diagnostic Question
**Action:** Ask: *"What is the bleeding neck problem right now?"*

### A. "The build is broken."
*   **Go to:** `Build System`
    *   **CI/CD failing?** -> Check `.github/workflows`.
    *   **Docker build failing?** -> Run `/build`.
    *   **Dependencies missing?** -> Run `npm install` or `pip install`.

### B. "The application is crashing."
*   **Go to:** `Runtime`
    *   **Frontend crash?** -> Check browser console + `/lint`.
    *   **Backend 500?** -> Check `docker-compose logs` + `/database`.
    *   **Streaming broken?** -> Check `src/agent.py` + `/testing`.

### C. "The code is messy / lint errors."
*   **Go to:** `Code Quality`
    *   **Type errors?** -> `/lint`.
    *   **Formatting?** -> Run `black` or `prettier`.
    *   **Refactoring needed?** -> Run `/feature_launch` (Stage 1).

### D. "I need to deploy updates."
*   **Go to:** `Operations`
    *   **Production deploy?** -> `/deployment`.
    *   **Database migration?** -> `/database`.

## Phase 2: The Command
**Action:** Once identified, run the specific command.
*   *Example:* "The backend is 500ing." -> **Run:** `docker-compose logs -f backend`

## Phase 3: Root Cause Analysis
*   If the issue was major, follow up with `/post_mortem`.
