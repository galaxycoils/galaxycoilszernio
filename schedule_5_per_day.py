"""Schedule 5 posts per day at fixed time slots using Pexels video content.

Usage:
  python3 schedule_5_per_day.py              # Schedule posts for open slots
  python3 schedule_5_per_day.py --dry-run    # Preview what would be scheduled
  python3 schedule_5_per_day.py --help       # Show all options

Set PEXELS_API_KEY in a .env file or environment variable.
"""

import argparse
import json
import os
import random
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS
from scripts.post_utils import create_post as _create_post, ZERNI0
from scripts.secure_dedup import extract_id, get_all_seen_source_ids, record_scheduled

# Load .env file if it exists (so the .env file at project root is picked up automatically)
_dotenv_path = Path(__file__).resolve().parent / ".env"
if _dotenv_path.is_file():
    with open(_dotenv_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                if _key not in os.environ:
                    os.environ[_key] = _val

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
SLOTS = [10, 13, 16, 19, 22]
QUERY_POOL = [
    "drone cinematic",
    "aerial landscape",
    "fpv flying",
    "drone mountain",
    "drone city",
    "drone ocean",
    "drone forest",
    "golden hour drone",
]
# Caption pools imported from scripts.captions_pool (engagement pivot: 30/30/22/18)


def run_json(cmd: List[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def list_scheduled() -> List[dict]:
    return run_json([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "100", "--pretty"]).get("posts", [])


def search_pexels(query: str, per_page: int = 30) -> List[dict]:
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("videos", [])


def choose_video_url(video: dict) -> str:
    files = video.get("video_files", [])
    ranked = sorted(
        [f for f in files if f.get("link")],
        key=lambda f: (
            abs((f.get("height") or 0) - 1920),
            -min((f.get("height") or 0), (f.get("width") or 0)),
        ),
    )
    return ranked[0]["link"] if ranked else ""


def fetch_unique_urls(limit: int) -> List[str]:
    seen = get_all_seen_source_ids(include_scheduled=True)
    urls = []
    local_ids = set()
    for query in QUERY_POOL:
        for video in search_pexels(query):
            url = choose_video_url(video)
            video_id = extract_id(url)
            if not video_id or video_id in seen or video_id in local_ids:
                continue
            local_ids.add(video_id)
            urls.append(url)
            if len(urls) >= limit:
                return urls
    return urls


def generate_caption_plan(total: int) -> List[str]:
    # Engagement pivot (2026-05-20): 30% CTA / 30% Empty / 22% Micro / 18% Value
    empty_count = round(total * 0.30)
    micro_count = round(total * 0.22)
    value_count = round(total * 0.18)
    cta_count = total - empty_count - micro_count - value_count
    plan = [""] * empty_count
    plan += random.sample(MICRO_HOOKS * ((micro_count // len(MICRO_HOOKS)) + 1), micro_count)
    plan += random.sample(VALUE_CAPTIONS * ((value_count // len(VALUE_CAPTIONS)) + 1), value_count)
    plan += random.sample(CTA_CAPTIONS * ((cta_count // len(CTA_CAPTIONS)) + 1), cta_count)
    random.shuffle(plan)
    return plan


def open_slots(days_ahead: int = 10) -> List[str]:
    scheduled = list_scheduled()
    occupied = {p.get("scheduledFor") for p in scheduled}
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    slots = []
    for day_offset in range(days_ahead + 1):
        day = (start + timedelta(days=day_offset)).date()
        for hour in SLOTS:
            dt = datetime(day.year, day.month, day.day, hour, 0, 0, tzinfo=timezone.utc)
            iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if dt > start and iso not in occupied:
                slots.append(iso)
    return slots


def create_post(url: str, caption: str, scheduled_at: str) -> None:
    if _create_post(url, caption, scheduled_at):
        video_id = extract_id(url)
        if video_id:
            record_scheduled(video_id)
    else:
        raise RuntimeError(f"Failed to create post for {scheduled_at}")


def main():
    parser = argparse.ArgumentParser(
        description="Schedule 5 posts per day at fixed time slots (10,13,16,19,22 UTC) using Pexels video content."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview which slots and captions would be scheduled without creating posts."
    )
    args = parser.parse_args()

    slots = open_slots(days_ahead=10)
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
        time.sleep(5)
    print(f"Scheduled {len(slots)} unique posts.")


if __name__ == "__main__":
    main()