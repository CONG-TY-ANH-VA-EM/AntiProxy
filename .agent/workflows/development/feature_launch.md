---
description: how to launch a new feature
---

# Feature Launch Protocol
*Adapted from COS v3.0 Master Workflow*

**Objective:** Introduce a new feature or technology to the codebase with high confidence.

## Stage 1: Technical Validation (The "Why")
1.  **Review Requirements:** Read the `USER_STORY.md` or issue description.
2.  **Architecture Check:** Ensure this fits the system design (`ARCHITECTURE_DOC.md`).
3.  **Output:** Create a brief plan in `task.md`.

## Stage 2: The "Seed" Phase (implementation)
// turbo
1.  **Create Branch:** `git checkout -b feature/name-of-feature`
2.  **Implementation:** Write code in `src/`.
3.  **Local Test:** Verify functionality locally.

## Stage 3: The "Scale" Phase (Verification)
1.  **Automated Tests:** Run `/testing` workflow.
2.  **Manual Verification:** Check flows in the browser (if UI).
3.  **Documentation:** Update `README.md` or code comments.

## Stage 4: Delivery
// turbo
1.  **Commit:** `git commit -m "feat: description"`
2.  **Merge:** Merge to main (after review).
3.  **Deploy:** Run `/deployment`.
