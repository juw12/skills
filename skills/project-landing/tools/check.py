"""Hard-gate checker for the rebuilt landing pages (rubric G1-G8).

Usage: python check.py OLD_P_DIR NEW_P_DIR
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
MOJIBAKE = ("â€", "Ã©", "Ã¨", "ðŸ", "Â·")
# TODO next to FIXME/HACK is product copy (e.g. "turns TODO/FIXME comments into tasks"), not a placeholder
PLACEHOLDER = re.compile(r"lorem ipsum|\bTODO\b(?!\s*(?:/|,|and|or)\s*FIXME)(?<!FIXME and TODO)|placeholder|undefined|\bNaN\b|\{\{|\}\}")


def links(html):
    return set(re.findall(r'href="(https?://[^"]+)"', html))


def main():
    old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
    slugs = sorted(d.name for d in new_dir.iterdir() if d.is_dir() and (d / "index.html").exists())
    failures = {}

    def fail(slug, gate, msg):
        failures.setdefault(slug, []).append(f"{gate}: {msg}")

    # static gates
    for slug in slugs:
        new = (new_dir / slug / "index.html").read_text(encoding="utf-8")
        old = (old_dir / slug / "index.html").read_text(encoding="utf-8")
        old_cta = re.search(r'<div class="cta">(.*?)</div>', old, re.S)
        must_keep = links(old_cta.group(1)) if old_cta else set()
        missing = must_keep - links(new)
        if missing:
            fail(slug, "G3", f"missing links {sorted(missing)}")
        for tag in ('<link rel="canonical"', 'property="og:image"', 'name="description"', "application/ld+json"):
            if tag in old and tag not in new:
                fail(slug, "G4", f"missing {tag}")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', new, re.S):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                fail(slug, "G4", f"bad JSON-LD {exc}")
        if any(m in new for m in MOJIBAKE):
            fail(slug, "G5", "mojibake sequence present")
        visible = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", new, flags=re.S)
        visible = re.sub(r"<[^>]+>", " ", visible)
        if PLACEHOLDER.search(visible):
            fail(slug, "G6", f"placeholder text: {PLACEHOLDER.search(visible).group(0)}")
        if "prefers-reduced-motion" not in new:
            fail(slug, "G7", "no reduced-motion handling")
        for img in re.findall(r"<img\b[^>]*>", new):
            if 'alt="' not in img:
                fail(slug, "G7", f"img without alt: {img[:80]}")
        sections = len(re.findall(r'<section class="block', new))
        if sections < 5:
            fail(slug, "G8", f"only {sections} content sections")
        empty = re.findall(r'<(?:div|ul|ol) class="(?:bento|grid3|checks|steps[^"]*|faq|related|gallery[^"]*|devices)">\s*</', new)
        if empty:
            fail(slug, "G6", "empty section container")

    # rendered gates
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        for width, height in ((1280, 800), (390, 844)):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            for slug in slugs:
                errors.clear()
                page.goto((new_dir / slug / "index.html").resolve().as_uri(), wait_until="load")
                page.wait_for_timeout(150)
                if errors:
                    fail(slug, "G1", f"{width}px JS errors: {errors[:2]}")
                overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                if overflow > 1:
                    culprit = page.evaluate("""() => { const w = window.innerWidth; const out = [];
                      document.querySelectorAll('body *').forEach(el => { const r = el.getBoundingClientRect();
                        if (r.right > w + 1 && out.length < 3) out.push(el.tagName + '.' + el.className); }); return out; }""")
                    fail(slug, "G2", f"{width}px horizontal overflow {overflow}px {culprit}")
            page.close()
        browser.close()

    report = {"pages": len(slugs), "failing_pages": len(failures), "failures": failures}
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
