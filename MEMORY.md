# GalaxyCoils & Zernio Persistent Memory

## GalaxyCoils
- Engagement pivot deployed (2026-05-20): 30% CTA / 30% Empty / 22% Micro-hook / 18% Value caption mix.
- CTA pool expanded from 4 to 21 hooks, centralized in `scripts/captions_pool.py`.
- Caption constants centralized in `scripts/captions_pool.py` (single source of truth).

## Zernio CLI Learnings
- `posts:create`: The `--platform instagram` flag requires specific handling (observed quirks, now resolved).
- `posts:get`: API response structure includes a `"post"` root object (accounted for in tooling).
- `posts:create --draft`: Boolean flag (no value needed) to create draft posts without scheduling.

## Git & CI
- **Git repo** initialized on 2026-05-20. **Made public** on 2026-05-20 for branch protection access.
- **`.gitignore`** excludes `__pycache__/`, `*.pyc`, `.DS_Store`, IDE dirs, `backups/`, `logs/`, `.hermes/`, `history.log.bak`, `.env`, and env/virtualenv dirs.
- **`.git/hooks/pre-push`** — Runs `make full-audit` (syntax + verify + 78 tests) before every push. Push aborted if audit fails.
- **`.github/workflows/ci.yml`** — GitHub Actions CI triggered on `push`/`pull_request` to `main` or `master`. Sets up Python 3.12, installs `requests`, and runs `make full-audit`.
- **Branch protection (master)** — `audit` status check required, enforce admins, no force pushes or deletions.
- **Ruleset** — `Require CI to pass` (ID 16669262), active, requires `audit` status check on `refs/heads/master`.

## Queue State (as of 2026-05-20)
- **50 scheduled posts**, 5/day × May 21–30 — fully packed, no gaps.
- **Caption mix** (engagement pivot): ~30% CTA, ~30% empty, ~22% micro-hook, ~18% value.
- **0 duplicates, 0 overlaps**.
- **history.log**: Reset to 24 published-only Pexels IDs (down from 98). No stale entries. Backup deleted after verification.

## Scripts Inventory (17 .py files, all syntax-clean)

### Documentation
- **`WIKI.md`** — Project wiki with architecture diagram, scripts inventory, testing overview, CI/CD pipeline, quick reference.
- **`MEMORY.md`** — Persistent project memory: queue state, dedup architecture, design decisions.

### Root-level schedulers & dedup
- **`schedule_5_per_day.py`** — Canonical 5-posts/day scheduler. Has `--dry-run` (argparse). Uses `secure_dedup.py` for dedup-aware video fetching.
- **`fill_schedule_gaps.py`** — Fills 10-slot window. Has `--dry-run` (argparse). Imports from `schedule_5_per_day.py`.
- **`purge_zernio_duplicates.py`** — Finds & deletes duplicate scheduled posts using `secure_dedup.py`'s `load_history()` as source of truth. Has `--dry-run` (argparse). Processes oldest-first, records through `record_scheduled()` to stay synced. No longer duplicates dedup logic.

