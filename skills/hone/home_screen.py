"""Give a page that is already there what a phone's home screen needs: a web manifest, icons and the head tags.

    python home_screen.py --site DIR --page index.html --name Lineup --tagline "..." --background "#f6f3ec" --accent "#c2500f"

Writes manifest.webmanifest and icons/ (192, 512, apple-touch-icon 180: the first letter of the name on the
accent colour) next to the page and adds the tags to its <head>. Leaves the page alone when it already has a manifest.
"""
import argparse
import json
import re
from pathlib import Path

from guide_page import icon


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--page", default="index.html")
    parser.add_argument("--name", required=True)
    parser.add_argument("--tagline", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--accent", required=True)
    parser.add_argument("--theme", default="")
    args = parser.parse_args()
    site = Path(args.site)
    page = site / args.page
    html = page.read_text(encoding="utf-8")
    if 'rel="manifest"' in html:
        raise SystemExit("the page already has a manifest")
    (site / "icons").mkdir(exist_ok=True)
    letter = next((c for c in args.name if c.isalnum()), "?").upper()
    for size, file in ((192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")):
        icon(letter, args.accent, size, site / "icons" / file)
    manifest = {
        "name": args.name, "short_name": args.name[:12], "description": args.tagline,
        "start_url": "./" if args.page == "index.html" else args.page, "scope": "./",
        "display": "standalone", "background_color": args.background, "theme_color": args.accent,
        "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }
    (site / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tags = [
        '<link rel="manifest" href="manifest.webmanifest">',
        '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">',
        '<link rel="icon" type="image/png" href="icons/icon-192.png">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-title" content="%s">' % args.name,
    ]
    if "theme-color" not in html:
        tags.append('<meta name="theme-color" content="%s">' % (args.theme or args.background))
    found = re.search(r"</title>\s*\n?", html, re.I)
    if not found:
        raise SystemExit("the page has no <title>")
    html = html[:found.end()] + "\n".join(tags) + "\n" + html[found.end():]
    page.write_text(html, encoding="utf-8")
    print("%s: tags, manifest and icons written in %s" % (args.name, site))


if __name__ == "__main__":
    main()
