"""
Shared utilities for creating zernio posts across all scheduling/recovery scripts.
"""

from __future__ import annotations
import subprocess
import time
import json
import os
import shutil
import requests
import uuid
import random
from typing import Optional
from pathlib import Path

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
IG_ACCOUNT_ID = "6a0afc8a5e333c0529912a50"
THREADS_ACCOUNT_ID = "6a0f83d7520992756d97578f"
DEDUP_SKIP_CAPTION = "Test caption with hashtags #drone #viral"

TAGS = "drone,fpv,cinematic,aerial,dronevideo,fpvlife,cinematography,dronelife,aerialvideography,viral"
HASHTAGS = "#drone,#fpv,#cinematic,#aerial,#dronevideo,#fpvlife,#droneshots,#cinematicdrone,#aerialfootage,#dronefly,#viral,#explore"
TIMEZONE = "America/New_York"


def ensure_zernio_media_url(url: str) -> str:
    """
    Ensure the media URL is hosted on Zernio CDN.
    If it's a local file, uploads it.
    If it's a remote URL (including existing zernio.com URLs), downloads it locally then uploads it to Zernio as a fresh asset.
    """
    if not url:
        return url
        
    # Case 1: Local file path (exists and is not a URL)
    if not (url.startswith("http://") or url.startswith("https://")) and os.path.exists(url) and os.path.isfile(url):
        try:
            print(f"Uploading local media file to Zernio CDN: {url}")
            cmd = [ZERNI0, "media:upload", url, "--pretty"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                zernio_url = data.get("url")
                if zernio_url:
                    print(f"  ✓ Media uploaded to Zernio CDN: {zernio_url}")
                    return zernio_url
            print(f"  ✗ Local media upload failed with returncode {result.returncode}: {result.stderr}")
        except Exception as e:
            print(f"  ✗ Exception during local media upload: {e}")
        return url

    # Case 2: Remote URL (treat all URLs as remote to ensure a fresh Zernio asset)
    if url.startswith("http://") or url.startswith("https://"):
        ext = ".mp4"
        url_lower = url.lower()
        for possible_ext in [".mp4", ".mov", ".avi", ".webm", ".m4v", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"]:
            if possible_ext in url_lower:
                ext = possible_ext
                break
        
        temp_dir = Path("/Users/cmd/galaxycoilszernio/temp_media")
        temp_dir.mkdir(exist_ok=True)
        local_path = temp_dir / f"temp_{uuid.uuid4().hex}{ext}"
        
        compressed_path = None
        try:
            print(f"Downloading remote media for reliability: {url}")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            upload_path = local_path
            # Compress video if applicable to prevent API timeouts on target platforms
            if ext in [".mp4", ".mov", ".avi", ".webm", ".m4v"]:
                print(f"Compressing video using ffmpeg to prevent API timeouts...")
                compressed_path = temp_dir / f"compressed_{uuid.uuid4().hex}.mp4"
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", str(local_path),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                    "-vf", "scale='min(1080,iw)':min'(1920,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-c:a", "aac", "-b:a", "128k",
                    str(compressed_path)
                ]
                comp_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                if comp_result.returncode == 0 and compressed_path.exists():
                    print("  ✓ Video compressed successfully.")
                    upload_path = compressed_path
                else:
                    print(f"  ✗ Video compression failed. Proceeding with original file. Error: {comp_result.stderr[-200:] if comp_result.stderr else 'Unknown'}")

            print(f"Uploading file to Zernio CDN: {upload_path}")
            cmd = [ZERNI0, "media:upload", str(upload_path), "--pretty"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                zernio_url = data.get("url")
                if zernio_url:
                    print(f"  ✓ Remote media uploaded to Zernio CDN: {zernio_url}")
                    return zernio_url
            print(f"  ✗ Remote media upload failed with returncode {result.returncode}: {result.stderr}")
        except Exception as e:
            print(f"  ✗ Exception during remote media download/upload: {e}")
        finally:
            if local_path.exists():
                local_path.unlink()
            if compressed_path and compressed_path.exists():
                compressed_path.unlink()
                
    return url


def apply_dedup_suffix(caption: str) -> str:
    """Append a unique token so Zernio/Meta do not treat reposts as duplicate content."""
    text = (caption or "").strip()
    if not text or text == DEDUP_SKIP_CAPTION:
        return caption
    return f"{text} #{uuid.uuid4().hex[:6]}"


def validate_post_content(caption: str, platform: str = "instagram") -> bool:
    text = (caption or "").strip()
    if not text or len(text.split()) < 3:
        return False
    return True


def create_single_post(
    url: Optional[str] = None,
    caption: str = "",
    scheduled_at: str = "",
    *,
    account_id: Optional[str] = None,
    accounts: Optional[str | list[str]] = None,
    draft: bool = False,
    max_retries: int = 3,
    media_url: Optional[str] = None,
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
    target_desc = "+".join(
        ["threads" if a == THREADS_ACCOUNT_ID else "instagram" for a in accounts]
    )

    caption = apply_dedup_suffix(caption)

    # Increase retries for Threads (often needs more room for media processing)
    if has_threads:
        max_retries = max(max_retries, 5)

    if not validate_post_content(caption, target_platform):
        print(f"ERROR: Caption validation failed for {target_platform}: '{caption[:60]}'")
        return False

    cmd = [
        ZERNI0, "posts:create",
        "--text", caption,
        "--accounts", accounts_str,
        "--timezone", TIMEZONE,
    ]
    
    resolved_media = media_url
    if url and not resolved_media:
        resolved_media = ensure_zernio_media_url(url)
    if resolved_media:
        cmd.extend(["--media", resolved_media])

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

        # ERROR HANDLING (Log to file and check for retries)
        log_path = os.path.join("/Users/cmd/galaxycoilszernio", "logs", "cli_errors.log")
        with open(log_path, "a") as f:
            f.write(f"--- Attempt {attempt} ---\nCmd: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}\n\n")

        # Analyze error content
        raw = ""
        if isinstance(result.stdout, str):
            raw += result.stdout
        elif isinstance(result.stdout, (bytes, bytearray)):
            raw += result.stdout.decode(errors='ignore')
        
        if isinstance(result.stderr, str):
            raw += result.stderr
        elif isinstance(result.stderr, (bytes, bytearray)):
            raw += result.stderr.decode(errors='ignore')
        
        msg = raw.lower()
        is_429 = "429" in msg or "rate" in msg
        is_500 = "500" in msg or "internal server error" in msg
        is_oauth = "oauth" in msg or "exception" in msg

        if is_429:
            # Randomized exponential backoff to avoid hammering API
            wait = (60 * (2 ** (attempt - 1))) + (random.randint(0, 30))
            print(f"  ⟳ Rate limited (429) {target_desc} attempt {attempt}/{max_retries}, retry in {wait}s")
            time.sleep(wait)
        elif is_500:
            # Randomized backoff for server errors
            wait = (10 * attempt) + (random.randint(0, 10))
            print(f"  ⟳ Server error (500) {target_desc} attempt {attempt}/{max_retries}, retry in {wait}s")
            time.sleep(wait)
        elif is_oauth:
            # Check if it's a transient OAuth error (e.g., Code 2, is_transient: true)
            is_transient = "transient" in msg or '"code":2' in msg
            if is_transient and attempt < max_retries:
                wait = 15 * attempt
                print(f"  ⟳ Transient OAuth error (retryable) {target_desc} attempt {attempt}/{max_retries}, retry in {wait}s")
                time.sleep(wait)
            else:
                print(f"  ✗ Persistent/Max-retry Auth error {target_desc}: {raw[:300]}")
                return False
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


def create_paired_posts(
    url: Optional[str],
    ig_caption: str,
    threads_caption: str,
    scheduled_at: str,
    *,
    ig_account: str = IG_ACCOUNT_ID,
    threads_account: str = THREADS_ACCOUNT_ID,
    require_threads: bool = False,
    max_retries: int = 3,
    media_url: Optional[str] = None,
) -> tuple[str | bool, str | bool]:
    """
    Schedule the same media to Instagram and Threads with platform-specific captions.
    Uploads media once, then creates two posts (separate content hashes for dedup).
    Pass media_url when the asset is already on Zernio CDN (migrations, retries).
    """
    cdn_url = media_url
    if url and not cdn_url:
        cdn_url = ensure_zernio_media_url(url)

    ig_result = create_single_post(
        None,
        ig_caption,
        scheduled_at,
        accounts=[ig_account],
        max_retries=max_retries,
        media_url=cdn_url,
    )
    if not ig_result:
        return False, False

    threads_result = create_single_post(
        None,
        threads_caption,
        scheduled_at,
        accounts=[threads_account],
        max_retries=max_retries,
        media_url=cdn_url,
    )
    if require_threads and not threads_result:
        return ig_result, False
    return ig_result, threads_result


# Backward compatibility alias
create_post = create_single_post
