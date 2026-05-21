# VIRALITY STRATEGY: GALAXYCOILS
## Goal: >3.6% Engagement Rate (ER)
## Status: Implemented 2026-05-20

### 1. The Content Mix (Engagement Pivot)
*   **30% Empty Captions:**
    *   Best live result: 3.63% ER. High-tension drone visuals outperform explanatory captions.
    *   Goal: Watch-time, shareability, algorithm-push.
*   **30% CTA (Calls to Action):**
    *   High-intent hooks: "Rate this 1-10", "Tag a friend", "Yes or No."
    *   Goal: Comments, engagement, community.
*   **22% Micro-hooks:**
    *   Short, punchy one-liners: "Too smooth.", "Locked in.", "Frame it tighter."
    *   Goal: Low-friction text overlay that doesn't distract from visuals.
*   **18% Value/Save-Bait (Authority):**
    *   "Save this: 3 drone moves that instantly look more cinematic."
    *   Goal: Saves, follows, authority building.

### 2. Execution Protocol
*   **Deduplication:** Use `scripts/secure_dedup.py` before scheduling. Three-layer check: history.log + published + scheduled.
*   **Staggered Schedule:** Maintain the 5/day cadence (10, 13, 16, 19, 22 UTC).
*   **Sourcing:** Fetch Pexels video via `requests` library. `choose_video_url()` ranks by height proximity to 1920 (favors HD/4K over lower resolutions). Avoid generic stock shots.
*   **Rate Limiting:** Zernio CLI rate-limited. Retry with 60s backoff on 429.

### 3. Implementation History
1.  ✅ **Purge Queue:** Cleared "Day X", "Delivery", generic hashtag-only templates.
2.  ✅ **Queue Rebuild:** Rebuilt 45-post queue with new caption architecture (2026-05-20).
3.  ✅ **Caption Centralization:** `scripts/captions_pool.py` — single source for MICRO_HOOKS, VALUE_CAPTIONS, CTA_CAPTIONS (21 entries).
4.  ✅ **Engagement Pivot Deployed:** `schedule_5_per_day.py` updated to 30/30/22/18 mix.
5.  🔄 **Monitor:** Cron job `galaxycoils-viral-monitor` (ID b32b51d9e63b) every 4 hours.

