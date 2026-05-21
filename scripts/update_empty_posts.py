"""
Fix empty-caption scheduled posts by deleting and recreating them with
fresh CTA captions + viral tags/hashtags + timezone.

Strategy: posts:get → extract media/schedule/accounts → posts:delete → posts:create
(zernio CLI has no posts:update command)

Usage:
  python3 scripts/update_empty_posts.py                    # fix empty posts
  python3 scripts/update_empty_posts.py --dry-run           # preview only
  python3 scripts/update_empty_posts.py --min-empty 3       # only fix if >3 empties
  python3 scripts/update_empty_posts.py --dry-run --min-empty 3
"""

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so `from scripts.post_utils import ...` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.captions_pool import CTA_CAPTIONS
from scripts.post_utils import ZERNI0, create_post as _create_post


def _run_json(cmd):
    """Run a zernio CLI command and return parsed JSON, or None on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  CLI error: {result.stderr.strip() or result.stdout.strip()}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  JSON parse error. Raw: {result.stdout[:200]}")
        return None


def _run_ok(cmd):
    """Run a command, return True on success."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def get_post_details(post_id):
    """Fetch post JSON and extract media URL, scheduled time, and account IDs."""
    data = _run_json([ZERNI0, "posts:get", post_id, "--pretty"])
    if not data:
        return None
    post = data if "_id" in data else data.get("post", {})
    media_items = post.get("mediaItems") or []
    media_url = media_items[0].get("url", "") if media_items else ""
    scheduled_for = post.get("scheduledFor", "")
    account_ids = post.get("accountIds", [])
    return {
        "media_url": media_url,
        "scheduled_for": scheduled_for,
        "account_ids": account_ids,
    }


def fix_post(post_id):
    """Delete and recreate a post with a fresh caption."""
    print(f"Processing {post_id}...")

    # 1. Get current post details
    details = get_post_details(post_id)
    if not details:
        print(f"  SKIP: could not fetch post details")
        return False
    if not details["media_url"]:
        print(f"  SKIP: no media URL found")
        return False
    if not details["scheduled_for"]:
        print(f"  SKIP: no scheduled time (already published?)")
        return False

    # 2. Delete the old post
    print(f"  Deleting old post...")
    if not _run_ok([ZERNI0, "posts:delete", post_id]):
        print(f"  SKIP: failed to delete")
        return False
    time.sleep(1)  # brief gap to avoid rate limiting

    # 3. Recreate with fresh caption + tags/hashtags/timezone
    caption = random.choice(CTA_CAPTIONS)
    accounts = ",".join(details["account_ids"]) if details["account_ids"] else None
    print(f"  Creating new post with caption: {caption[:50]}...")
    ok = _create_post(
        details["media_url"],
        caption,
        details["scheduled_for"],
        accounts=accounts,
    )
    if ok:
        print(f"  OK: recreated successfully")
    else:
        print(f"  FAIL: could not recreate post")
    return ok


def find_empty_posts():
    """Fetch all scheduled posts and return IDs of those with empty captions."""
    data = _run_json([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "100", "--pretty"])
    if not data:
        print("Failed to fetch scheduled posts.")
        return []
    posts = data.get("posts", [])
    return [p["_id"] for p in posts if not (p.get("content") or "").strip()]


def dry_run(empty_post_ids):
    """Preview what would be fixed without making any changes."""
    print(f"DRY RUN: {len(empty_post_ids)} empty-caption post(s) found.\n")
    for i, pid in enumerate(empty_post_ids, 1):
        details = get_post_details(pid)
        if not details:
            print(f"[{i}/{len(empty_post_ids)}] {pid} — SKIP (could not fetch)")
            continue
        if not details["media_url"]:
            print(f"[{i}/{len(empty_post_ids)}] {pid} — SKIP (no media)")
            continue
        caption = random.choice(CTA_CAPTIONS)
        print(f"[{i}/{len(empty_post_ids)}] {pid}")
        print(f"  Scheduled:  {details['scheduled_for']}")
        print(f"  Media:      {details['media_url'][:60]}...")
        print(f"  New caption: {caption[:60]}{'...' if len(caption) > 60 else ''}")
        print()
        time.sleep(1)  # gap to avoid rate limiting on posts:get calls
    print(f"DRY RUN complete — no posts were modified.")


def main():
    parser = argparse.ArgumentParser(description="Fix empty-caption scheduled posts.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying anything")
    parser.add_argument(
        "--min-empty", type=int, default=0, metavar="N",
        help="Only fix if more than N empty-caption posts exist (default: 0, fix any)"
    )
    args = parser.parse_args()

    empty_post_ids = find_empty_posts()
    total = len(empty_post_ids)

    if total == 0:
        print("No empty-caption posts found.")
        return

    if total <= args.min_empty:
        print(f"{total} empty-caption post(s) found — at or below --min-empty threshold of {args.min_empty}. Skipping.")
        return

    if args.dry_run:
        dry_run(empty_post_ids)
        return

    ok_count = 0
    for i, pid in enumerate(empty_post_ids, 1):
        print(f"[{i}/{total}] {pid}")
        if fix_post(pid):
            ok_count += 1
        time.sleep(2)  # gap between posts to avoid rate limiting
    print(f"\nDone: {ok_count}/{total} posts fixed.")


if __name__ == "__main__":
    main()
