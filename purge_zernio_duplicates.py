"""Find and delete duplicate scheduled posts using the shared dedup system.

Uses scripts/secure_dedup.py's load_history() as the source of truth for
already-seen Pexels IDs. Scheduled posts are checked oldest-first: the first
occurrence of each Pexels ID is kept, subsequent duplicates are deleted.

Usage:
  python3 purge_zernio_duplicates.py              # Delete duplicate scheduled posts
  python3 purge_zernio_duplicates.py --dry-run    # Preview duplicates without deleting
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure project root is on sys.path so `from scripts.secure_dedup import ...` works
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.secure_dedup import (
    extract_id,
    fetch_posts,
    load_history,
    record_scheduled,
)

ZERNI0 = shutil.which("zernio") or os.environ.get("ZERNIO_PATH", "")


def main():
    parser = argparse.ArgumentParser(
        description="Find and delete duplicate scheduled posts using the shared dedup system."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview duplicates without deleting or writing history."
    )
    args = parser.parse_args()

    # Build the "seen" set from history.log (already-published Pexels IDs).
    # We do NOT include live published posts — history.log IS the canonical
    # record of what's been published. This avoids false positives when the
    # scheduled queue was rebuilt from previously-published content.
    print("Loading history...")
    seen = load_history()
    print(f"  {len(seen)} source IDs in history.log.\n")

    # Fetch scheduled posts, oldest first so the first occurrence is kept
    print("Fetching scheduled posts...")
    scheduled = fetch_posts("scheduled")
    scheduled.sort(key=lambda p: p.get("createdAt", ""))
    print(f"  {len(scheduled)} scheduled posts found.\n")

    to_delete = []
    new_ids = []

    for post in scheduled:
        post_id = post["_id"]
        media_items = post.get("mediaItems") or []
        if not media_items:
            continue

        url = media_items[0].get("url", "")
        pexels_id = extract_id(url)
        if not pexels_id:
            continue

        if pexels_id in seen:
            print(f"  DUPLICATE  {post_id}  @ {post.get('scheduledFor')}  (Pexels {pexels_id})")
            to_delete.append(post_id)
        else:
            print(f"  UNIQUE     {post_id}  @ {post.get('scheduledFor')}  (Pexels {pexels_id})")
            seen.add(pexels_id)
            new_ids.append(pexels_id)
            if not args.dry_run:
                record_scheduled(pexels_id)

    print()
    if not to_delete:
        print("No duplicate scheduled posts found.")
    elif args.dry_run:
        print(f"[DRY RUN] Would delete {len(to_delete)} duplicate posts:")
        for post_id in to_delete:
            print(f"  {post_id}")
        print(f"[DRY RUN] Would record {len(new_ids)} new source IDs to history.")
        print("[DRY RUN] No posts deleted, no history written.")
    else:
        for post_id in to_delete:
            print(f"Deleting {post_id}...")
            subprocess.run([ZERNI0, "posts:delete", post_id], capture_output=True, text=True)
        print(f"Deleted {len(to_delete)} duplicates.")


if __name__ == "__main__":
    main()
