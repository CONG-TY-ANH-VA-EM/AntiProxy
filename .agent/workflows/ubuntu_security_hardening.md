---
description: Standard build for staff desktops.
---

# 🐧 Ubuntu Desktop Security Hardening

**Objective:** Secure the endpoints.

## Phase 1: The Build
**Action:** Install.
*   **OS:** Ubuntu LTS (Long Term Support) only. 24.04.
*   **Disk Encryption:** LUKS enabled during install (Essential for laptops).

## Phase 2: The Firewall
**Action:** UFW.
*   **Command:** `sudo ufw enable`.
*   **Policy:** Deny incoming, Allow outgoing.

## Phase 3: Updates
**Action:** Auto-patch.
*   **Config:** Enable "Unattended Upgrades" for security updates.
*   **Browser:** Snap auto-updates Firefox/Chromium.

## Output
*   **Artifact:** `hardening_checklist.md`
