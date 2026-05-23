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
from scripts.post_utils import create_paired_posts, ZERNI0
from scripts.secure_dedup import extract_id, get_all_seen_source_ids, record_scheduled
from scripts.threads_utils import build_threads_caption
from scripts.rebuild_viral_queue import get_social_seo_tags

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
IG_ACCOUNT = "6a0afc8a5e333c0529912a50"
THREADS_ACCOUNT = "6a0f83d7520992756d97578f"
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
    "luxury real estate aerial",
    "cinematic nature",
    "drone racing",
    "aerial cinematography",
    "fpv freestyle"
]


WEIGHTS_FILE = Path("/Users/cmd/galaxycoilszernio/logs/engagement_weights.json")


def run_json(cmd: List[str]) -> dict:

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def list_scheduled() -> List[dict]:
    if not ZERNI0:
        return []
    return run_json([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "100", "--pretty"]).get("posts", [])


def search_pexels(query: str, per_page: int = 80) -> List[dict]:
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page, "orientation": "portrait"},
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
    queries = random.sample(QUERY_POOL, len(QUERY_POOL))
    for query in queries:
        for video in search_pexels(query):
            # Enforce maximum duration of 40 seconds if present
            duration = video.get("duration")
            if duration is not None and duration > 40:
                continue
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
    # Default engagement pivot: 30% CTA / 30% Empty / 22% Micro / 18% Value
    weights = {"empty": 0.30, "micro": 0.22, "value": 0.18, "cta": 0.30}
    weights_file = WEIGHTS_FILE
    
    if weights_file.is_file():
        try:
            with open(weights_file, "r") as f:
                loaded = json.load(f)
                if all(k in loaded for k in ["empty", "micro", "value", "cta"]):
                    weights = loaded
                    print(f"Loaded dynamic engagement weights: {weights}")
        except Exception as e:
            print(f"Warning: Failed to load dynamic weights, using default. Error: {e}")

    empty_count = max(0, round(total * weights.get("empty", 0.30)))
    micro_count = max(0, round(total * weights.get("micro", 0.22)))
    value_count = max(0, round(total * weights.get("value", 0.18)))
    cta_count = max(0, total - empty_count - micro_count - value_count)
    
    # Adjust total discrepancy
    current_total = empty_count + micro_count + value_count + cta_count
    if current_total != total:
        diff = total - current_total
        cta_count = max(0, cta_count + diff)

    plan = [""] * empty_count
    plan += random.sample(MICRO_HOOKS * ((micro_count // len(MICRO_HOOKS)) + 1), micro_count)
    plan += random.sample(VALUE_CAPTIONS * ((value_count // len(VALUE_CAPTIONS)) + 1), value_count)
    plan += random.sample(CTA_CAPTIONS * ((cta_count // len(CTA_CAPTIONS)) + 1), cta_count)
    random.shuffle(plan)
    return plan
    

def open_slots(days_ahead: int = 10) -> List[str]:
    scheduled = list_scheduled()
    occupied = set()
    for p in scheduled:
        sf = p.get("scheduledFor")
        if sf:
            platforms = p.get("platforms")
            if not platforms or platforms[0].get("accountId") == IG_ACCOUNT:
                occupied.add(sf)
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
    video_id = extract_id(url)
    print(f"Scheduling IG + Threads (separate captions) for {scheduled_at}...")
    tags = get_social_seo_tags()
    ig_caption = f"{caption}\n\n{tags}" if caption else tags
    threads_caption = build_threads_caption(caption)

    ig_post_id, threads_post_id = create_paired_posts(
        url,
        ig_caption,
        threads_caption,
        scheduled_at,
        ig_account=IG_ACCOUNT,
        threads_account=THREADS_ACCOUNT,
        require_threads=False,
    )
    if not ig_post_id:
        raise RuntimeError(f"Failed to schedule Instagram post for {scheduled_at}")
    if video_id:
        record_scheduled(video_id, url)
    if not threads_post_id:
        print(f"  ⚠ Instagram scheduled ({ig_post_id}) but Threads failed for {scheduled_at}")


def main():
    parser = argparse.ArgumentParser(
        description="Schedule 5 posts per day at fixed time slots (10,13,16,19,22 UTC) using Pexels video content."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview which slots and captions would be scheduled without creating posts."
    )
    parser.add_argument(
        "--days", type=int, default=10,
        help="Number of days ahead to schedule (default: 10)"
    )
    args = parser.parse_args()

    slots = open_slots(days_ahead=args.days)
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
        print(f"Warning: Only found {len(urls)} videos for {len(slots)} slots.")
        slots = slots[:len(urls)]
        captions = captions[:len(urls)]

    for scheduled_at, url, caption in zip(slots, urls, captions):
        try:
            create_post(url, caption, scheduled_at)
            time.sleep(random.uniform(5, 15)) # Increased and randomized wait
        except Exception as e:
            print(f"Error scheduling post at {scheduled_at}: {e}")
            continue
    print(f"Scheduled {len(slots)} unique posts.")


if __name__ == "__main__":
    main()