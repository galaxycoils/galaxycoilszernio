import json
import subprocess
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ZERNI0 = "/Users/cmd/.npm-global/bin/zernio"

def run_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    return json.loads(result.stdout)

def main():
    print("Fetching scheduled and partial posts...")
    posts = []
    for status in ["scheduled", "partial"]:
        data = run_json([ZERNI0, "posts:list", "--status", status, "--limit", "500", "--pretty"])
        posts.extend(data.get("posts", []))
    
    if not posts:
        print("No scheduled posts to purge.")
        return

    print(f"Found {len(posts)} scheduled posts. Starting purge...")
    
    for post in posts:
        post_id = post["_id"]
        print(f"Deleting post {post_id}...")
        subprocess.run([ZERNI0, "posts:delete", post_id])
        time.sleep(0.5)

    print("Purge complete.")

if __name__ == "__main__":
    main()
