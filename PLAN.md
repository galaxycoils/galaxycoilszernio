# VIRALITY STRATEGY: GALAXYCOILS
## Goal: >3.6% Engagement Rate (ER)

### 1. The Content Mix (80/20)
*   **80% Pure Engagement (Viral):**
    *   Content: High-tension, unique angle drone footage (FPV forest runs, massive scale, architectural beauty).
    *   Caption: [NULL] or single emoji (e.g., 🚁, 🌊, 🔥).
    *   Goal: Watch-time, shareability, algorithm-push.
*   **20% Value/Save-Bait (Authority):**
    *   Content: Bulleted SaaS tips, drone tech workflows, location scouting maps.
    *   Caption: "Save this for your next shoot. [List of 3-5 tools/tips]."
    *   Goal: Saves, follows, community building.

### 2. Execution Protocol
*   **Deduplication:** Always use `dedup.py` before scheduling. Purge stale "Day X" from `zernio posts`.
*   **Staggered Schedule:** Maintain the 5/day cadence (10, 13, 16, 19, 22 UTC).
*   **Sourcing:** Fetch only UHD/4K media. Avoid generic stock shots; look for unique perspective/motion.

### 3. Immediate Action Plan
1.  **Purge Queue:** Clear all pending "Day X" templates to stop the fatigue.
2.  **Audit:** Analyze recent "5 SaaS Tools" performance vs. "Day X" performance to confirm engagement drop-off.
3.  **Deploy:** Rotate the new caption logic into the `schedule_5_per_day.py` script.
4.  **Monitor:** Trigger analytics sweep in 48 hours to confirm ER trend shift.
