#!/usr/bin/env python3
"""Capture clean screenshots for promotional video without browser UI elements"""

import subprocess
import time
import os

def capture_screenshot(url, output_path, width=1920, height=1080, delay=3):
    """Use headless Chrome to capture clean screenshot"""
    cmd = [
        "Google Chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--window-size={},{}".format(width, height),
        "--screenshot={}".format(output_path),
        "--virtual-time-budget=10000",
        url
    ]
    
    try:
        subprocess.run(cmd, timeout=30, check=True)
        print(f"✓ Captured: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to capture {output_path}: {e}")
        return False

# Ensure output directory exists
output_dir = os.path.expanduser("~/workspace/loan-sizer-saas/video/interactions_clean")
os.makedirs(output_dir, exist_ok=True)

base_url = "http://localhost:3456/frontend/index.html"

# Scene 1: Landing page - hero section
print("\n📸 Scene 1: Landing page hero...")
capture_screenshot(
    base_url,
    f"{output_dir}/01_landing_hero.png",
    width=1920,
    height=1080,
    delay=3
)

# Scene 2: Multi-lender analyzer (after clicking Launch Demo)
print("\n📸 Scene 2: Multi-lender analyzer empty...")
# Navigate to analyzer section
capture_screenshot(
    f"{base_url}#multi-lender",
    f"{output_dir}/02_analyzer_empty.png",
    width=1920,
    height=1080,
    delay=3
)

# Scene 3-7 will be captured manually with interactions
print("\n" + "="*50)
print("Clean screenshot capture complete!")
print(f"Output directory: {output_dir}")
print("="*50)
