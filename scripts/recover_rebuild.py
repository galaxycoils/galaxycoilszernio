"""Recover all posts from a rebuild manifest in a single pass.

Usage:
  python3 scripts/recover_rebuild.py          # recover all posts
  python3 scripts/recover_rebuild.py --manifest path/to/manifest.json  # custom manifest
  python3 scripts/recover_rebuild.py -h       # show help
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
    print(f"Creating post for {item['scheduledFor']}...")
    _create_post(item["mediaUrl"], item["content"], item["scheduledFor"])

def main():
    parser = argparse.ArgumentParser(
        description="Recover all posts from a rebuild manifest."
    )
    parser.add_argument(
        "--manifest",
        default=MANIFEST,
        help=f"Path to rebuild manifest JSON (default: {MANIFEST})"
    )
    args = parser.parse_args()

    with open(args.manifest, "r") as f:
        manifest = json.load(f)
    
    for item in manifest:
        create_post(item)
        time.sleep(2) # Brief gap to avoid immediate 429

if __name__ == "__main__":
    main()
