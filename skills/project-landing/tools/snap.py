"""Screenshot URLs to JPEG files at a fixed viewport.

Usage: python snap.py jobs.json
jobs.json: [{"url": ..., "out": ..., "w": 1280, "h": 800, "click": optional CSS selector, "wait": ms}]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

jobs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    for job in jobs:
        page = browser.new_page(viewport={"width": job.get("w", 1280), "height": job.get("h", 800)},
                                device_scale_factor=job.get("scale", 1))
        page.goto(job["url"], wait_until="networkidle", timeout=30000)
        if job.get("click"):
            try:
                page.click(job["click"], timeout=5000)
            except Exception as exc:
                print("click failed", job["click"], str(exc)[:80])
        page.wait_for_timeout(job.get("wait", 600))
        Path(job["out"]).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=job["out"], type="jpeg", quality=88)
        print("saved", job["out"])
        page.close()
    browser.close()
