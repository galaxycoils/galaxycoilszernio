"""Fill up to POSTS_TO_SCHEDULE gaps in the existing queue.

Usage:
  python3 fill_schedule_gaps.py              # Create posts to fill gaps
  python3 fill_schedule_gaps.py --dry-run    # Preview what would be scheduled
  python3 fill_schedule_gaps.py --help       # Show all options
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from schedule_5_per_day import open_slots, fetch_unique_urls, generate_caption_plan, create_post

POSTS_TO_SCHEDULE = 10


def main():
    parser = argparse.ArgumentParser(
        description="Fill up to 10 open schedule gaps with new posts."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview which slots and captions would be scheduled without creating posts."
    )
    args = parser.parse_args()

    slots = open_slots(days_ahead=10)[:POSTS_TO_SCHEDULE]
    if not slots:
        print("No open slots found.")
        return

    captions = generate_caption_plan(len(slots))

    if args.dry_run:
        print(f"[DRY RUN] Would schedule {len(slots)} posts:\n")
        for scheduled_at, caption in zip(slots, captions):
            print(f"  {scheduled_at}  →  {caption}")
        print(f"\n[DRY RUN] No posts created.")
        return

    urls = fetch_unique_urls(limit=len(slots))
    if len(urls) < len(slots):
        raise RuntimeError(f"Only found {len(urls)} unique videos for {len(slots)} slots")
    for scheduled_at, url, caption in zip(slots, urls, captions):
        create_post(url, caption, scheduled_at)
    print(f"Successfully scheduled {len(slots)} posts.")


if __name__ == "__main__":
    main()