"""
Shared utilities for creating zernio posts across all scheduling/recovery scripts.

Centralizes: ZERNI0 path, account ID, viral tags/hashtags, timezone,
and the rate-limit-aware create_post retry loop.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import time

ZERNI0 = "/Users/cmd/.npm-global/bin/zernio"
ACCOUNT_ID = "6a0afc8a5e333c0529912a50"

TAGS = "drone,fpv,cinematic,aerial,dronevideo,fpvlife,cinematography,dronelife,aerialvideography,viral"
HASHTAGS = "#drone,#fpv,#cinematic,#aerial,#dronevideo,#fpvlife,#droneshots,#cinematicdrone,#aerialfootage,#dronefly,#viral,#explore"
TIMEZONE = "America/New_York"


from typing import Optional
import json

def validate_post_content(caption: str, platform: str = "instagram") -> bool:
    """Ensure caption is not empty and meets platform-specific requirements."""
    text = (caption or "").strip()
    if not text:
        return False
    
    # Instagram requires hashtags for Virality V5
    if platform == "instagram":
        if "#" not in text:
            return False
    
    # Minimum length check
    if len(text.split()) < 3:
        return False
    return True

def create_post(
    url: str,
    caption: str,
    scheduled_at: str = "",
    *,
    accounts: Optional[str | list[str]] = None,
    draft: bool = False,
    max_retries: int = 3,
    retry_delay: int = 5,
) -> str | bool:
    """
    Create zernio post(s) with tags, hashtags, and timezone baked in.
    Supports single account ID or list of account IDs.
    Returns the ID of the last created post if successful, or False.
    """
    if not ZERNI0:
        return False
    
    target_accounts = []
    if accounts:
        if isinstance(accounts, str):
            target_accounts = [accounts]
        else:
            target_accounts = accounts
    else:
        target_accounts = [ACCOUNT_ID]

    success = True
    for acc_id in target_accounts:
        # Simple platform detection based on ID length or mapping if needed
        # For this project: 6a0afc8a... is IG, 6a0f83d7... is Threads
        platform = "threads" if acc_id == "6a0f83d7520992756d97578f" else "instagram"
        
        # Virality V8: Basic caption validation (must have hashtags for IG)
        if not validate_post_content(caption, platform):
            print(f"ERROR: Mandatory caption validation failed for {platform} at {scheduled_at}. Content: '{caption}'")
            success = False
            continue

        cmd = [
            ZERNI0, "posts:create",
            "--text", caption,
            "--accounts", acc_id,
            "--media", url,
            "--timezone", TIMEZONE,
        ]
        
        # Instagram gets the legacy tag/hashtag flags
        if platform == "instagram":
            cmd.extend(["--tags", TAGS, "--hashtags", HASHTAGS])
            
        if draft:
            cmd.append("--draft")
        elif scheduled_at:
            cmd.extend(["--scheduledAt", scheduled_at])
        else:
            # We don't raise ValueError anymore, just return success=False and log
            print(f"ERROR: Either draft=True or a scheduled_at time is required.")
            success = False
            continue

        attempt = 0
        acc_success = False
        post_id = None
        while True:
            attempt += 1
            result = subprocess.run(cmd + ["--pretty"], capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    post_id = data.get("post", {}).get("id") or data.get("id")
                    if post_id:
                        acc_success = True
                        break
                except Exception:
                    # Fallback if JSON parsing fails but returncode was 0
                    acc_success = True
                    break
            msg = f"{result.stdout}\n{result.stderr}".lower()
            msg = f"{result.stdout}\n{result.stderr}".lower()
            
            # Identify retryable errors
            is_429 = "429" in msg or "rate" in msg
            is_500 = "500" in msg or "internal server error" in msg
            
            if is_429:
                wait_time = 60 * attempt # Exponential-ish backoff
                print(f"Rate limited (429) on {platform}. Attempt {attempt}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            elif is_500:
                wait_time = 10 * attempt
                print(f"Server error (500) on {platform}. Attempt {attempt}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Non-retryable error creating {platform} post: {result.stderr}")
                break
            
            if attempt >= max_retries:
                print(f"Max retries ({max_retries}) reached for {platform} post.")
                break
        
        if not acc_success:
            success = False
        elif post_id:
            # If we have multiple accounts, this returns the last one. 
            # For current usage, it's fine.
            success = post_id

    return success

def reply_to_post(post_id: str, account_id: str, message: str) -> bool:
    """
    Replies to a specific post using zernio inbox:reply.
    """
    if not ZERNI0 or not post_id:
        return False

    cmd = [
        ZERNI0, "inbox:reply", post_id,
        "--accountId", account_id,
        "--message", message
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Successfully replied to post {post_id}")
        return True
    else:
        print(f"Error replying to post {post_id}: {result.stderr}")
        return False
