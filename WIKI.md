---
tags: [wiki, documentation, reference, galaxycoils]
last-updated: 2026-05-23
---

# WIKI

> [!info] Project wiki for GalaxyCoils Zernio.

## Quick Links
- [[GalaxyCoils Zernio]] — Architecture, scripts, paired IG/Threads posting
- [[GalaxyCoils Memory]] — Keys, branch, queue state, design decisions
- [[PROJECTS/GalaxyCoils-Zernio/STATE_HANDOFF]] — **Start here** for next dev pickup
- [[Zernio CLI Learnings]] — CLI quirks, platform errors
- [[Queue State]] — Scheduled queue snapshot
- [[Instagram-Automation]] — Automation rules, recovery

## Repo & CI
- Public repo: github.com/galaxycoils/galaxycoilszernio
- Active work: branch `fix/zernio-dedup-threads-crosspost`
- Pre-push hook: `make full-audit`
- GitHub Actions CI: Python 3.12, push/PR to master

## Posting Model (current)
| Step | What happens |
|------|----------------|
| Pexels | Portrait video, ≤40s, deduped via `secure_dedup` |
| CDN | `ensure_zernio_media_url` — download + ffmpeg compress + `zernio media:upload` |
| Instagram | `create_single_post` with SEO tags + hashtags |
| Threads | Separate post, `build_threads_caption`, no IG hashtag block |
| Dedup | Unique ` #uuid` suffix on each platform caption |

## Scripts Inventory
| File | Purpose |
|---|---|
| schedule_5_per_day.py | Main scheduler — **paired** IG + Threads posts |
| schedule_10_per_day.py | High-volume scheduler — paired posts |
| scripts/post_utils.py | `create_paired_posts`, `apply_dedup_suffix`, retries |
| scripts/threads_utils.py | `build_threads_caption`, `strip_ig_seo_block`, `enrich_for_threads` |
| scripts/split_scheduled_queue.py | **Migrate** unified scheduled → paired posts |
| scripts/unify_scheduled_queue.py | Legacy: merge separate posts → unified (opposite direction) |
| scripts/secure_dedup.py | Dedup (history + API) |
| scripts/verify_queue.py | Queue audit + `cli_errors.log` summary |
| fill_schedule_gaps.py | Gap filler |
| purge_zernio_duplicates.py | Duplicate purger |

(Full list: see [[GalaxyCoils Zernio]] or repo root.)

## Migration (required for existing queue)
```bash
python3 scripts/split_scheduled_queue.py              # dry-run
python3 scripts/split_scheduled_queue.py --execute    # apply (backs up first)
python3 scripts/split_scheduled_queue.py --execute --limit 5  # pilot
```

## Test Suites
| Suite | Tests (approx.) |
|---|---|
| test_secure_dedup | 18 |
| test_post_utils | 24 |
| test_threads_utils | 4 |
| test_purge_dedup | 10 |
| test_fill_gaps | 8 |
| test_schedule | 24 |
| test_optimize_engagement | 8 |
| **Total** | **92+** |

## Quick Commands
`make help`, `make schedule`, `make test`, `make full-audit`, `make dedup-dry`, `make empties-dry`
