"""Deep engagement analytics: engagement rate and views by caption category.

Fetches post analytics via the zernio CLI, classifies captions with the shared
classifier (scripts.captions_pool.classify_caption — same categories as
verify_queue.py and generate_caption_plan()), and writes two reports:

  logs/engagement-report.md    human-readable Markdown table
  logs/engagement-report.json  machine-readable metrics for automation

Usage:
  python3 scripts/analyze_engagement.py            # analyze last 100 posts
  python3 scripts/analyze_engagement.py --limit 200
"""

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.captions_pool import CATEGORIES, classify_caption

ZERNIO = shutil.which("zernio") or os.environ.get("ZERNIO_PATH", "")
REPORT_MD = Path("logs/engagement-report.md")
REPORT_JSON = Path("logs/engagement-report.json")

# Below this many posts, a category's averages are noise, not signal.
MIN_SAMPLE = 5


def fetch_analytics(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch posts with analytics from the zernio CLI."""
    if not ZERNIO:
        raise RuntimeError(
            "zernio CLI not found on PATH (set ZERNIO_PATH to its location)."
        )
    result = subprocess.run(
        [ZERNIO, "analytics:posts", "--limit", str(limit)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout).get("posts", [])


def summarize(posts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate ER/views per caption category.

    Every category in CATEGORIES is present in the output (even with zero
    posts) so downstream automation has a stable schema.
    """
    buckets: dict[str, dict[str, list[float]]] = {
        cat: {"er": [], "views": []} for cat in CATEGORIES
    }
    for post in posts:
        cat = classify_caption(post.get("content", "") or "")
        analytics = post.get("analytics", {}) or {}
        er = analytics.get("engagementRate") or 0
        views = analytics.get("views") or 0
        buckets[cat]["er"].append(float(er))
        buckets[cat]["views"].append(float(views))

    summary: dict[str, dict[str, Any]] = {}
    for cat in CATEGORIES:
        ers = buckets[cat]["er"]
        views = buckets[cat]["views"]
        count = len(ers)
        summary[cat] = {
            "count": count,
            "avg_er": round(sum(ers) / count, 3) if count else 0.0,
            "median_er": round(statistics.median(ers), 3) if count else 0.0,
            "avg_views": round(sum(views) / count, 1) if count else 0.0,
            "max_views": int(max(views)) if count else 0,
            "reliable": count >= MIN_SAMPLE,
        }
    return summary


def write_reports(summary: dict[str, dict[str, Any]], total_posts: int) -> None:
    """Write the Markdown and JSON engagement reports."""
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(f"# Engagement Report — {generated}\n\n")
        f.write(f"Posts analyzed: {total_posts}\n\n")
        f.write("| Category | Posts | Avg ER | Median ER | Avg Views | Max Views | Reliable |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for cat in CATEGORIES:
            m = summary[cat]
            reliable = "yes" if m["reliable"] else f"no (n<{MIN_SAMPLE})"
            f.write(
                f"| {cat} | {m['count']} | {m['avg_er']:.2f} | "
                f"{m['median_er']:.2f} | {m['avg_views']:.1f} | "
                f"{m['max_views']} | {reliable} |\n"
            )

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "posts_analyzed": total_posts,
            "min_sample": MIN_SAMPLE,
            "categories": summary,
        }, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Engagement analytics by caption category.")
    parser.add_argument("--limit", type=int, default=100, help="Max posts to analyze (default 100)")
    args = parser.parse_args()

    try:
        posts = fetch_analytics(limit=args.limit)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"Error fetching analytics: {exc}")
        return 2

    if not posts:
        print("No posts with analytics found.")
        return 0

    summary = summarize(posts)
    write_reports(summary, total_posts=len(posts))
    print(f"Analyzed {len(posts)} posts.")
    print(f"Reports written to {REPORT_MD} and {REPORT_JSON}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
