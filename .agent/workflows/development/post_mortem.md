---
description: how to conduct a post-mortem for incidents
---

# Post-Mortem Analysis (Retrospective)
*Adapted from COS v3.0 PMO Protocol*

**Objective:** Don't make the same mistake twice.

## Phase 1: The Timeline
**Action:** Establish facts.
1.  **Trigger:** When did the incident start?
2.  **Detection:** When did we notice?
3.  **Resolution:** When was it fixed?

## Phase 2: The Root Cause (5 Whys)
**Action:** Dig deep.
*   *Example:*
    *   Why did the build fail? -> Context missing.
    *   Why? -> API changed.
    *   Why? -> No integration test for that API. (Root Cause)

## Phase 3: The Action Plan
**Action:** Fix the system, not just the bug.
1.  **Immediate Fix:** Apply patch (done).
2.  **Preventative:** Add test case to `/testing` workflow.
3.  **Process:** Update `maintenance_schedule.md` or similar.

## Output
*   **Artifact:** Create a `post_mortem_YYYY_MM_DD.md` in `docs/incidents/`.
