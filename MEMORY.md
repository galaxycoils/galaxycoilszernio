---
tags: [memory, galaxycoils, zernio, pipeline]
last-updated: 2026-05-22
---

# GalaxyCoils Memory

Persistent project memory for the GalaxyCoils/Zernio pipeline.

## Git & CI
- **Repo:** github.com/galaxycoils/galaxycoilszernio (public)
- **Pre-push hook:** make full-audit (syntax checks + 85 unit tests)
- **Branch protection (master):** audit status check required, strict:false, enforce admins
- **GitHub Actions CI:** Python 3.12, pip install requests, push/PR to master
- **Ruleset:** Require CI to pass (ID 16669655)

## Security
- PEXELS_API_KEY in .env (auto-loaded via python-dotenv, gitignored)
- No hardcoded keys in source files

## Queue State (as of 2026-05-22)
- **50 unified posts** scheduled (publishing to both Instagram and Threads simultaneously), 5 posts/day total through May 29
- **0 duplicates, 0 overlaps**
- **Caption mix (Engagement Optimization V3):** Determined dynamically via feedback loop weights in logs/engagement_weights.json.
- **85/85 unit tests passing**, 23 .py files (including test modules)

## Caption Centralization & Optimization (2026-05-22)
- **V3 Upgrade:** MICRO_HOOKS refactored into direct questions to force comment velocity. VALUE_CAPTIONS refactored to include steps directly in the caption.
- Single source of truth in scripts/captions_pool.py.
- Dynamic weighting updates based on post engagement analysis.

## Zernio PATH Hardening
- All scripts use shutil.which('zernio') or a globally configured CLI path variable.
- secure_dedup.py: fetch_posts() returns [] when Zernio unavailable (CI-compatible)
- post_utils.py: create_post() returns False when Zernio unavailable
- Test mocks updated to patch ZERNI0 in all test suites

## Dedup Architecture
- Central dedup module: scripts/secure_dedup.py
- State ledger: history.log tracks seen Pexels source IDs
- Three-layer gate: history.log -> published posts -> scheduled queue
- Duplicate validation checks for both Instagram and Threads.

## Design Decisions
- Dynamic weighting based on Engagement Rate (ER) feedback loop.
- argparse interface for all scripts.
- Bankers rounding for caption distribution.
- Companion first reply automation on Threads to foster user discussion.
- Unified Cross-Posting: Instead of scheduling separate posts for Instagram and Threads, a single `zernio posts:create` call is used with comma-separated accounts. Threads companion replies are scheduled under this single post ID.

## See Also
- [[GalaxyCoils Zernio]]
- [[Zernio CLI Learnings]]
- [[Queue State]]
- [[WIKI]]
- [[Instagram-Automation]]