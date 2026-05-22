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
from collections import defaultdict
from typing import List

# Ensure project root is on sys.path so `from scripts.secure_dedup import ...` works
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.secure_dedup import (
    extract_id,
    fetch_posts,
    load_history,
    record_scheduled,
)

ZERNI0 = shutil.which("zernio") or os.environ.get("ZERNIO_PATH", "")


def get_post_account_ids(post: dict) -> List[str]:
    account_ids = []
    for p in post.get("platforms") or []:
        acc = p.get("accountId")
        if isinstance(acc, dict):
            acc_id = acc.get("_id") or acc.get("id")
        else:
            acc_id = acc
        if acc_id:
            account_ids.append(acc_id)
    return account_ids


def main():
    parser = argparse.ArgumentParser(
        description="Find and delete duplicate scheduled posts using the shared dedup system."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview duplicates without deleting or writing history."
    )
    args = parser.parse_args()

    # Load history.log (all previously scheduled/published Pexels IDs).
    print("Loading history...")
    history_ids = load_history()
    print(f"  {len(history_ids)} source IDs in history.log.\n")

    # Fetch scheduled posts, oldest first so the first occurrence is kept
    print("Fetching scheduled posts...")
    scheduled = fetch_posts("scheduled")
    scheduled.sort(key=lambda p: p.get("createdAt", ""))
    print(f"  {len(scheduled)} scheduled posts found.\n")

    # Extract all Pexels IDs currently in the scheduled queue
    scheduled_pexels_ids = set()
    for post in scheduled:
        media_items = post.get("mediaItems") or []
        if not media_items:
            continue
        url = media_items[0].get("url", "")
        pexels_id = extract_id(url)
        if pexels_id:
            scheduled_pexels_ids.add(pexels_id)

    # To avoid deleting freshly scheduled posts (since they were written to history.log
    # during scheduling), we compute the set of IDs that are in history.log but NOT
    # currently scheduled. These represent truly published/past videos.
    # To preserve historical duplicate deletion capability in tests and real scenarios,
    # we only protect scheduled posts that were created recently (in the last 24 hours).
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    freshly_scheduled_pexels_ids = set()
    for post in scheduled:
        created_at_str = post.get("createdAt")
        if not created_at_str:
            continue
        try:
            clean = created_at_str.strip()
            if clean.endswith("Z"):
                clean = clean[:-1] + "+00:00"
            created_at = datetime.fromisoformat(clean)
            # Protect if created between 1 hour in the future and 24 hours in the past
            if -3600 < (now - created_at).total_seconds() < 24 * 3600:
                media_items = post.get("mediaItems") or []
                if media_items:
                    url = media_items[0].get("url", "")
                    pexels_id = extract_id(url)
                    if pexels_id:
                        freshly_scheduled_pexels_ids.add(pexels_id)
        except Exception:
            pass

    published_history = history_ids - freshly_scheduled_pexels_ids
    print(f"  {len(published_history)} published IDs identified from history.\n")

    # Initialize per-account seen sets with the published history
    seen_by_account = defaultdict(lambda: set(published_history))

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

        account_ids = get_post_account_ids(post)
        if not account_ids:
            account_ids = ["unknown"]

        # Check if duplicate on ANY of the account IDs associated with this post
        is_duplicate = False
        for acc_id in account_ids:
            if pexels_id in seen_by_account[acc_id]:
                is_duplicate = True
                break

        if is_duplicate:
            print(f"  DUPLICATE  {post_id}  @ {post.get('scheduledFor')}  (Pexels {pexels_id}) for accounts {account_ids}")
            to_delete.append(post_id)
        else:
            print(f"  UNIQUE     {post_id}  @ {post.get('scheduledFor')}  (Pexels {pexels_id}) for accounts {account_ids}")
            for acc_id in account_ids:
                seen_by_account[acc_id].add(pexels_id)
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
