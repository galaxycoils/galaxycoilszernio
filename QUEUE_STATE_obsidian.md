---
tags: [queue, state, snapshot, galaxycoils]
last-updated: 2026-05-23
---

# Queue State

> [!warning] Snapshot 2026-05-23 — queue still **unified**; migration to paired posts **pending**

| Metric | Value |
|---|---|
| Scheduled Zernio posts | **55** |
| Format | Unified (1 post → IG + Threads platforms each) |
| IG-only / Threads-only | 0 |
| Duplicates (Pexels) | 0 |
| Published overlap | 0 |

## After migration (expected)
| Metric | Value |
|---|---|
| Scheduled posts | **110** (55 × 2 paired) |
| Format | Separate IG post + separate Threads post per slot |

Run: `python3 scripts/split_scheduled_queue.py --execute`

## Branch / code state
- Branch: `fix/zernio-dedup-threads-crosspost` @ `f1eea1e`
- New schedules use `create_paired_posts()` automatically
- Existing 55 unified posts need `split_scheduled_queue.py`

## Dynamic caption mix
Weights: `logs/engagement_weights.json` (from engagement optimizer)

## See Also
- [[PROJECTS/GalaxyCoils-Zernio/STATE_HANDOFF]]
- [[GalaxyCoils Zernio]]
- [[GalaxyCoils Memory]]
- [[WIKI]]
