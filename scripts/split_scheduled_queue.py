"""
Migrate scheduled unified posts (one Zernio post → IG + Threads platforms)
into paired posts (separate IG and Threads schedules, platform-specific captions).

Backs up the queue first. Default is dry-run; pass --execute to apply changes.

Usage:
  python3 scripts/split_scheduled_queue.py
  python3 scripts/split_scheduled_queue.py --execute
  python3 scripts/split_scheduled_queue.py --execute --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.post_utils import (
    IG_ACCOUNT_ID,
    THREADS_ACCOUNT_ID,
    ZERNI0,
    create_paired_posts,
)
from scripts.secure_dedup import fetch_posts
from scripts.threads_utils import build_threads_caption, strip_ig_seo_block

BACKUP_DIR = Path("/Users/cmd/galaxycoilszernio/backups")


def get_account_ids(post: dict) -> list[str]:
    ids = []
    for plat in post.get("platforms") or []:
        acc = plat.get("accountId")
        acc_id = acc.get("_id") if isinstance(acc, dict) else acc
        if acc_id:
            ids.append(acc_id)
    return ids


def media_url_for(post: dict) -> str:
    media_items = post.get("mediaItems") or []
    if not media_items:
        return ""
    return (media_items[0].get("url") or "").strip()


def delete_post(post_id: str) -> bool:
    if not ZERNI0 or not post_id:
        return False
    result = subprocess.run(
        [ZERNI0, "posts:delete", post_id],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ Deleted unified post {post_id}")
        return True
    err = (result.stderr or result.stdout or "")[:200]
    print(f"  ✗ Failed to delete {post_id}: {err}")
    return False


def migrate_post(post: dict, *, execute: bool) -> dict:
    """Return a result dict describing dry-run or live outcome."""
    post_id = post.get("_id") or post.get("id")
    scheduled_at = post.get("scheduledFor") or ""
    content = post.get("content") or ""
    cdn_url = media_url_for(post)

    base = strip_ig_seo_block(content)
    threads_caption = build_threads_caption(base)
    ig_caption = content

    result = {
        "post_id": post_id,
        "scheduled_at": scheduled_at,
        "media": cdn_url[:80] + "..." if len(cdn_url) > 80 else cdn_url,
        "ig_preview": ig_caption[:60] + "..." if len(ig_caption) > 60 else ig_caption,
        "threads_preview": threads_caption[:60] + "..." if len(threads_caption) > 60 else threads_caption,
        "status": "skipped",
        "detail": "",
    }

    if not post_id or not scheduled_at:
        result["detail"] = "missing id or scheduledFor"
        return result
    if not cdn_url:
        result["detail"] = "no media"
        return result

    if not execute:
        result["status"] = "would_migrate"
        return result

    ig_id, threads_id = create_paired_posts(
        None,
        ig_caption,
        threads_caption,
        scheduled_at,
        ig_account=IG_ACCOUNT_ID,
        threads_account=THREADS_ACCOUNT_ID,
        require_threads=False,
        media_url=cdn_url,
    )

    if not ig_id:
        result["status"] = "failed"
        result["detail"] = "paired create failed (Instagram)"
        return result

    if not threads_id:
        result["status"] = "partial"
        result["detail"] = f"IG ok ({ig_id}), Threads failed"
    else:
        result["status"] = "ok"
        result["detail"] = f"IG {ig_id}, Threads {threads_id}"

    if delete_post(post_id):
        return result

    result["status"] = "partial"
    result["detail"] += "; unified post not deleted — remove manually"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split scheduled unified IG+Threads posts into paired posts."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Create paired posts and delete unified entries (default: dry-run).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max unified posts to migrate (0 = all).",
    )
    args = parser.parse_args()

    if not ZERNI0:
        print("ERROR: zernio CLI not found. Set PATH or ZERNIO_PATH.")
        sys.exit(1)

    print("Fetching scheduled posts...")
    posts = fetch_posts("scheduled", limit=300)
    if not posts:
        print("No scheduled posts found.")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"scheduled_queue_backup_{stamp}.json"
    backup_path.write_text(json.dumps(posts, indent=2), encoding="utf-8")
    print(f"Backup saved: {backup_path}")

    unified = []
    ig_only = []
    threads_only = []
    other = []

    for post in posts:
        ids = get_account_ids(post)
        has_ig = IG_ACCOUNT_ID in ids
        has_threads = THREADS_ACCOUNT_ID in ids
        if has_ig and has_threads:
            unified.append(post)
        elif has_ig:
            ig_only.append(post)
        elif has_threads:
            threads_only.append(post)
        else:
            other.append(post)

    print("\nQueue analysis:")
    print(f"  Total scheduled:     {len(posts)}")
    print(f"  Unified (split):     {len(unified)}")
    print(f"  Instagram-only:      {len(ig_only)}  (unchanged)")
    print(f"  Threads-only:        {len(threads_only)}  (unchanged)")
    print(f"  Other:               {len(other)}")

    targets = sorted(unified, key=lambda p: p.get("scheduledFor", ""))
    if args.limit > 0:
        targets = targets[: args.limit]

    if not targets:
        print("\nNo unified posts to migrate.")
        return

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"\n[{mode}] Processing {len(targets)} unified post(s)...\n")

    counts = {"would_migrate": 0, "ok": 0, "partial": 0, "failed": 0, "skipped": 0}

    for idx, post in enumerate(targets, 1):
        post_id = post.get("_id") or post.get("id")
        print(f"[{idx}/{len(targets)}] {post.get('scheduledFor')}  {post_id}")
        outcome = migrate_post(post, execute=args.execute)
        counts[outcome["status"]] = counts.get(outcome["status"], 0) + 1
        print(f"  → {outcome['status']}: {outcome['detail'] or outcome['threads_preview']}")
        if args.execute and outcome["status"] in ("ok", "partial"):
            time.sleep(2)

    print("\nSummary:")
    for key, val in sorted(counts.items()):
        if val:
            print(f"  {key}: {val}")

    if not args.execute:
        print("\nDry run only. Re-run with: python3 scripts/split_scheduled_queue.py --execute")


if __name__ == "__main__":
    main()
