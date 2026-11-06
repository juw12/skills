"""Screenshot a list of URLs (or local files) with system Chrome via Playwright.

Usage: python shoot.py OUT_DIR WIDTH HEIGHT FULLPAGE name=url [name=url ...]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main():
    out_dir = Path(sys.argv[1])
    width = int(sys.argv[2])
    height = int(sys.argv[3])
    full_page = sys.argv[4] == "1"
    targets = [arg.split("=", 1) for arg in sys.argv[5:]]
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        for name, url in targets:
            errors.clear()
            try:
                page.goto(url, wait_until="networkidle", timeout=25000)
            except Exception as exc:
                print(f"{name}: nav issue {str(exc)[:80]}")
            page.wait_for_timeout(500)
            page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading='eager')")
            page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }")
            page.wait_for_timeout(700)
            page.add_style_tag(content="*{transition:none!important;animation:none!important}.reveal{opacity:1!important;transform:none!important}")
            page.screenshot(path=str(out_dir / f"{name}.png"), full_page=full_page)
            overflow = page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1"
            )
            height_px = page.evaluate("document.documentElement.scrollHeight")
            print(f"{name}: ok height={height_px} hscroll={overflow} jsErrors={len(errors)}")
            for err in errors:
                print(f"   err: {err[:160]}")
        browser.close()


if __name__ == "__main__":
    main()
