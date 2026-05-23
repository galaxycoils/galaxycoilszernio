---
tags: [memory, galaxycoils, zernio, pipeline]
last-updated: 2026-05-23
---

# GalaxyCoils Memory

Persistent project memory for the GalaxyCoils/Zernio pipeline.

## Git & CI
- **Repo:** github.com/galaxycoils/galaxycoilszernio (public)
- **Active branch:** `fix/zernio-dedup-threads-crosspost` (commit `f1eea1e` pushed 2026-05-23)
- **Pre-push hook:** `make full-audit` (syntax + verify + unit tests)
- **Branch protection (master):** audit status check required, strict:false, enforce admins
- **GitHub Actions CI:** Python 3.12, pip install requests, push/PR to master
- **Ruleset:** Require CI to pass (ID 16669655)

## Security
- PEXELS_API_KEY in `.env` (auto-loaded via python-dotenv, gitignored)
- No hardcoded keys in source files

## Queue State (as of 2026-05-23)
- **55 scheduled posts** — still **unified** (one Zernio post, IG + Threads platforms each); **not yet migrated** to paired posts
- **0 duplicates, 0 overlaps** in scheduled queue
- **Published history:** most live posts were IG-only; only one successful unified IG+Threads publish; one failed unified post (IG duplicate + Threads OAuth video error)
- **Caption mix:** dynamic weights in `logs/engagement_weights.json`

## Posting Architecture (2026-05-23 — paired posts)
- **Schedulers** (`schedule_5_per_day.py`, `schedule_10_per_day.py`) now call `create_paired_posts()`:
  - One media upload to Zernio CDN (`ensure_zernio_media_url`)
  - **Instagram:** full caption + SEO tags + IG `--tags` / `--hashtags`
  - **Threads:** `build_threads_caption()` (strip IG hashtag block, enrich, 500-char cap)
  - **Dedup:** `apply_dedup_suffix()` appends ` #<6 hex>` on **both** platforms (different token per post)
- **Migration:** `scripts/split_scheduled_queue.py` — dry-run by default; `--execute` splits existing unified queue into paired posts (backs up to `backups/` first)

## Account IDs
- Instagram: `6a0afc8a5e333c0529912a50` (`galaxycoils`)
- Threads: `6a0f83d7520992756d97578f` (`galaxycoils`)

## Zernio PATH Hardening
- All scripts use `shutil.which('zernio')` or `/Users/cmd/.npm-global/bin/zernio`
- `secure_dedup.py`: `fetch_posts()` returns `[]` when Zernio unavailable (CI-compatible)

## Dedup Architecture
- Central: `scripts/secure_dedup.py`
- Ledger: `history.log` (Pexels source IDs)
- Three-layer gate: history.log → published → scheduled
- Zernio also blocks duplicate **content hash** on re-post (mitigated by per-post suffix)

## Known Limitations
- Threads scheduled **text replies** (`inbox:reply`) → 400; first-reply automation skipped
- Threads video publish can fail with Meta `OAuthException` code 2 (`is_transient`) even when IG succeeds
- `enrich_for_threads` adds opener/closer — can feel repetitive; tune in `scripts/threads_utils.py`

## Tests
- **92+ unit tests** (includes `scripts/test_threads_utils.py`, expanded `test_post_utils.py`)
- Run: `make test` or `make full-audit`

## Next Dev Actions
1. **Migrate queue:** `python3 scripts/split_scheduled_queue.py` then `python3 scripts/split_scheduled_queue.py --execute` (optionally `--limit 5` first)
2. **Merge** `fix/zernio-dedup-threads-crosspost` → `master`
3. **Monitor** publish failures in Zernio UI; retry with `zernio posts:retry <id>` for transient Threads errors
4. Do **not** commit `stress_test_*.py`, `test_debug.py`, `temp_media/`

## See Also
- [[GalaxyCoils Zernio]]
- [[Zernio CLI Learnings]]
- [[Queue State]]
- [[WIKI]]
- [[Instagram-Automation]]
- [[PROJECTS/GalaxyCoils-Zernio/STATE_HANDOFF]]
