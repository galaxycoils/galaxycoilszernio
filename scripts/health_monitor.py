#!/usr/bin/env python3
"""
Health Monitor for GalaxyCoils Zernio infrastructure.
Checks Pexels API connectivity and Zernio CLI status.
"""

import os
import subprocess
import requests
import sys
from pathlib import Path
from typing import Tuple

# Load .env file if it exists
_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.is_file():
    with open(_dotenv_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                if _key not in os.environ:
                    os.environ[_key] = _val

# Configuration
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
ZERNI0 = "/Users/cmd/.npm-global/bin/zernio"

def check_pexels() -> Tuple[bool, str]:
    """Check if Pexels API is reachable and key is valid."""
    if not PEXELS_API_KEY:
        return False, "PEXELS_API_KEY environment variable not set."
    
    try:
        # Simple search for 'drone' to verify API
        response = requests.get(
            "https://api.pexels.com/videos/search?query=drone&per_page=1",
            headers={"Authorization": PEXELS_API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            return True, "Pexels API is healthy."
        elif response.status_code == 401:
            return False, "Pexels API key is invalid (401 Unauthorized)."
        else:
            return False, f"Pexels API returned status {response.status_code}."
    except Exception as e:
        return False, f"Pexels API connection error: {str(e)}"

def check_zernio() -> Tuple[bool, str]:
    """Check if Zernio CLI is available and responsive."""
    if not os.path.exists(ZERNI0):
        # Fallback to which
        import shutil
        z_path = shutil.which("zernio")
        if not z_path:
            return False, f"Zernio CLI not found at {ZERNI0} or in PATH."
    
    try:
        # Run a simple command to check health
        result = subprocess.run(
            [ZERNI0, "accounts:list"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return True, "Zernio CLI is healthy and responsive."
        else:
            return False, f"Zernio CLI error ({result.returncode}): {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Zernio CLI timed out after 15 seconds."
    except Exception as e:
        return False, f"Zernio CLI execution error: {str(e)}"

def main():
    print("=== GalaxyCoils Health Monitor ===")
    
    all_ok = True
    
    print("[1/2] Checking Pexels API...")
    p_ok, p_msg = check_pexels()
    print(f"      {'PASS' if p_ok else 'FAIL'}: {p_msg}")
    if not p_ok:
        all_ok = False
        
    print("[2/2] Checking Zernio CLI...")
    z_ok, z_msg = check_zernio()
    print(f"      {'PASS' if z_ok else 'FAIL'}: {z_msg}")
    if not z_ok:
        all_ok = False
        
    print("=" * 34)
    if all_ok:
        print("RESULT: Infrastructure is HEALTHY.")
        sys.exit(0)
    else:
        print("RESULT: Infrastructure has ISSUES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
