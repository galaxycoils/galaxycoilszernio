---
tags: [reflection, galaxycoils, threads, zernio]
date: 2026-05-23
---

# 2026-05-23 — Paired posts & Threads crosspost fix

## Investigation
- Queried Zernio API: 37/39 published posts were **Instagram-only**; Threads was not failing on those—it was never scheduled.
- One failed unified post: IG = duplicate content hash; Threads = Meta `OAuthException` code 2 on video (`userId video`).
- One success: unified post `6a10822c` published to both platforms when CDN video + unique caption suffix aligned.

## Fix (merged to branch, not master yet)
- Replaced single `posts:create` with two posts via `create_paired_posts()`.
- `apply_dedup_suffix()` on both platforms.
- `build_threads_caption()` strips IG SEO block before Threads enrichment.

## Still open
- [ ] Run `split_scheduled_queue.py --execute` on 55 unified scheduled posts
- [ ] Merge `fix/zernio-dedup-threads-crosspost`
- [ ] Watch Threads publish for recurring code 2 after migration

## Links
- [[PROJECTS/GalaxyCoils-Zernio/STATE_HANDOFF]]
- [[Zernio CLI Learnings]]
