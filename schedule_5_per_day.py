"""Schedule 5 posts per day at fixed time slots using Pexels video content.

Usage:
  python3 schedule_5_per_day.py              # Schedule posts for open slots
  python3 schedule_5_per_day.py --dry-run    # Preview what would be scheduled
  python3 schedule_5_per_day.py --help       # Show all options

Set PEXELS_API_KEY in a .env file or environment variable.
"""

import argparse
import datetime as _dt_module  # robust ISO parsing (kept unpatched by tests that mock `datetime`)
import json
import os
import random
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS
from scripts.post_utils import ZERNI0
from scripts.post_utils import create_post as _create_post
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


def run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def list_scheduled() -> list[dict]:
    return run_json([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "100", "--pretty"]).get("posts", [])


def search_pexels(query: str, per_page: int = 30, max_retries: int = 3) -> list[dict]:
    """Search Pexels videos with retry/backoff on transient failures.

    Previously a single Pexels 429/5xx or connection error aborted the whole
    scheduling run. Now retries up to max_retries with linear backoff.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": str(per_page)},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("videos", [])
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Pexels search failed after {max_retries} attempts: {last_error}")


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


def fetch_unique_urls(limit: int) -> list[str]:
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


def generate_caption_plan(total: int) -> list[str]:
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


def _parse_iso(ts: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp to an aware UTC datetime.

    Tolerates 'Z' suffixes, explicit offsets, missing milliseconds, and naive
    timestamps (assumed UTC). Returns None for empty/unparseable values.

    Uses _dt_module.datetime so tests that mock the module-level `datetime`
    name (to freeze now()) don't break parsing.
    """
    if not ts:
        return None
    try:
        dt = _dt_module.datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt_module.timezone.utc)
    return dt.astimezone(_dt_module.timezone.utc)


def open_slots(days_ahead: int = 10) -> list[str]:
    """Return ISO timestamps of unoccupied future slots.

    Occupied detection compares parsed datetimes (not raw strings), so API
    responses like '2026-06-01T10:00:00Z' or '+00:00' offsets still match the
    '.000Z' slot format — preventing double-booking.
    """
    scheduled = list_scheduled()
    occupied = set()
    for post in scheduled:
        parsed = _parse_iso(post.get("scheduledFor"))
        if parsed is not None:
            occupied.add(parsed)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    slots = []
    for day_offset in range(days_ahead + 1):
        day = (start + timedelta(days=day_offset)).date()
        for hour in SLOTS:
            dt = datetime(day.year, day.month, day.day, hour, 0, 0, tzinfo=timezone.utc)
            if dt > start and dt not in occupied:
                slots.append(dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
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

    if not args.dry_run and not PEXELS_API_KEY:
        raise SystemExit(
            "PEXELS_API_KEY is not set. Add it to a .env file at the project "
            "root (see .env.example) or export it in the environment."
        )

    slots = open_slots(days_ahead=10)
    if not slots:
        print("No open slots found.")
        return

    captions = generate_caption_plan(len(slots))

    if args.dry_run:
        print(f"[DRY RUN] Would schedule {len(slots)} posts:\n")
        for scheduled_at, caption in zip(slots, captions, strict=False):
            print(f"  {scheduled_at}  →  {caption}")
        print("\n[DRY RUN] No posts created.")
        return

    urls = fetch_unique_urls(limit=len(slots))
    if len(urls) < len(slots):
        raise RuntimeError(f"Only found {len(urls)} unique videos for {len(slots)} slots")
    for scheduled_at, url, caption in zip(slots, urls, captions, strict=False):
        create_post(url, caption, scheduled_at)
        time.sleep(5)
    print(f"Scheduled {len(slots)} unique posts.")


if __name__ == "__main__":  # pragma: no cover
    main()
