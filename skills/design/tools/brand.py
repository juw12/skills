"""Keep a project's landing page on-brand with the app itself.

The APP is the source of truth. From an app audit (app_audit.py audit.json) this reads the app's real accent
(--accent var, else primary button, else theme-color), compares it with the landing page accent, and with
--apply writes accent / accent_soft / accent_ink into the landing data (data.json + content/<slug>.json so
re-ingest keeps it). With --gallery it also adds the audit's desktop screenshots of the live app to the
landing gallery as the next g<N>.jpg files.

Usage: python brand.py <slug> <audit.json> --landing-state <project-landing/state> [--apply] [--gallery]
"""
import argparse
import colorsys
import json
import math
import re
import sys
from pathlib import Path


def hex_of(value):
    if not value:
        return None
    value = value.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h.lower()
    m = re.match(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+))?", value)
    if m:
        if m.group(4) is not None and float(m.group(4)) < 0.5:
            return None
        return "#" + "".join(f"{int(m.group(i)):02x}" for i in (1, 2, 3))
    return None


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def to_hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in c)


def lab(h):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a, b):
    return math.dist(lab(a), lab(b))


def luminance(h):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    return to_hex(tuple(x * (1 - t) + y * t for x, y in zip(rgb(a), rgb(b))))


def ink_for(accent, paper):
    """Darken the accent until it reads as body-text colour on the paper (>= 7:1)."""
    r, g, b = (v / 255 for v in rgb(accent))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    while l > 0.05 and contrast(to_hex(tuple(v * 255 for v in colorsys.hls_to_rgb(h, l, s))), paper) < 7:
        l -= 0.02
    return to_hex(tuple(v * 255 for v in colorsys.hls_to_rgb(h, l, s)))


def app_accent(audit):
    brand = audit["results"][0]["probe"]["brand"]
    for key in ("accent_var", "primary_bg", "theme_color"):
        value = hex_of(brand.get(key))
        if value and not (min(rgb(value)) > 235 or max(rgb(value)) < 25):
            return value, key
    return None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("audit")
    ap.add_argument("--landing-state", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gallery", action="store_true")
    ap.add_argument("--threshold", type=float, default=12.0, help="CIE76 delta-E above which accents differ")
    args = ap.parse_args()

    state = Path(args.landing_state)
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    data_path = state / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    entry = data[args.slug]
    landing_accent = hex_of(entry.get("accent"))
    accent, source = app_accent(audit)
    brand = audit["results"][0]["probe"]["brand"]
    print(f"app accent: {accent} (from {source})  landing accent: {landing_accent}")
    print(f"app fonts: body={brand.get('body_font', '')[:60]!r}  theme-color={brand.get('theme_color')}")
    if not brand.get("theme_color"):
        print("note: app has no <meta name=theme-color>; add one in the app (A-pass suggestion)")
    if not accent:
        print("could not read an accent from the app; leaving the landing page as is")
        return
    distance = delta_e(accent, landing_accent) if landing_accent else 999
    print(f"delta-E {distance:.1f} ({'MISMATCH' if distance > args.threshold else 'on-brand'})")

    paper = entry.get("paper", "#fffaf3")
    proposal = {
        "accent": accent,
        "accent_soft": mix(accent, paper, 0.86),
        "accent_ink": ink_for(accent, paper),
    }
    if contrast(proposal["accent"], "#ffffff") < 3:
        print("warning: app accent is light; white button text on it would fail contrast. "
              "accent_ink is used for text, but check buttons visually.")
    print("proposal:", json.dumps(proposal))

    gallery_entries = []
    if args.gallery:
        from PIL import Image
        gdir = state / "gallery" / args.slug
        gdir.mkdir(parents=True, exist_ok=True)
        existing = list(entry.get("gallery") or [])
        used = {g["file"] for g in existing}
        n = 1
        for r in audit["results"]:
            if r["width"] < 1000:
                continue
            while f"g{n}.jpg" in used:
                n += 1
            name = f"g{n}.jpg"
            im = Image.open(r["shot"]).convert("RGB")
            im.save(gdir / name, "JPEG", quality=84, optimize=True)
            used.add(name)
            gallery_entries.append({"file": name, "alt": f"{entry['name']} app, live (desktop)", "w": im.width, "h": im.height})
        print(f"gallery: +{len(gallery_entries)} live app screenshot(s)")

    if not args.apply:
        print("dry run; re-run with --apply to write the landing data")
        return
    updates = dict(proposal) if distance > args.threshold else {}
    if gallery_entries:
        updates["gallery"] = (entry.get("gallery") or []) + gallery_entries
    if not updates:
        print("nothing to change")
        return
    entry.update(updates)
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    content_path = state / "content" / f"{args.slug}.json"
    content = json.loads(content_path.read_text(encoding="utf-8")) if content_path.exists() else {}
    content.update(updates)
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"applied {sorted(updates)} to {data_path} and {content_path}")


if __name__ == "__main__":
    main()
