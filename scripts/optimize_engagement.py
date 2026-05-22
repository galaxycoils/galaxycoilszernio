#!/usr/bin/env python3
"""
Analyze recent post engagement and optimize scheduling weights.
"""

import os
import subprocess
import json
import re
import shutil
from pathlib import Path

def _resolve_zernio() -> str:
    path = shutil.which("zernio") or os.environ.get("ZERNIO_PATH")
    if path:
        return path
    default_path = "/Users/cmd/.npm-global/bin/zernio"
    if os.path.exists(default_path):
        return default_path
    return "zernio"

ZERNI0 = _resolve_zernio()
WEIGHTS_FILE = "/Users/cmd/galaxycoilszernio/logs/engagement_weights.json"


def classify_caption(content: str) -> str:
    content = content or ""
    text_no_hashtags = re.sub(r'#\w+', '', content).strip()
    if not text_no_hashtags:
        return "empty"
    
    content_lower = content.lower()
    if any(k in content_lower for k in ["save", "tip", "saas", "workflow", "nd filter", "settings", "rule"]):
        return "value"
    if any(k in content_lower for k in ["?", "👇", "vote", "rate", "tag", "dm"]):
        return "cta"
    
    return "micro"


def calculate_weights(categories: dict) -> dict:
    averages = {}
    for cat in ["empty", "micro", "value", "cta"]:
        er_list = categories.get(cat, [])
        averages[cat] = sum(er_list) / len(er_list) if er_list else 0.0
    
    total_er = sum(averages.values())
    if total_er <= 0:
        return {"empty": 0.30, "micro": 0.22, "value": 0.18, "cta": 0.30}
    
    floor = 0.10
    num_categories = 4
    remaining_weight = 1.0 - (floor * num_categories)
    
    weights = {}
    for cat, avg_er in averages.items():
        weights[cat] = round(floor + (avg_er / total_er) * remaining_weight, 4)
        
    # Ensure they sum to exactly 1.0 after rounding issues
    diff = 1.0 - sum(weights.values())
    if diff != 0:
        # Adjust the highest weight slightly
        max_cat = max(weights, key=weights.get)
        weights[max_cat] = round(weights[max_cat] + diff, 4)
        
    return weights


def main():
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    
    try:
        result = subprocess.run([ZERNI0, "analytics:posts", "--limit", "100", "--pretty"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error running zernio analytics:posts: {e}")
        # Default fallback
        fallback = {"empty": 0.30, "micro": 0.22, "value": 0.18, "cta": 0.30}
        with open(WEIGHTS_FILE, "w") as f:
            json.dump(fallback, f, indent=2)
        print(f"Wrote fallback weights to {WEIGHTS_FILE}")
        return

    posts = data.get("posts", [])
    categories = {"empty": [], "micro": [], "value": [], "cta": []}
    
    for post in posts:
        content = post.get("content", "") or ""
        cat = classify_caption(content)
        
        analytics = post.get("analytics", {})
        er = analytics.get("engagementRate") or 0.0
        categories[cat].append(er)

    weights = calculate_weights(categories)
    
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=2)
        
    print(f"Optimization weights calculated:")
    for cat, w in weights.items():
        print(f"  {cat}: {w:.4f}")
    print(f"Weights written to {WEIGHTS_FILE}")


if __name__ == "__main__":
    main()
