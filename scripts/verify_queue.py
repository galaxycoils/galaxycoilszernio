import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.secure_dedup import extract_id, fetch_posts, fetch_published_source_ids

def classify_caption(content: str) -> str:
    text = (content or "").strip()
    lower = text.lower()
    if not text:
        return "empty"
    if text.startswith("#"):
        return "hashtag-only"
    if "day " in lower or "delivery:" in lower:
        return "day-template"
    if any(phrase in lower for phrase in ["save this", "save for your next", "workflow", "footage feels flat", "drone edit tip", "real estate"]):
        return "value"
    if any(phrase in lower for phrase in ["which shot", "too slow or just right", "would you post this", "which angle", "what would you rate", "comment raw", "what would you change", "what's your"]):
        return "cta-question"
    if len(text.split()) <= 5 and not text.endswith("?"):
        return "micro-hook"
    if any(phrase in lower for phrase in ["wait for the reveal", "pov:"]):
        return "hook-visual"
    return "other"


def main():
    scheduled = fetch_posts("scheduled", limit=100)
    published_ids = fetch_published_source_ids(limit=100)
    
    # NEW: Check for API error logs and categorize
    cli_errors = []
    error_summary = {"rate_limits": 0, "oauth_failures": 0, "duplicates": 0, "other": 0}
    if os.path.exists("logs/cli_errors.log"):
        with open("logs/cli_errors.log", "r") as f:
            lines = f.readlines()
            for line in lines:
                msg = line.lower()
                if "429" in msg or "rate" in msg:
                    error_summary["rate_limits"] += 1
                elif "oauth" in msg:
                    error_summary["oauth_failures"] += 1
                elif "duplicate" in msg:
                    error_summary["duplicates"] += 1
                elif "error" in msg or "failed" in msg:
                    error_summary["other"] += 1
            cli_errors = lines[-20:] # Last 20 lines

    source_ids = []
    by_day = Counter()
    by_kind = Counter()
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

    print(json.dumps({
        "scheduled_total": len(scheduled),
        "scheduled_duplicates": duplicates,
        "published_overlap": overlap,
        "per_day": dict(sorted(by_day.items())),
        "caption_mix": dict(by_kind),
        "cli_error_summary": error_summary,
        "recent_cli_errors": cli_errors
    }, indent=2))


if __name__ == "__main__":
    main()
