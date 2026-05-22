import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ZERNI0 = "/Users/cmd/.npm-global/bin/zernio"
ACCOUNT_ID = "6a0afc8a5e333c0529912a50"
BACKUP_MANIFEST = "/Users/cmd/galaxycoilszernio/backups/2026-05-20-fix/rebuild-manifest.json"

from scripts.post_utils import create_post as _create_post
from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS, GENERIC_HOOKS
from scripts.hashtags_pool import BRANDED_KEYWORDS, SEARCH_MAP
import random

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def run_json(cmd):
    code, out, err = run(cmd)
    if code != 0:
        raise RuntimeError(err or out)
    return json.loads(out)

def list_scheduled():
    data = run_json([ZERNI0, "posts:list", "--status", "scheduled", "--limit", "100", "--pretty"])
    return sorted(data.get("posts", []), key=lambda p: p.get("scheduledFor", ""))

def get_social_seo_tags():
    """
    Refactored for May 2026 SEO Standards:
    1. Enforces '3-5 Rule' (1 Branded + 3-4 Search Intent Keywords).
    2. Uses 'Search-Intent Keywords' instead of raw hashtags for better discovery.
    """
    niche = random.choice(list(SEARCH_MAP.keys()))
    from datetime import datetime
    day_seed = datetime.now().timetuple().tm_yday
    random.seed(day_seed + random.randint(0, 1000))
    
    # Select 3-4 keywords from the intent pool
    intent_keywords = random.sample(SEARCH_MAP[niche], random.randint(3, 4))
    
    # Combine Branded + Search Keywords (prepended with # for discovery)
    tags = BRANDED_KEYWORDS + [f"#{kw.replace(' ', '')}" for kw in intent_keywords]
    return " ".join(tags)

def build_caption_map(posts):
    by_day = defaultdict(list)
    for post in posts:
        day = post["scheduledFor"][:10]
        by_day[day].append(post)

    days = sorted(by_day)
    micro_i = 0
    value_i = 0
    cta_i = 0
    generic_i = 0
    manifest = []

    for idx, day in enumerate(days):
        day_posts = sorted(by_day[day], key=lambda p: p["scheduledFor"])
        day_captions = [
            MICRO_HOOKS[micro_i % len(MICRO_HOOKS)],
            CTA_CAPTIONS[cta_i % len(CTA_CAPTIONS)],
            VALUE_CAPTIONS[value_i % len(VALUE_CAPTIONS)],
            GENERIC_HOOKS[generic_i % len(GENERIC_HOOKS)],
            CTA_CAPTIONS[(cta_i + 1) % len(CTA_CAPTIONS)],
        ]
        micro_i += 1
        cta_i += 2
        value_i += 1
        generic_i += 1

        day_captions = day_captions[:len(day_posts)]

        for post, caption in zip(day_posts, day_captions):
            full_caption = f"{caption}\n\n{get_social_seo_tags()}"
            url = (post.get("mediaItems") or [{}])[0].get("url", "")
            manifest.append({
                "old_post_id": post.get("_id"),
                "scheduledFor": post.get("scheduledFor"),
                "mediaUrl": url,
                "content": full_caption,
            })
    return manifest

def delete_post(post_id):
    code, out, err = run([ZERNI0, "posts:delete", post_id])
    if code != 0:
        raise RuntimeError(err or out)

def create_post(item):
    if not _create_post(item["mediaUrl"], item["content"], item["scheduledFor"]):
        raise RuntimeError(f"Failed to create post for {item['scheduledFor']}")

def main():
    scheduled = list_scheduled()
    if not scheduled:
        print("No scheduled posts found.")
        return
    manifest = build_caption_map(scheduled)
    with open(BACKUP_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for post in scheduled:
        delete_post(post["_id"])
        time.sleep(1)

    for item in manifest:
        create_post(item)
        time.sleep(5)

    print(json.dumps({
        "rebuilt_posts": len(manifest),
        "empty": sum(1 for x in manifest if not x["content"]),
        "micro": sum(1 for x in manifest if any(h in x["content"] for h in MICRO_HOOKS)),
        "value": sum(1 for x in manifest if any(v in x["content"] for v in VALUE_CAPTIONS)),
        "cta": sum(1 for x in manifest if any(c in x["content"] for c in CTA_CAPTIONS)),
        "generic": sum(1 for x in manifest if any(g in x["content"] for g in GENERIC_HOOKS)),
    }, indent=2))

if __name__ == "__main__":
    main()
