"""Full queue health checker: totals, per-day, caption mix, duplicates, overlaps.

Exits 0 when the queue is healthy, 1 when duplicates or published/scheduled
overlaps are found — so `make audit` / CI / the pre-push hook actually fail
on an unhealthy queue (previously it always exited 0).

Caption classification uses the shared classifier from scripts.captions_pool
(exact pool membership first), so the reported caption mix matches what
generate_caption_plan() produced.

Usage:
  python3 scripts/verify_queue.py            # health report, exit 0/1
  python3 scripts/verify_queue.py --no-fail  # report only, always exit 0
"""

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.captions_pool import classify_caption
from scripts.secure_dedup import extract_id, fetch_posts, fetch_published_source_ids

# Target mix from the engagement pivot (PLAN.md): 30/30/22/18.
TARGET_MIX = {"empty": 0.30, "cta": 0.30, "micro-hook": 0.22, "value": 0.18}


def main() -> int:
    parser = argparse.ArgumentParser(description="Full queue health check.")
    parser.add_argument(
        "--no-fail", action="store_true",
        help="Always exit 0, even if the queue is unhealthy (report only).",
    )
    args = parser.parse_args()

    scheduled = fetch_posts("scheduled", limit=100)
    published_ids = fetch_published_source_ids(limit=100)

    source_ids: list[str] = []
    by_day: Counter = Counter()
    by_kind: Counter = Counter()
    overlap = []

    for post in sorted(scheduled, key=lambda p: p.get("scheduledFor", "")):
        dt = post.get("scheduledFor", "")
        day = dt[:10]
        by_day[day] += 1
        by_kind[classify_caption(post.get("content", ""))] += 1

        media_items = post.get("mediaItems") or []
        if media_items:
            url = media_items[0].get("url", "")
            source_id = extract_id(url)
            if source_id:
                source_ids.append(source_id)
                if source_id in published_ids:
                    overlap.append({"scheduledFor": dt, "source_id": source_id, "post_id": post.get("_id")})

    duplicates = {k: v for k, v in Counter(source_ids).items() if v > 1}
    healthy = not duplicates and not overlap

    total = len(scheduled)
    mix_pct = {
        kind: round(count / total * 100, 1) if total else 0.0
        for kind, count in sorted(by_kind.items())
    }

    print(json.dumps({
        "scheduled_total": total,
        "healthy": healthy,
        "scheduled_duplicates": duplicates,
        "published_overlap": overlap,
        "per_day": dict(sorted(by_day.items())),
        "caption_mix": dict(sorted(by_kind.items())),
        "caption_mix_pct": mix_pct,
        "target_mix_pct": {k: round(v * 100, 1) for k, v in TARGET_MIX.items()},
    }, indent=2))

    if not healthy and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
