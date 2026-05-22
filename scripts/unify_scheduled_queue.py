"""
Script to migrate existing separate Instagram and Threads scheduled posts
into unified cross-posted Zernio posts.

Safely backups the queue first, purges independent Threads posts,
and recreates Instagram posts as unified IG+Threads posts.
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from scripts.secure_dedup import fetch_posts, ZERNI0
from scripts.post_utils import create_single_post, reply_to_post
from scripts.threads_conversation import generate_first_reply

IG_ACCOUNT = "6a0afc8a5e333c0529912a50"
THREADS_ACCOUNT = "6a0f83d7520992756d97578f"

def get_account_ids(post: dict) -> list[str]:
    platform_list = post.get("platforms") or []
    ids = []
    for plat in platform_list:
        acc = plat.get("accountId")
        acc_id = acc.get("_id") if isinstance(acc, dict) else acc
        if acc_id:
            ids.append(acc_id)
    return ids

def delete_post(post_id: str) -> bool:
    if not ZERNI0 or not post_id:
        return False
    cmd = [ZERNI0, "posts:delete", post_id]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Deleted post: {post_id}")
        return True
    print(f"  ✗ Failed to delete post {post_id}: {result.stderr[:200]}")
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Unify separate Instagram and Threads scheduled posts."
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Perform the actual deletion and migration."
    )
    args = parser.parse_args()

    print("Fetching all scheduled posts from Zernio...")
    posts = fetch_posts("scheduled", limit=300)
    if not posts:
        print("No scheduled posts found or Zernio error.")
        return

    # 1. Create a backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("/Users/cmd/galaxycoilszernio/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"scheduled_queue_backup_{timestamp}.json"
    
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
    print(f"Backup saved successfully to: {backup_path}")

    # 2. Categorize posts
    threads_only = []
    ig_only = []
    unified = []

    for p in posts:
        ids = get_account_ids(p)
        has_ig = IG_ACCOUNT in ids
        has_threads = THREADS_ACCOUNT in ids
        
        if has_ig and has_threads:
            unified.append(p)
        elif has_ig:
            ig_only.append(p)
        elif has_threads:
            threads_only.append(p)

    print(f"\nQueue Analysis:")
    print(f"  Total scheduled posts: {len(posts)}")
    print(f"  Threads-only posts (to be deleted): {len(threads_only)}")
    print(f"  Instagram-only posts (to be unified): {len(ig_only)}")
    print(f"  Already unified posts (to keep): {len(unified)}")

    if not args.execute:
        print("\n[DRY RUN] Details of planned actions:")
        print(f"\n[DRY RUN] Would delete {len(threads_only)} Threads-only posts.")
        if threads_only:
            print("Sample Threads-only posts to delete:")
            for t in threads_only[:3]:
                print(f"  - ID: {t.get('_id')} | Scheduled: {t.get('scheduledFor')} | Content: '{t.get('content', '')[:50]}...'")

        print(f"\n[DRY RUN] Would delete and recreate {len(ig_only)} Instagram-only posts as unified (IG+Threads).")
        if ig_only:
            print("Sample Instagram-only posts to migrate:")
            for i in ig_only[:3]:
                print(f"  - ID: {i.get('_id')} | Scheduled: {i.get('scheduledFor')} | Content: '{i.get('content', '')[:50]}...'")

        print("\n[DRY RUN] To perform these actions, run with: python3 scripts/unify_scheduled_queue.py --execute")
        return

    # 3. Execute Migration
    print("\nStarting execution...")

    # A. Delete Threads-only posts
    print(f"\n--- Deleting {len(threads_only)} Threads-only posts ---")
    for idx, t in enumerate(threads_only, 1):
        post_id = t.get("_id") or t.get("id")
        if post_id:
            print(f"[{idx}/{len(threads_only)}] Deleting Threads post {post_id} (scheduled for {t.get('scheduledFor')})...")
            delete_post(post_id)
            time.sleep(1)

    # B. Migrate Instagram-only posts
    print(f"\n--- Migrating {len(ig_only)} Instagram-only posts to Unified ---")
    for idx, i in enumerate(ig_only, 1):
        post_id = i.get("_id") or i.get("id")
        scheduled_at = i.get("scheduledFor")
        content = i.get("content", "")
        
        media_items = i.get("mediaItems") or []
        url = media_items[0].get("url", "") if media_items else ""
        
        if not post_id or not url:
            print(f"[{idx}/{len(ig_only)}] SKIPPING invalid post: {post_id}")
            continue

        print(f"[{idx}/{len(ig_only)}] Migrating post {post_id} (scheduled for {scheduled_at})...")
        
        # Delete old post
        if delete_post(post_id):
            # Recreate as unified
            print(f"  Re-creating unified post for {scheduled_at}...")
            new_id = create_single_post(
                url=url,
                caption=content,
                scheduled_at=scheduled_at,
                accounts=[IG_ACCOUNT, THREADS_ACCOUNT],
                max_retries=3
            )
            
            if not new_id:
                print(f"  ✗ Failed to recreate post for {scheduled_at}")
        
        time.sleep(1)  # Safety backoff to avoid rate limits

    print("\nMigration finished successfully!")

if __name__ == "__main__":
    main()
