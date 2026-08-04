# GalaxyCoils & Zernio Persistent Memory

## GalaxyCoils
- Engagement pivot deployed (2026-05-20): 30% CTA / 30% Empty / 22% Micro-hook / 18% Value caption mix.
- CTA pool expanded from 4 to 21 hooks, centralized in `scripts/captions_pool.py`.
- Caption constants centralized in `scripts/captions_pool.py` (single source of truth).
- **Perfection Review #1 (2026-08-04)** — quality gate rebuilt: 179 tests (99% coverage), ruff+mypy zero-error, real health gate. See `PERFECTION.md` for the 4-phase tracker.

## Zernio CLI Learnings
- `posts:create`: The `--platform instagram` flag requires specific handling (observed quirks, now resolved).
- `posts:get`: API response structure includes a `"post"` root object (accounted for in tooling).
- `posts:create --draft`: Boolean flag (no value needed) to create draft posts without scheduling.

## Git & CI
- **Git repo** initialized on 2026-05-20. **Made public** on 2026-05-20 for branch protection access.
- **`.gitignore`** excludes `__pycache__/`, `*.pyc`, `.DS_Store`, IDE dirs, `backups/`, `logs/`, `.hermes/`, `history.log.bak`, `.env`, env/virtualenv dirs, local-tool state (`.antigravitycli/`), generated artifacts (`queue_audit.json`), and test/lint caches.
- **`.git/hooks/pre-push`** — Runs `make full-audit` before every push. Push aborted if audit fails.
- **`.github/workflows/ci.yml`** — GitHub Actions CI triggered on `push`/`pull_request` to `main` or `master`. Sets up Python 3.12, installs `requirements-dev.txt`, and runs `make full-audit` (syntax + verify + ruff + mypy + 179 tests + coverage ≥95%).
- **`.github/workflows/daily.yml`** — Daily 09:30 UTC queue top-up. Gated by repo var `ENABLE_AUTOSCHEDULE` (off = dry-run). Requires `PEXELS_API_KEY` secret + non-interactive zernio auth.
- **Branch protection (master)** — `audit` status check required, enforce admins, no force pushes or deletions.
- **Ruleset** — `Require CI to pass` (ID 16669262), active, requires `audit` status check on `refs/heads/master`.

## Queue State (as of 2026-08-04)
- **⚠️ QUEUE DRY since 2026-05-30** — the May 21–30 batch (50 posts) fully published; nothing refilled it for 79 days. Fix = enable `daily.yml` automation (Phase 3 in PERFECTION.md), then run `make schedule` to refill.
- **Caption mix** (engagement pivot): ~30% CTA, ~30% empty, ~22% micro-hook, ~18% value.
- **history.log**: 78 published Pexels IDs (grew from 24 after the May rebuild published). Repo-relative path since 2026-08-04 — works on any machine.

## Scripts Inventory (22 .py files, all syntax-clean, ruff-clean, mypy-clean)

### Documentation
- **`WIKI.md`** — Project wiki with architecture diagram, scripts inventory, testing overview, CI/CD pipeline, quick reference.
- **`MEMORY.md`** — Persistent project memory: queue state, dedup architecture, design decisions.
- **`PERFECTION.md`** — Daily perfection-review tracker: 4 phases, status, review log, next targets.

### Root-level schedulers & dedup
- **`schedule_5_per_day.py`** — Canonical 5-posts/day scheduler. `--dry-run`. Pexels retry/backoff, API-key fail-fast, ISO-tolerant slot matching (no double-booking).
- **`fill_schedule_gaps.py`** — Fills 10-slot window. `--dry-run`. Imports from `schedule_5_per_day.py`.
- **`purge_zernio_duplicates.py`** — Finds & deletes duplicate scheduled posts. `--dry-run`.

