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

ZERNI0 = shutil.which("zernio") or os.environ.get("ZERNIO_PATH", "")
ACCOUNT_ID = "6a0afc8a5e333c0529912a50"

TAGS = "drone,fpv,cinematic,aerial,dronevideo,fpvlife,cinematography,dronelife,aerialvideography,viral"
HASHTAGS = "#drone,#fpv,#cinematic,#aerial,#dronevideo,#fpvlife,#droneshots,#cinematicdrone,#aerialfootage,#dronefly,#viral,#explore"
TIMEZONE = "America/New_York"


from typing import Optional

def create_post(
    url: str,
    caption: str,
    scheduled_at: str = "",
    *,
    accounts: Optional[str] = None,
    draft: bool = False,
    max_retries: int = 3,
    retry_delay: int = 5,
) -> bool:
    """
    Create a zernio post with tags, hashtags, and timezone baked in.

    When ``draft=False`` (default), ``scheduled_at`` is required and the post
    is scheduled for that ISO 8601 time.  When ``draft=True``, ``scheduled_at``
    is ignored and ``--draft`` is passed instead.

    Handles 429 rate-limiting with a 60-second backoff. Returns True on
    success, False after exhausting max_retries (non-rate-limit failures).
    Callers that need infinite rate-limit retries can set max_retries high.

    Note: zernio auto-detects platform from the account ID, so no --platform
    flag is needed (nor does the CLI support one).
    """
    if not ZERNI0:
        return False
    cmd = [
        ZERNI0, "posts:create",
        "--text", caption,
        "--accounts", accounts or ACCOUNT_ID,
        "--media", url,
        "--tags", TAGS,
        "--hashtags", HASHTAGS,
        "--timezone", TIMEZONE,
    ]
    if draft:
        cmd.append("--draft")
    elif scheduled_at:
        cmd.extend(["--scheduledAt", scheduled_at])
    else:
        raise ValueError("Either draft=True or a scheduled_at time is required.")

    attempt = 0
    while True:
        attempt += 1
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        msg = f"{result.stdout}\n{result.stderr}".lower()
        if "429" in msg or "rate" in msg:
            time.sleep(60)
            continue
        if attempt >= max_retries:
            break
        time.sleep(retry_delay)

    return False
