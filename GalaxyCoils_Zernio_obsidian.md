---
tags: [galaxycoils, zernio, instagram, threads, automation, pexels]
last-updated: 2026-05-23
---

# GalaxyCoils Zernio

Automated Instagram + Threads scheduling for @galaxycoils using Pexels drone footage and the Zernio CLI.

> **Handoff:** [[PROJECTS/GalaxyCoils-Zernio/STATE_HANDOFF]] · **Graph:** `graphify-out/graph.html` in repo

## Architecture (2026-05-23)

| Layer | Detail |
|-------|--------|
| Source | Pexels API (portrait, ≤40s) |
| Media | `ensure_zernio_media_url` → ffmpeg H.264 1080p → `zernio media:upload` |
| Posting | **Paired posts** — separate Zernio schedules for IG and Threads |
| IG caption | Base + SEO tags + `apply_dedup_suffix()` |
| Threads caption | `build_threads_caption()` (no IG hashtag block) |
| Dedup | `history.log` + API + per-post `#uuid` suffix |
| Slots | 10, 13, 16, 19, 22 UTC — 5/day via `schedule_5_per_day.py` |

## Account IDs
- Instagram: `6a0afc8a5e333c0529912a50`
- Threads: `6a0f83d7520992756d97578f`

## Key scripts
| Script | Role |
|--------|------|
| `schedule_5_per_day.py` | Main scheduler (paired posts) |
| `scripts/post_utils.py` | `create_paired_posts`, retries, CDN upload |
| `scripts/threads_utils.py` | Threads caption builder |
| `scripts/split_scheduled_queue.py` | Migrate unified → paired queue |
| `scripts/secure_dedup.py` | Pexels + queue dedup |
| `scripts/verify_queue.py` | Audit + CLI error log summary |

## Queue (2026-05-23)
- **55 scheduled** unified posts — run migration before relying on paired flow in production queue
- See [[Queue State]]

## Branch
`fix/zernio-dedup-threads-crosspost` @ `f1eea1e` (pushed)

## Testing
- 92+ unit tests — `make full-audit`
- Pre-push hook runs full audit

## See also
- [[GalaxyCoils Memory]]
- [[WIKI]]
- [[Zernio CLI Learnings]]
- [[Instagram-Automation]]
- [[MEMORY/REFLECTIONS/2026-05-23-paired-posts-migration]]