### Scripts/ directory
- **`captions_pool.py`** — Shared caption constants (MICRO_HOOKS 10, VALUE_CAPTIONS 7, CTA_CAPTIONS 21) **plus `classify_caption()`** — the single canonical classifier for verify + analytics.
- **`secure_dedup.py`** — Single canonical dedup module. **Repo-relative `BASE_DIR`** (portable; was hardcoded `/Users/cmd/...`).
- **`analyze_engagement.py`** — ER/views per caption category → `logs/engagement-report.md` + `.json`. Median ER, small-sample reliability flags, exit codes.
- **`update_empty_posts.py`** — Fixes *excess* empty captions. Mix-protected via `--max-empty-ratio`/`--target-ratio` (defaults 0.35/0.30): can no longer wipe out the intentional ~30% empties.
- **`post_utils.py`** — `create_post()` with 429 backoff, draft/scheduled modes.
- **`verify_queue.py`** — Queue health checker. **Exits 1 on duplicates/overlap** (real audit gate), reports mix % vs target.
- **`batch_recover.py` / `chunk_recover.py` / `recover_rebuild.py` / `rebuild_viral_queue.py`** — One-off May-2026 recovery scripts, kept for reference (excluded from coverage gate).
- **9 test suites, 179 tests, 99% coverage** — `test_secure_dedup` (30), `test_post_utils` (15), `test_purge_dedup` (10), `test_fill_gaps` (8), `test_schedule` (49), `test_verify_queue` (9), `test_captions_pool` (13), `test_analyze_engagement` (14), `test_update_empty` (31). Auto-discovered: `python3 -m unittest discover -s scripts -t . -p "test_*.py"`.

### Config
- **`pyproject.toml`** — ruff, mypy, coverage (95% gate) configuration.
- **`requirements.txt` / `requirements-dev.txt`** — runtime vs dev/CI deps.
- **`.env.example`** — template for `PEXELS_API_KEY` / `ZERNIO_PATH`.

### Removed
- **`scripts/remediate_empty_posts.py`** — Removed (superseded by `update_empty_posts.py`).
- **`dedup.py`** — Removed (superseded by `scripts/secure_dedup.py`). No external consumers.
- **`.antigravitycli/` symlink, `queue_audit.json`** — Removed from tracking 2026-08-04 (local-only state / generated artifact).

## Dedup Architecture
- **`secure_dedup.py`** is the single source of truth for duplicate detection.
- **`history.log`** stores already-used Pexels IDs (published + scheduled). Reset to published-only after queue rebuild.
- **`schedule_5_per_day.py`** prevents duplicates upstream via `get_all_seen_source_ids(include_scheduled=True)`.
- **`purge_zernio_duplicates.py`** catches any that slip through using `load_history()` only (no live published double-count).
- All three share the same `record_scheduled()` write path — always in sync.

## Quick Reference (Makefile)
- `make help` — show all commands
- `make schedule` / `make schedule-dry` — schedule 5/day or preview
- `make verify` — queue health check (exits 1 on duplicates/overlap)
- `make audit` — syntax-check ALL .py files (auto-discovered) + verify
- `make test` — run all 179 unit tests (auto-discovered)
- `make coverage` — tests + coverage report (95% gate)
- `make lint` / `make typecheck` — ruff / mypy (zero-error gates)
- `make dedup-dry` / `make dedup` — preview/delete duplicates
- `make empties-dry` / `make empties` — preview/fix EXCESS empty captions (mix-protected)
- `make analytics` — engagement report by caption category (MD + JSON)
- `make full-audit` — audit + lint + typecheck + coverage (pre-push + CI gate)
- ~30% of scheduled posts intentionally have empty captions (engagement pivot). `update_empty_posts.py` now only fixes empties beyond 35% of the queue, back down to 30% — the intentional mix is protected by default.
- `purge_zernio_duplicates.py` uses `load_history()` not `get_all_seen_source_ids()` to avoid false positives from live published posts post-rebuild.
- All scripts use `argparse` for `--help`/`--dry-run` where applicable.

## Obsidian Vault
- **5 notes** created in "Obsidian Vault" with cross-linked project documentation:
  - [[GalaxyCoils Zernio]] — Project overview with architecture, testing, CI/CD
  - [[GalaxyCoils Memory]] — Persistent memory (synced from MEMORY.md)
  - [[Zernio CLI Learnings]] — Zernio API quirks and patterns
  - [[Queue State]] — Current queue snapshot (50 posts, 0 duplicates)
  - [[WIKI]] — Entry point to project documentation with quick commands
