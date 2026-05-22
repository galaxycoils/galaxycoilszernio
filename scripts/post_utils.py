"""
Shared utilities for creating zernio posts across all scheduling/recovery scripts.
"""

from __future__ import annotations
import subprocess
import time
import json
import os
import shutil
from typing import Optional

def _resolve_zernio() -> str:
    path = shutil.which("zernio") or os.environ.get("ZERNIO_PATH")
    if path:
        return path
    default_path = "/Users/cmd/.npm-global/bin/zernio"
    if os.path.exists(default_path):
        return default_path
    return ""

ZERNI0 = _resolve_zernio()
ACCOUNT_ID = "6a0afc8a5e333c0529912a50"

TAGS = "drone,fpv,cinematic,aerial,dronevideo,fpvlife,cinematography,dronelife,aerialvideography,viral"
HASHTAGS = "#drone,#fpv,#cinematic,#aerial,#dronevideo,#fpvlife,#droneshots,#cinematicdrone,#aerialfootage,#dronefly,#viral,#explore"
TIMEZONE = "America/New_York"


def validate_post_content(caption: str, platform: str = "instagram") -> bool:
    text = (caption or "").strip()
    if not text or len(text.split()) < 3:
        return False
    return True


def create_single_post(
    url: str,
    caption: str,
    scheduled_at: str = "",
    *,
    account_id: Optional[str] = None,
    accounts: Optional[str | list[str]] = None,
    draft: bool = False,
    max_retries: int = 3,
) -> str | bool:
    """
    Create a single zernio post for one or more accounts.
    Returns post_id string on success, False on failure.
    """
    if accounts is None:
        if account_id:
            accounts = [account_id]
        else:
            accounts = [ACCOUNT_ID]
    elif isinstance(accounts, str):
        accounts = [a.strip() for a in accounts.split(",") if a.strip()]
    elif not isinstance(accounts, list):
        accounts = list(accounts)

    accounts_str = ",".join(accounts)

    has_threads = "6a0f83d7520992756d97578f" in accounts
    has_ig = any(a != "6a0f83d7520992756d97578f" for a in accounts)

    target_platform = "instagram" if has_ig else "threads"
    target_desc = "+".join(["threads" if a == "6a0f83d7520992756d97578f" else "instagram" for a in accounts])

    if not validate_post_content(caption, target_platform):
        print(f"ERROR: Caption validation failed for {target_platform}: '{caption[:60]}'")
        return False

    cmd = [
        ZERNI0, "posts:create",
        "--text", caption,
        "--accounts", accounts_str,
        "--media", url,
        "--timezone", TIMEZONE,
    ]

    if has_ig:
        cmd.extend(["--tags", TAGS, "--hashtags", HASHTAGS])

    if draft:
        cmd.append("--draft")
    elif scheduled_at:
        cmd.extend(["--scheduledAt", scheduled_at])
    else:
        print("ERROR: Either draft=True or scheduled_at is required.")
        return False

    for attempt in range(1, max_retries + 1):
        result = subprocess.run(cmd + ["--pretty"], capture_output=True, text=True)

        # SUCCESS CHECK FIRST
        if result.returncode == 0:
            try:
                stdout_str = ""
                if isinstance(result.stdout, (str, bytes, bytearray)):
                    stdout_str = result.stdout.decode() if isinstance(result.stdout, (bytes, bytearray)) else result.stdout
                
                try:
                    data = json.loads(stdout_str)
                    post_id = data.get("post", {}).get("id") or data.get("post", {}).get("_id") or data.get("id") or data.get("_id")
                    if post_id:
                        print(f"  ✓ {target_desc} post created: {post_id}")
                        return post_id
                except Exception:
                    # Fallback if JSON parsing fails but returncode was 0
                    print(f"  ✓ {target_desc} post created (fallback)")
                    return True
            except Exception as e:
                print(f"  ✗ Exception in success check: {e}")

        # ERROR HANDLING
        raw = ""
        if isinstance(result.stdout, (str, bytes, bytearray)):
            raw += result.stdout.decode() if isinstance(result.stdout, (bytes, bytearray)) else result.stdout
        if isinstance(result.stderr, (str, bytes, bytearray)):
            raw += result.stderr.decode() if isinstance(result.stderr, (bytes, bytearray)) else result.stderr
        
        msg = raw.lower()
        is_429 = "429" in msg or "rate" in msg
        is_500 = "500" in msg or "internal server error" in msg

        if is_429:
            wait = 60 * attempt
            print(f"  ⟳ Rate limited (429) {target_desc} attempt {attempt}/{max_retries}, retry in {wait}s")
            time.sleep(wait)
        elif is_500:
            wait = 10 * attempt
            print(f"  ⟳ Server error (500) {target_desc} attempt {attempt}/{max_retries}, retry in {wait}s")
            time.sleep(wait)
        else:
            print(f"  ✗ Non-retryable error {target_desc}: {raw[:300]}")
            return False

    print(f"  ✗ Max retries ({max_retries}) exceeded for {target_desc}")
    return False


def reply_to_post(post_id: str, account_id: str, message: str) -> bool:
    if not ZERNI0 or not post_id:
        return False
    cmd = [ZERNI0, "inbox:reply", post_id, "--accountId", account_id, "--message", message]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Replied to {post_id}")
        return True
    print(f"  ✗ Reply failed: {result.stderr[:200]}")
    return False


# Backward compatibility alias
create_post = create_single_post
