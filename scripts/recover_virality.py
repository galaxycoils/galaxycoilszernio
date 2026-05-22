import json
import time
import sys
import os
from pathlib import Path

# Fix module import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.post_utils import create_post
from scripts.hashtags_pool import BRANDED, NICHE_MAP
import random

MANIFEST_PATH = "/Users/cmd/galaxycoilszernio/backups/2026-05-20-fix/rebuild-manifest.json"

def get_hashtags():
    niche = random.choice(list(NICHE_MAP.keys()))
    tags = BRANDED + random.sample(NICHE_MAP[niche], 3)
    return " ".join(tags)

def main():
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    
    success = 0
    failed = 0
    
    for item in manifest:
        caption = item["content"]
        # Apply the new hashtag strategy to non-empty posts
        if caption:
            # Check if it already has hashtags from a partial run
            if "#" not in caption:
                caption = f"{caption}\n\n{get_hashtags()}"
        
        print(f"Creating post for {item['scheduledFor']}...", flush=True)
        if create_post(item["mediaUrl"], caption, item["scheduledFor"]):
            success += 1
            print("Success.", flush=True)
        else:
            failed += 1
            print("Failed.", flush=True)
        time.sleep(2)
    
    print(f"Done. Success: {success}, Failed: {failed}", flush=True)

if __name__ == "__main__":
    main()
