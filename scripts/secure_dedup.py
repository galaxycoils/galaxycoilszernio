import json
import os
import re
import shutil
import subprocess
from collections import Counter
from typing import Iterable, List, Optional, Set

BASE_DIR = "/Users/cmd/galaxycoilszernio"
HISTORY_FILE = f"{BASE_DIR}/history.log"
GLOBAL_BLACKLIST = f"{BASE_DIR}/logs/global_video_blacklist.json"
ZERNI0 = "/Users/cmd/.npm-global/bin/zernio"

def load_blacklist() -> Set[str]:
    if not os.path.exists(GLOBAL_BLACKLIST):
        return set()
    with open(GLOBAL_BLACKLIST, "r") as f:
        try:
            return set(json.load(f))
        except:
            return set()

def save_blacklist(ids: Set[str]):
    os.makedirs(os.path.dirname(GLOBAL_BLACKLIST), exist_ok=True)
    with open(GLOBAL_BLACKLIST, "w") as f:
        json.dump(list(sorted(ids)), f, indent=2)

def load_history() -> Set[str]:
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def extract_id(url: str) -> Optional[str]:
    # Matches Pexels standard video URL structure
    match = re.search(r"video-files/(\d+)/", url or "")
    if match:
        return match.group(1)
    
    # Fallback: catch IDs in other common Pexels URL formats
    match = re.search(r"video/(\d+)/", url or "")
    if match:
        return match.group(1)

    # 2026 catch-all: any sequence of digits in a pexels URL usually is the ID
    if "pexels" in (url or "").lower():
        match = re.search(r"/(\d+)/", url)
        if match:
            return match.group(1)
        
    return None

def extract_id_from_any(url: str) -> Optional[str]:
    """Extract ID from any Pexels URL including CDN and shortened links."""
    if not url:
        return None
    for pattern in [r"video-files/(\d+)/", r"video/(\d+)/", r"/(\d+)/"]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_ids_from_urls(urls: Iterable[str]) -> Set[str]:
    ids = set()
    for url in urls:
        video_id = extract_id(url)
        if video_id:
            ids.add(video_id)
    return ids

def _run_json(cmd: List[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)

def fetch_posts(status: str, limit: int = 100) -> List[dict]:
    if not ZERNI0:
        return []
    data = _run_json([ZERNI0, "posts:list", "--status", status, "--limit", str(limit), "--pretty"])
    return data.get("posts", [])

def source_ids_from_posts(posts: Iterable[dict]) -> Set[str]:
    ids = set()
    for post in posts:
        media_items = post.get("mediaItems") or []
        if not media_items:
            continue
        url = media_items[0].get("url", "")
        video_id = extract_id(url)
        if video_id:
            ids.add(video_id)
    return ids

def fetch_published_source_ids(limit: int = 100) -> Set[str]:
    return source_ids_from_posts(fetch_posts("published", limit=limit))

def fetch_scheduled_source_ids(limit: int = 100) -> Set[str]:
    return source_ids_from_posts(fetch_posts("scheduled", limit=limit))

def get_all_seen_source_ids(include_scheduled: bool = True) -> Set[str]:
    seen = load_blacklist()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            seen.update({line.strip() for line in f if line.strip()})
    
    seen |= fetch_published_source_ids()
    if include_scheduled:
        seen |= fetch_scheduled_source_ids()
    
    save_blacklist(seen)
    return seen

def is_new(video_id: str, seen_ids: Set[str]) -> bool:
    return bool(video_id) and video_id not in seen_ids

import hashlib

def get_fingerprint(url: str) -> str:
    """Generate a unique fingerprint for a video URL (ignoring query params)."""
    if not url:
        return ""
    # Pexels URLs often have different query params for the same video file
    base = url.split("?")[0]
    return hashlib.sha256(base.encode()).hexdigest()

def record_scheduled(video_id: str, url: str = "") -> None:
    if not video_id:
        return
    existing = load_history()
    if video_id in existing:
        return
    
    # Store ID in history.log
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")
    
    # Store Fingerprint in global_video_blacklist
    if url:
        fp = get_fingerprint(url)
        blacklist = list(load_blacklist())
        if fp not in blacklist:
            blacklist.append(fp)
            save_blacklist(set(blacklist))

def is_blacklisted(url: str) -> bool:
    """Check if a URL fingerprint is in the global blacklist."""
    fp = get_fingerprint(url)
    return fp in load_blacklist()

def record_many(video_ids: Iterable[str]) -> None:
    existing = load_history()
    new_ids = [video_id for video_id in video_ids if video_id and video_id not in existing]
    if not new_ids:
        return
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for video_id in new_ids:
            f.write(f"{video_id}\n")

def duplicate_counts(video_ids: Iterable[str]) -> Counter:
    return Counter(video_id for video_id in video_ids if video_id)

if __name__ == "__main__":
    history_ids = load_history()
    published_ids = fetch_published_source_ids()
    scheduled_ids = fetch_scheduled_source_ids()
    print(json.dumps({
        "history_count": len(history_ids),
        "published_count": len(published_ids),
        "scheduled_count": len(scheduled_ids),
        "all_seen_count": len(history_ids.union(published_ids).union(scheduled_ids)),
    }, indent=2))
