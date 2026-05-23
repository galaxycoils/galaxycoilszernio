---
tags: [wiki, documentation, reference, galaxycoils]
last-updated: 2026-05-22
---

# WIKI

> [!info] Project wiki for GalaxyCoils Zernio.

## Quick Links
- [[GalaxyCoils Zernio]] — Main repo architecture, scripts inventory, and unified dual-posting setup
- [[GalaxyCoils Memory]] — Centralized keys, branch protections, and design decisions
- [[Zernio CLI Learnings]] — CLI quirks, platform-specific observations
- [[Queue State]] — Current scheduled state, dynamic caption weights, queue metrics
- [[Instagram-Automation]] — Automation rules, recovery guides, platform limitations

## Repo & CI
- Public repo: github.com/galaxycoils/galaxycoilszernio
- Branch protection: audit check required, strict:false, enforce admins
- Ruleset: Require CI to pass (ID 16669655)
- Pre-push hook: make full-audit
- GitHub Actions CI: Python 3.12, push/PR to master

## Security
- PEXELS_API_KEY in .env (auto-loaded, gitignored)
- No hardcoded keys

## Scripts Inventory (23 .py files)
| File | Purpose |
|---|---|
| schedule_5_per_day.py | Main scheduler (Instagram & Threads unified dual-posting, dynamic caption weights) |
| schedule_10_per_day.py | Alternate scheduler for high-volume posting (IG + Threads unified dual-posting) |
| fill_schedule_gaps.py | Gap filler |
| purge_zernio_duplicates.py | Duplicate purger |
| scripts/captions_pool.py | Shared caption constants |
| scripts/hashtags_pool.py | Shared hashtag pools for Social SEO |
| scripts/secure_dedup.py | Central deduplication (history.log, API records) |
| scripts/post_utils.py | Zernio interaction utilities |
| scripts/threads_utils.py | Threads caption enrichment and tags management |
| scripts/threads_conversation.py | Companion first reply generation |
| scripts/verify_queue.py | Queue audit |
| scripts/rebuild_viral_queue.py | Queue rebuild tool |
| scripts/update_empty_posts.py | Empty post fixer |
| scripts/unify_scheduled_queue.py | Migration script to unify Instagram and Threads scheduled queues |
| scripts/split_scheduled_queue.py | Migration script to split unified scheduled posts into paired IG + Threads posts |
| scripts/health_monitor.py | Health check and pre-push validations |
| scripts/optimize_engagement.py | Updates caption mix weights based on performance metrics |
| scripts/analyze_engagement.py | Analyzes performance metrics to identify top-performing posts |
| scripts/purge_all_scheduled.py | Queue purge tool |
| scripts/recover_rebuild.py | Queue recovery |
| scripts/recover_virality.py | Virality restoration |
| scripts/batch_recover.py | Batch recovery |
| scripts/chunk_recover.py | Chunk recovery |
| scripts/__init__.py | Package init |

## Test Suites
| Suite | Purpose | Tests |
|---|---|---|
| test_secure_dedup | Deduplication safety | 18 |
| test_post_utils | Zernio CLI wrappers | 17 |
| test_purge_dedup | Duplicate purging logic | 10 |
| test_fill_gaps | Gap filling verification | 8 |
| test_schedule | Scheduling slot assignments & dynamic weights | 24 |
| test_optimize_engagement | Weight calculation and classification logic | 8 |
| Total | | 85 |

## Quick Commands
`make help`, `make schedule`, `make test`, `make full-audit`, `make dedup-dry`, `make empties-dry`