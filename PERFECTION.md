# PERFECTION — Daily Review Tracker

> Goal state: clean, fast, bulletproof, highly effective. Never "good enough".
> Each daily review must measurably advance the phases below.

## The 4 Phases

### Phase 1 — Correctness & Quality Gate
> 95%+ meaningful coverage · zero lint/type errors · audit that actually fails on problems

- [x] 99% line / 99% total coverage on all operational modules (179 tests, 9 suites)
- [x] Zero ruff errors (E,F,W,I,UP,B,SIM,C90 rulesets)
- [x] Zero mypy errors across all 20 source files
- [x] `verify_queue.py` exits 1 on duplicates/overlap — the audit gate is real (was: always exit 0)
- [x] Self-maintaining audit/test discovery (no hardcoded file lists to go stale)
- [ ] Legacy one-off recovery scripts (batch/chunk/recover/rebuild) tested or formally archived
- [ ] Branch coverage 100% (2 partial branches remain)

### Phase 2 — Observability & Data
> Structured logging + monitoring · accurate engagement analytics

- [x] Single canonical caption classifier (`captions_pool.classify_caption`) — reporting can no longer drift from the caption pools
- [x] `analyze_engagement.py` v2: micro-hook category (was invisible), median ER, small-sample reliability flags, machine-readable JSON report
- [x] `verify_queue.py` reports caption_mix_pct vs target mix
- [ ] Structured (JSON) logging across all scripts — currently bare `print()`
- [ ] Analytics run on a schedule with trend history (weekly snapshot committed or stored)
- [ ] Alerting when queue health degrades (duplicates, gaps, ER drop)

### Phase 3 — Automation & Reliability
> Zero manual intervention for daily operation · sub-second critical ops · robust async where beneficial

- [x] Pexels API retry/backoff (a single 429/timeout no longer kills a scheduling run)
- [x] Double-booking guard: slot occupancy compares parsed datetimes, not raw strings
- [x] Fail-fast when `PEXELS_API_KEY` is missing (clear error instead of 401s)
- [x] `update_empty_posts.py` is mix-protected — cannot wipe out the intentional ~30% empty captions
- [x] Daily GitHub Actions workflow scaffold (`daily.yml`, gated by `ENABLE_AUTOSCHEDULE` var)
- [ ] Zernio CLI non-interactive auth working in Actions → flip `ENABLE_AUTOSCHEDULE=true`
- [ ] Self-healing: auto `fill-gaps` + `dedup` + `verify` in the daily run
- [ ] history.log state committed back by automation (currently diverges between laptop and repo)
- [ ] Parallel Pexels fetching (8 queries are sequential; ~8× speedup available)

### Phase 4 — Production Deployment
> Docker · secrets management · backups · data-driven caption optimization

- [ ] Dockerfile + compose (Python 3.12 + Node for zernio)
- [ ] Secrets in a real store (currently `.env` on one laptop + Actions secret)
- [ ] Automated backups of queue state/history
- [ ] Closed loop: analytics JSON → caption mix adjustment in `generate_caption_plan()`

---

## Review Log

### 2026-08-04 — Review #1 (79 days after last commit)

**State found:** queue dry since 2026-05-30 (50 posts ran out, nothing refilled);
dedup silently broken off-laptop (hardcoded `/Users/cmd/...` path); audit gate
toothless (verify always exit 0); analytics blind to micro-hooks; maintenance
tool (`empties`) able to destroy the intentional caption mix; docs stale
(53%-empty claim, file/test counts); local-only symlink + 122KB artifact committed;
new `analyze_engagement.py` untested, unlinted, missing from audit.

**Shipped (this review):**
1. `secure_dedup.py` — repo-relative `BASE_DIR` (dedup now works anywhere)
2. `captions_pool.py` — shared `classify_caption()` (pool-membership first)
3. `verify_queue.py` — real health gate + mix % vs target + `--no-fail`
4. `analyze_engagement.py` — full rewrite: micro-hook category, medians, reliability flags, MD+JSON reports, exit codes
5. `update_empty_posts.py` — ratio-aware guard (`select_posts_to_fix`)
6. `schedule_5_per_day.py` — ISO-tolerant slot matching, Pexels retry/backoff, API-key fail-fast
7. Tests: 78 → **179** (+101), coverage ~56% effective → **99%** (gate at 95%)
8. Quality gate: ruff (0 errors), mypy (0 errors), wired into `make full-audit` + CI
9. `requirements.txt` / `requirements-dev.txt` / `.env.example` / `pyproject.toml`
10. `daily.yml` workflow scaffold (zero-touch scheduling, off by default)
11. Repo hygiene: `.gitignore` hardened, docs re-synced (WIKI/MEMORY)

**Next highest-leverage targets (in order):**
1. Enable `ENABLE_AUTOSCHEDULE` after verifying zernio auth in Actions → queue never runs dry again (Phase 3)
2. Structured logging module + adopt in scheduler/verify/analytics (Phase 2)
3. Parallel Pexels fetching (Phase 3 perf)
4. Dockerfile (Phase 4)
5. Analytics → caption-mix feedback loop (Phase 4)
