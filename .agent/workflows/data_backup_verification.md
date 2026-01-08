---
description: Did the server actually back up last night?
---

# 💾 Data Backup Verification

**Objective:** Survive a ransomware attack or fire.

## Phase 1: The Automated Check
**Action:** Check logs.
*   **Status:** "Success"?
*   **Size:** Is the backup file size consistent with previous days? (If it's 0kb, it failed).

## Phase 2: The Restoration Test (Monthly)
**Action:** Prove it works.
*   **Task:** Pick one random file from the backup and try to open it.

## Phase 3: The Offsite
**Action:** 3-2-1 Rule.
*   **3** Copies of data.
*   **2** Different media (Disk/Cloud).
*   **1** Offsite (Cloud typically). Verify Cloud sync is active.

## Output
*   **Artifact:** `backup_log_[date].md`