### Scripts/ directory
- **`captions_pool.py`** — Shared caption constants: MICRO_HOOKS (10), VALUE_CAPTIONS (7), CTA_CAPTIONS (21 — expanded from 4). Single source of truth for all scheduling/recovery/rebuild scripts.
- **`secure_dedup.py`** — Single canonical dedup module. Provides `load_history()`, `get_all_seen_source_ids()`, `fetch_posts()`, `fetch_published_source_ids()`, `fetch_scheduled_source_ids()`, `extract_id()`, `record_scheduled()`, `record_many()`.
- **`update_empty_posts.py`** — Finds & fixes empty-caption scheduled posts (delete+recreate with CTA captions). Has `--dry-run` (argparse) and `--min-empty N` (threshold before acting, default 0). Uses `post_utils.create_post`.
- **`post_utils.py`** — `create_post(media_url, caption, scheduled_at="", draft=False)`. When `draft=True`, appends `--draft` instead of `--scheduledAt`. Raises `ValueError` if neither provided.
- **`verify_queue.py`** — Full queue health checker: total, per-day, caption mix, duplicates, overlaps.
- **`batch_recover.py`** — Recovers posts by batch. Has `argparse` with required `batch_num` positional + auto `--help`.
- **`chunk_recover.py`** — Recovers posts by chunk range. Has `argparse` with required `start`/`end` positionals, bounds validation + auto `--help`.
- **`recover_rebuild.py`** — Rebuilds from manifest. Has `argparse` with optional `--manifest` flag + auto `--help`.
- **`rebuild_viral_queue.py`** — Viral queue rebuilder (batch-oriented).
- **`test_secure_dedup.py`** — 18 unit tests covering `load_history()`, `extract_id()`, `record_scheduled()`. Isolated via `tempfile` + `mock.patch`. Run with `python3 -m unittest scripts.test_secure_dedup -v`.
- **`test_post_utils.py`** — 15 unit tests covering `create_post()`: draft mode, scheduled mode, ValueError guard, command construction (flags, accounts, tags), success path, 429 rate-limit retry (stdout+stderr), and max-retry exhaustion. Isolated via `mock.patch` on `subprocess.run` and `time.sleep`. Run with `python3 -m unittest scripts.test_post_utils -v`.
- **`test_purge_dedup.py`** — 10 unit tests covering `main()` dedup logic: oldest-first ordering, intra-queue duplicates, history duplicates, unidentifiable posts (no media/no extractable ID), dry-run isolation, and all-unique. Isolated via `mock.patch` on `purge_zernio_duplicates.*` (not `scripts.secure_dedup.*` — targets the importing module due to `from X import Y`). Run with `python3 -m unittest scripts.test_purge_dedup -v`.
- **`test_fill_gaps.py`** — 8 unit tests covering `main()` gap-fill logic: no-slots early exit, dry-run preview (with and without slots), success path (posts created with correct tuples), insufficient URLs raising RuntimeError, and POSTS_TO_SCHEDULE=10 capping. Isolated via `mock.patch` on `fill_schedule_gaps.*` (targets the importing module). Run with `python3 -m unittest scripts.test_fill_gaps -v`.
- **`test_schedule.py`** — 27 unit tests covering 4 core functions from `schedule_5_per_day.py`:
  - `choose_video_url` (9 tests): single file, closest-to-1920 height, tiebreaker on min(h,w), null height, missing links, 4K vs 1080p
  - `generate_caption_plan` (6 tests): empty/null total, known distributions (total=50 → 15/11/9/15 with 30/30/22/18 mix), small totals, large totals (1000), all non-empty from known pools
  - `open_slots` (6 tests): no scheduled → all slots, partially occupied, fully occupied, days_ahead=1, past slots excluded, weekend slots generated
  - `fetch_unique_urls` (6 tests): no Pexels results, all duplicates filtered, some duplicates, empty input, limit control, dedup uses `get_all_seen_source_ids`
  Run with `python3 -m unittest scripts.test_schedule -v`.

### Removed
- **`scripts/remediate_empty_posts.py`** — Removed (superseded by `update_empty_posts.py`).
- **`dedup.py`** — Removed (superseded by `scripts/secure_dedup.py`). No external consumers.

## Dedup Architecture
- **`secure_dedup.py`** is the single source of truth for duplicate detection.
- **`history.log`** stores already-used Pexels IDs (published + scheduled). Reset to published-only after queue rebuild.
- **`schedule_5_per_day.py`** prevents duplicates upstream via `get_all_seen_source_ids(include_scheduled=True)`.
- **`purge_zernio_duplicates.py`** catches any that slip through using `load_history()` only (no live published double-count).
- All three share the same `record_scheduled()` write path — always in sync.

## Quick Reference (Makefile)
- `make help` — show all commands
- `make schedule` / `make schedule-dry` — schedule 5/day or preview
- `make verify` — queue health check
- `make audit` — syntax-check all .py files + verify
- `make test` — run all 78 unit tests
- `make dedup-dry` / `make dedup` — preview/delete duplicates
- `make empties-dry` / `make empties` — preview/fix empty captions (threshold 3)
- `make full-audit` — syntax + verify + all 78 tests
- ~30% of scheduled posts intentionally have empty captions (part of `generate_caption_plan()`'s engagement pivot mix). `update_empty_posts.py --min-empty 3` tolerates this.
- `purge_zernio_duplicates.py` uses `load_history()` not `get_all_seen_source_ids()` to avoid false positives from live published posts post-rebuild.
- All scripts use `argparse` for `--help`/`--dry-run` where applicable.

## Obsidian Vault
- **5 notes** created in "Obsidian Vault" with cross-linked project documentation:
  - [[GalaxyCoils Zernio]] — Project overview with architecture, testing, CI/CD
  - [[GalaxyCoils Memory]] — Persistent memory (synced from MEMORY.md)
  - [[Zernio CLI Learnings]] — Zernio API quirks and patterns
  - [[Queue State]] — Current queue snapshot (50 posts, 0 duplicates)
  - [[WIKI]] — Entry point to project documentation with quick commands
