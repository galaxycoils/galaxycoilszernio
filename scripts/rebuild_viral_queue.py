import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ZERNI0 = shutil.which("zernio") or os.environ.get("ZERNIO_PATH", "")
ACCOUNT_ID = "6a0afc8a5e333c0529912a50"
BACKUP_MANIFEST = "/Users/cmd/galaxycoilszernio/backups/2026-05-20-fix/rebuild-manifest.json"

from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS
from scripts.post_utils import create_post as _create_post


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


def build_caption_map(posts):
    by_day = defaultdict(list)
    for post in posts:
        day = post["scheduledFor"][:10]
        by_day[day].append(post)

    days = sorted(by_day)
    micro_i = 0
    value_i = 0
    cta_i = 0
    manifest = []

    # Target: 14 empty, 14 cta, 10 micro, 7 value
    for idx, day in enumerate(days):
        day_posts = sorted(by_day[day], key=lambda p: p["scheduledFor"])
        times = [p["scheduledFor"][11:16] for p in day_posts]
        is_partial_first = idx == 0 and len(day_posts) == 1 and times == ["22:00"]
        is_partial_last = idx == len(days) - 1 and len(day_posts) == 4 and times == ["10:00", "13:00", "19:00", "22:00"]

        if is_partial_first:
            captions = [""]
        elif is_partial_last:
            captions = [
                CTA_CAPTIONS[cta_i % len(CTA_CAPTIONS)],
                MICRO_HOOKS[micro_i % len(MICRO_HOOKS)],
                CTA_CAPTIONS[(cta_i + 1) % len(CTA_CAPTIONS)],
                CTA_CAPTIONS[(cta_i + 2) % len(CTA_CAPTIONS)],
            ]
            cta_i += 3
            micro_i += 1
        else:
            # Full day (5 posts)
            # Pattern: Empty, Micro, Empty, Value, CTA
            # (Adjusting pattern to hit 14/14/10/7)
            # Days: 21, 22, 23, 24, 25, 26, 27, 28
            if day in ["2026-05-21", "2026-05-23", "2026-05-25", "2026-05-27"]:
                # 2 CTA day
                captions = [
                    "",
                    MICRO_HOOKS[micro_i % len(MICRO_HOOKS)],
                    CTA_CAPTIONS[cta_i % len(CTA_CAPTIONS)],
                    VALUE_CAPTIONS[value_i % len(VALUE_CAPTIONS)],
                    CTA_CAPTIONS[(cta_i + 1) % len(CTA_CAPTIONS)],
                ]
                micro_i += 1
                cta_i += 2
                value_i += 1
            else:
                # 1 CTA day
                captions = [
                    "",
                    MICRO_HOOKS[micro_i % len(MICRO_HOOKS)],
                    "",
                    VALUE_CAPTIONS[value_i % len(VALUE_CAPTIONS)],
                    CTA_CAPTIONS[cta_i % len(CTA_CAPTIONS)],
                ]
                micro_i += 1
                cta_i += 1
                value_i += 1

        if len(captions) != len(day_posts):
            raise RuntimeError(f"Caption count mismatch for {day}: {len(captions)} vs {len(day_posts)}")

        for post, caption in zip(day_posts, captions, strict=False):
            url = (post.get("mediaItems") or [{}])[0].get("url", "")
            manifest.append({
                "old_post_id": post.get("_id"),
                "scheduledFor": post.get("scheduledFor"),
                "mediaUrl": url,
                "content": caption,
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
        "micro": sum(1 for x in manifest if x["content"] in MICRO_HOOKS),
        "value": sum(1 for x in manifest if x["content"] in VALUE_CAPTIONS),
        "cta": sum(1 for x in manifest if x["content"] in CTA_CAPTIONS),
    }, indent=2))


if __name__ == "__main__":
    main()
