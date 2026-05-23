---
tags: [galaxycoils, zernio, handoff, dev]
status: active
last-updated: 2026-05-23
branch: fix/zernio-dedup-threads-crosspost
commit: f1eea1e
---

# State Handoff — GalaxyCoils Zernio

> **Start here** when picking up this project. Repo: `galaxycoils/galaxycoilszernio`.

## What changed (2026-05-23)

### Problem we solved
- Instagram looked fine; Threads showed errors because:
  1. **Most published posts were IG-only** (Threads never targeted).
  2. **Unified posts** (one Zernio post, two platforms) failed when IG hit duplicate-content guard or Threads hit Meta `OAuthException` code 2 on **video** publish.
  3. Same IG-style caption (long hashtag block) went to Threads.

### Solution shipped (branch `fix/zernio-dedup-threads-crosspost`)
| Piece | Location |
|-------|----------|
| Paired scheduling | `create_paired_posts()` in `scripts/post_utils.py` |
| Per-platform dedup token | `apply_dedup_suffix()` on **both** IG and Threads |
| Threads captions | `build_threads_caption()` in `scripts/threads_utils.py` |
| Schedulers updated | `schedule_5_per_day.py`, `schedule_10_per_day.py` |
| Queue migration | `scripts/split_scheduled_queue.py` |
| Tests | `scripts/test_threads_utils.py`, expanded `test_post_utils.py` |

**Flow now:** upload media once → schedule **two** Zernio posts (IG + Threads) with different captions and different `#dedup` suffixes.

## Current queue (live Zernio — 2026-05-23)

| Metric | Value |
|--------|-------|
| Scheduled posts | **55** |
| Format | **Still unified** (one post, IG + Threads platforms) |
| Action needed | Run migration script (below) |

Accounts (healthy, `canPost: true`):
- IG: `6a0afc8a5e333c0529912a50` → @galaxycoils
- Threads: `6a0f83d7520992756d97578f` → @galaxycoils

## Next dev — do this first

```bash
cd galaxycoilszernio
export PATH="$PATH:/Users/cmd/.npm-global/bin"   # zernio CLI

# 1. Preview migration (backs up queue to backups/)
python3 scripts/split_scheduled_queue.py

# 2. Pilot 5 posts
python3 scripts/split_scheduled_queue.py --execute --limit 5

# 3. Full migration (55 posts, ~2 min + API time)
python3 scripts/split_scheduled_queue.py --execute

# 4. Verify
python3 scripts/verify_queue.py
make full-audit
```

Then **merge PR** from `fix/zernio-dedup-threads-crosspost` → `master`.

## Commands reference

| Task | Command |
|------|---------|
| Schedule new slots | `python3 schedule_5_per_day.py` |
| Dry-run schedule | `python3 schedule_5_per_day.py --dry-run` |
| Retry failed post | `zernio posts:retry <post_id>` |
| Account health | `zernio accounts:health --pretty` |

## Do not commit
- `stress_test_*.py`, `test_debug.py`, `temp_media/`

## Known issues (unchanged)
- Threads **scheduled text replies** → HTTP 400; `reply_to_post` skipped.
- Meta **transient** video errors on Threads — retry later or `posts:retry`.
- Duplicate slots: some UTC times have **two** unified posts (pre-existing); migration doubles to 4 platform posts at that slot — review after pilot.

## Repo docs (synced)
- `MEMORY.md`, `WIKI.md` in repo root
- Graph: `graphify-out/` after `/graphify` (HTML report + `graph.json`)

## See also
- [[GalaxyCoils Zernio]]
- [[GalaxyCoils Memory]]
- [[Queue State]]
- [[Zernio CLI Learnings]]
- [[WIKI]]
- [[MEMORY/REFLECTIONS/2026-05-23-paired-posts-migration]]
