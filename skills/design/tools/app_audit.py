"""Objective UI audit of a running web app (live URL or local server), desktop + phone.

Gates (all must pass for "A: pass"):
  A1 no uncaught JS errors / console errors          A5 tap targets >= 32 px on phone (inline text links exempt)
  A2 no horizontal overflow at 1280 and 390          A6 no visible text smaller than 12 px
  A3 <meta name=viewport> present                    A7 every <img> has alt and loads
  A4 text contrast >= WCAG AA (4.5, or 3 for large)  A8 exactly one <h1> or a labelled main heading, <title> set
Also records brand facts used by brand.py: theme-color, primary button colour, body + heading fonts.

Usage: python app_audit.py OUT_DIR URL [URL ...] [--name NAME] [--wait MS]
Writes OUT_DIR/audit.json and OUT_DIR/<name>-<width>-<n>.png
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WIDTHS = ((1280, 820), (390, 844))

PROBE = r"""
() => {
  const vis = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05;
  };
  const parse = c => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  const lum = c => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const bgOf = el => {
    let base = {r: 255, g: 255, b: 255};
    const stack = [];
    for (let n = el; n; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.backgroundImage && s.backgroundImage !== 'none' && !s.backgroundImage.startsWith('radial-gradient')) return null;
      const c = parse(s.backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 0.99) break; }
    }
    for (let i = stack.length - 1; i >= 0; i--) {
      const c = stack[i];
      base = {r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a)};
    }
    return base;
  };
  const label = el => (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '') +
    ' "' + (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 30) + '"');

  const out = {contrast: [], small_text: [], tap: [], img: [], fonts: {}, heading_fonts: {}};
  const textEls = [...document.querySelectorAll('body *')].filter(el =>
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1) && vis(el));
  for (const el of textEls.slice(0, 1500)) {
    const s = getComputedStyle(el);
    const size = parseFloat(s.fontSize);
    const fam = s.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    const bucket = /^H[1-3]$/.test(el.tagName) ? out.heading_fonts : out.fonts;
    bucket[fam] = (bucket[fam] || 0) + 1;
    if (size < 12 && !el.closest('svg,code,pre,sup,sub')) out.small_text.push(label(el) + ' ' + size + 'px');
    const fg = parse(s.color);
    const bg = bgOf(el);
    if (!fg || !bg || fg.a < 0.3) continue;
    const L1 = lum(fg), L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = size >= 24 || (size >= 18.66 && +s.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) out.contrast.push(label(el) + ' ' + ratio.toFixed(2));
  }
  if (innerWidth < 500) {
    for (const el of document.querySelectorAll('a, button, input, select, textarea, [role=button], [onclick]')) {
      if (!vis(el)) continue;
      if (el.tagName === 'A' && el.closest('p, li, td, span') && getComputedStyle(el).display === 'inline') continue;
      const r = el.getBoundingClientRect();
      if (r.width < 32 || r.height < 32) out.tap.push(label(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    }
  }
  for (const img of document.images) {
    if (!vis(img)) continue;
    if (!img.hasAttribute('alt')) out.img.push('no alt: ' + img.src.slice(-60));
    else if (img.complete && img.naturalWidth === 0) out.img.push('broken: ' + img.src.slice(-60));
  }
  const solid = el => { const c = parse(getComputedStyle(el).backgroundColor); return c && c.a > 0.5 && !(c.r > 245 && c.g > 245 && c.b > 245); };
  const btn = [...document.querySelectorAll('.primary, [class*=primary], button, .btn, a[class*=button]')].find(el => vis(el) && solid(el));
  out.brand = {
    theme_color: (document.querySelector('meta[name=theme-color]') || {}).content || null,
    primary_bg: btn ? getComputedStyle(btn).backgroundColor : null,
    accent_var: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || null,
    body_font: getComputedStyle(document.body).fontFamily,
    title: document.title,
  };
  out.viewport_meta = !!document.querySelector('meta[name=viewport]');
  out.h1 = [...document.querySelectorAll('h1')].filter(vis).length;
  out.overflow = document.documentElement.scrollWidth - innerWidth;
  return out;
}
"""


def gates(results):
    fails = {}
    def add(gate, msg):
        fails.setdefault(gate, []).append(msg)
    for r in results:
        tag = f"{r['url_short']}@{r['width']}"
        if r["errors"]:
            add("A1", f"{tag}: {r['errors'][:2]}")
        if r["probe"]["overflow"] > 1:
            add("A2", f"{tag}: {r['probe']['overflow']}px")
        if not r["probe"]["viewport_meta"]:
            add("A3", tag)
        if r["probe"]["contrast"]:
            add("A4", f"{tag}: {len(r['probe']['contrast'])} e.g. {r['probe']['contrast'][:3]}")
        if r["probe"]["tap"]:
            add("A5", f"{tag}: {len(r['probe']['tap'])} e.g. {r['probe']['tap'][:3]}")
        if r["probe"]["small_text"]:
            add("A6", f"{tag}: {len(r['probe']['small_text'])} e.g. {r['probe']['small_text'][:3]}")
        if r["probe"]["img"]:
            add("A7", f"{tag}: {r['probe']['img'][:3]}")
        if r["probe"]["h1"] != 1 or not r["probe"]["brand"]["title"]:
            add("A8", f"{tag}: h1={r['probe']['h1']} title={bool(r['probe']['brand']['title'])}")
    return fails


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--name", default="app")
    ap.add_argument("--wait", type=int, default=900)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        for width, height in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)[:160]))
            page.on("console", lambda msg: errors.append("console: " + msg.text[:160]) if msg.type == "error" else None)
            for n, url in enumerate(args.urls, 1):
                errors.clear()
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as exc:
                    errors.append(f"navigation: {str(exc)[:120]}")
                page.wait_for_timeout(args.wait)
                shot = out / f"{args.name}-{width}-{n}.png"
                page.screenshot(path=str(shot))
                probe = page.evaluate(PROBE)
                results.append({"url": url, "url_short": url.split("//")[-1][:60], "width": width,
                                "errors": list(errors), "probe": probe, "shot": str(shot)})
            page.close()
        browser.close()
    fails = gates(results)
    report = {"name": args.name, "urls": args.urls, "pass": not fails, "failing_gates": sorted(fails),
              "failures": fails, "results": results}
    (out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{args.name}: {'PASS' if not fails else 'FAIL ' + ','.join(sorted(fails))}")
    for gate, msgs in sorted(fails.items()):
        for msg in msgs[:3]:
            print(f"  {gate} {msg[:220]}")
    brand = results[0]["probe"]["brand"] if results else {}
    print("  brand:", json.dumps(brand, ensure_ascii=False)[:300])
    sys.exit(0)


if __name__ == "__main__":
    main()
