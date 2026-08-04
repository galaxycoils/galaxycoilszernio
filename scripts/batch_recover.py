"""Recover posts from a rebuild manifest in parallel batches.

Usage:
  python3 scripts/batch_recover.py 0  # run batch 0
  python3 scripts/batch_recover.py 1  # run batch 1
  python3 scripts/batch_recover.py -h # show help
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
    return _create_post(item["mediaUrl"], item["content"], item["scheduledFor"])

def main():
    parser = argparse.ArgumentParser(
        description="Recover posts from a rebuild manifest in batches (for parallel recovery)."
    )
    parser.add_argument(
        "batch_num", type=int,
        help="Batch number (0-based). Posts are split into 4 batches."
    )
    args = parser.parse_args()

    batch_num = args.batch_num
    with open(MANIFEST) as f:
        manifest = json.load(f)

    # Split into 4 batches
    batch_size = len(manifest) // 4 + 1
    start = batch_num * batch_size
    end = min(start + batch_size, len(manifest))
    batch = manifest[start:end]

    print(f"Running batch {batch_num} ({start} to {end})...")
    for item in batch:
        if create_post(item):
            time.sleep(5)
        else:
            print(f"Batch {batch_num} stopped on failure.")
            break

if __name__ == "__main__":
    main()
