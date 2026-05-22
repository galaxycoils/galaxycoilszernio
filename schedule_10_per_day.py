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

from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS, GENERIC_HOOKS
from scripts.post_utils import create_single_post as create_post, ZERNI0, reply_to_post
from scripts.secure_dedup import extract_id, get_all_seen_source_ids, record_scheduled, is_blacklisted
from scripts.threads_utils import enrich_for_threads
from scripts.threads_conversation import generate_first_reply

# Load .env
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

# 10 Posts per day slots
SLOTS = [0, 2, 4, 8, 10, 12, 14, 16, 18, 20, 22]

QUERY_POOL = [
    "drone cinematic", "aerial landscape", "fpv flying", "drone mountain",
    "drone city", "drone ocean", "drone forest", "golden hour drone",
    "luxury real estate aerial", "cinematic nature", "drone racing"
]

def search_pexels(query: str, per_page: int = 40) -> List[dict]:
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
        key=lambda f: (abs((f.get("height") or 0) - 1920), -min((f.get("height") or 0), (f.get("width") or 0))),
    )
    return ranked[0]["link"] if ranked else ""

def fetch_unique_urls(limit: int) -> List[str]:
    seen = get_all_seen_source_ids(include_scheduled=True)
    urls = []
    local_ids = set()
    local_fps = set()
    
    # Shuffle query pool to find diverse content
    queries = random.sample(QUERY_POOL, len(QUERY_POOL))
    
    for query in queries:
        videos = search_pexels(query)
        for video in videos:
            url = choose_video_url(video)
            video_id = extract_id(url)
            
            # ATOMIC DEDUPLICATION: Check ID, Global Blacklist Fingerprint, AND Local Session Fingerprint
            if not video_id or video_id in seen or video_id in local_ids:
                continue
            
            from scripts.secure_dedup import get_fingerprint
            fp = get_fingerprint(url)
            if fp in local_fps or is_blacklisted(url):
                continue
                
            local_ids.add(video_id)
            local_fps.add(fp)
            urls.append(url)
            
            if len(urls) >= limit:
                return urls
    return urls

def generate_caption_plan(total: int) -> List[str]:
    # Mix for 10/day: Hook, Value, CTA, Generic
    plan = []
    pools = [MICRO_HOOKS, VALUE_CAPTIONS, CTA_CAPTIONS, GENERIC_HOOKS]
    for i in range(total):
        pool = pools[i % len(pools)]
        plan.append(random.choice(pool))
    random.shuffle(plan)
    return plan

def open_slots(days_ahead: int = 7) -> List[str]:
    # Query IG scheduled posts (base for scheduling)
    data = subprocess.run([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "500", "--pretty"], capture_output=True, text=True)
    scheduled = json.loads(data.stdout).get("posts", [])
    occupied = {p.get("scheduledFor") for p in scheduled if p.get("platforms", [{}])[0].get("accountId") == IG_ACCOUNT}
    
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

def main():
    parser = argparse.ArgumentParser(description="Schedule 10 posts/day on IG + Threads")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slots = open_slots(days_ahead=7)
    if not slots:
        print("No open slots found.")
        return

    print(f"Planning {len(slots)} slots (IG + Threads)...")
    captions = generate_caption_plan(len(slots))
    urls = fetch_unique_urls(limit=len(slots))
    
    if len(urls) < len(slots):
        print(f"Warning: Only found {len(urls)} videos for {len(slots)} slots.")
        slots = slots[:len(urls)]
        captions = captions[:len(urls)]

    if args.dry_run:
        for s, c in zip(slots, captions):
            print(f"Slot: {s} | Caption: {c[:50]}...")
        return

    for scheduled_at, url, caption in zip(slots, urls, captions):
        video_id = extract_id(url)
        
        print(f"Scheduling IG & Threads simultaneously for {scheduled_at}...")
        from scripts.rebuild_viral_queue import get_social_seo_tags
        ig_caption = f"{caption}\n\n{get_social_seo_tags()}" if caption else get_social_seo_tags()

        post_id = create_post(url, ig_caption, scheduled_at, accounts=[IG_ACCOUNT, THREADS_ACCOUNT])
        if post_id:
            if video_id:
                record_scheduled(video_id, url)

            if isinstance(post_id, str):
                print(f"Adding first reply to Threads post {post_id}...")
                reply_text = generate_first_reply()
                reply_to_post(post_id, THREADS_ACCOUNT, reply_text)
        
        time.sleep(10) # Safety buffer

if __name__ == "__main__":
    main()
