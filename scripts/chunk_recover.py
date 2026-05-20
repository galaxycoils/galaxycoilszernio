"""Recover a range of posts from a rebuild manifest by index.

Usage:
  python3 scripts/chunk_recover.py 0 10  # recover posts 0 through 9
  python3 scripts/chunk_recover.py -h    # show help
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MANIFEST = "/Users/cmd/galaxycoilszernio/backups/2026-05-20-fix/rebuild-manifest.json"

from scripts.post_utils import create_post as _create_post

def create_post(item):
    return _create_post(item["mediaUrl"], item["content"], item["scheduledFor"], max_retries=1)

def main():
    parser = argparse.ArgumentParser(
        description="Recover a range of posts from a rebuild manifest by index."
    )
    parser.add_argument("start", type=int, help="Start index (inclusive)")
    parser.add_argument("end", type=int, help="End index (exclusive)")
    args = parser.parse_args()

    start = args.start
    end = args.end

    if start < 0 or end < start:
        print("Error: start must be >= 0 and end must be > start.")
        return

    with open(MANIFEST, "r") as f:
        manifest = json.load(f)
        
    for i in range(start, min(end, len(manifest))):
        print(f"Creating post {i+1}/{len(manifest)}...")
        if create_post(manifest[i]):
            time.sleep(2)
        else:
            print("Stopping.")
            break

if __name__ == "__main__":
    main()
