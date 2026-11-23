"""Make a project's guide page: its README laid out for a phone, with the files a home screen needs.

    python guide_page.py --checkout DIR --repo juw12/shiphub --name ShipHub --site docs --url https://juw12.github.io/shiphub/
    python guide_page.py --checkout DIR --repo juw12/projects --path apps/kinibuka --name KiniBuka --site apps/kinibuka/web --url ...

Writes into <checkout>/<site>/: index.html, manifest.webmanifest, sw.js, icons/ (192, 512 and the 180 px
apple-touch-icon: the first letter of the name on the page's own colour).

The page is the README as GitHub renders it (asked from GitHub's Markdown API through `gh`), so it says
nothing the README does not say. Pictures that sit in the site folder are linked from there; the others
and every link to a file point at the repo on GitHub. Run it again after the README changes.
Needs gh and Pillow.
"""
import argparse
import colorsys
import datetime as dt
import hashlib
import html as escape_html
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"

CSS = """
:root{--paper:#fbfaf6;--ink:#1d1c1a;--soft:#5d5a54;--line:#e3dfd5;--card:#ffffff;--accent:ACCENT;--code:#f1eee6}
@media (prefers-color-scheme:dark){:root{--paper:#171614;--ink:#eeebe4;--soft:#a9a49a;--line:#35322d;--card:#201f1c;--accent:ACCENT_DARK;--code:#262420}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:12px;min-height:60px;padding:8px 16px;padding-top:max(8px,env(safe-area-inset-top));background:var(--paper);border-bottom:1px solid var(--line)}
header.bar img{width:36px;height:36px;border-radius:9px;flex:none}
header.bar .name{font-weight:700;font-size:18px;line-height:1.2;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
header.bar .name small{display:block;font-weight:500;font-size:13px;color:var(--soft)}
header.bar a.source{flex:none;display:inline-flex;align-items:center;min-height:48px;padding:0 16px;border:1px solid var(--line);border-radius:24px;background:var(--card);color:var(--ink);font-size:15px;font-weight:600;text-decoration:none}
main{max-width:760px;margin:0 auto;padding:20px 16px 40px}
main img{max-width:100%;height:auto;border-radius:8px}
main h1{font-size:30px;line-height:1.2;margin:24px 0 12px}
main h2{font-size:23px;line-height:1.25;margin:36px 0 12px;padding-top:14px;border-top:1px solid var(--line)}
main h3{font-size:19px;line-height:1.3;margin:26px 0 8px}
main h4{font-size:17px;margin:22px 0 6px}
main p,main li{overflow-wrap:anywhere}
main a{color:var(--accent);text-underline-offset:3px;padding:6px 0}
main p[align=center] a,main li>a:only-child{display:inline-block;padding:12px 3px}
main a:has(>img){display:inline-block;padding:8px 0}
main p[align=center] a:has(>img[width="100%"]){display:block;padding:0}
main ul,main ol{padding-left:24px}
main li{margin:6px 0}
main blockquote{margin:16px 0;padding:4px 16px;border-left:4px solid var(--accent);color:var(--soft)}
main code{font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--code);padding:2px 5px;border-radius:5px;overflow-wrap:anywhere}
main pre{background:var(--code);padding:14px;border-radius:10px;overflow-x:auto;-webkit-overflow-scrolling:touch}
main pre code{background:none;padding:0;overflow-wrap:normal;white-space:pre}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0}
main table{border-collapse:collapse;font-size:15px;min-width:100%}
main th,main td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
main th{background:var(--code)}
main hr{border:0;border-top:1px solid var(--line);margin:28px 0}
main kbd{font:13px ui-monospace,Menlo,monospace;border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:1px 5px}
main details{margin:12px 0}
main summary{cursor:pointer;min-height:44px;display:flex;align-items:center;font-weight:600}
footer{max-width:760px;margin:0 auto;padding:18px 16px calc(28px + env(safe-area-inset-bottom));border-top:1px solid var(--line);color:var(--soft);font-size:14px}
footer a{color:var(--soft)}
"""

SW = """// Keeps the guide readable without a connection: the page and its own files, newest first when online.
const CACHE = 'guide-STAMP';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(['./', 'manifest.webmanifest', 'icons/icon-192.png'])).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== location.origin) return;
  event.respondWith(
    fetch(request).then(answer => {
      const copy = answer.clone();
      caches.open(CACHE).then(cache => cache.put(request, copy));
      return answer;
    }).catch(() => caches.match(request).then(found => found || caches.match('./')))
  );
});
"""


def contrast(first: str, second: str) -> float:
    def luminance(colour):
        parts = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def colours(name: str) -> tuple[str, str]:
    """An accent of the project's own, steady from run to run: readable as link text on the light paper
    (4.5:1 or more, so also under white), and a lighter one that is readable on the dark paper."""
    hue = int(hashlib.sha256(name.lower().encode()).hexdigest()[:6], 16) % 360 / 360
    def hexed(lightness, saturation):
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))
    light = 0.36
    while light > 0.12 and contrast(hexed(light, 0.62), "#fbfaf6") < 4.6:
        light -= 0.01
    dark = 0.70
    while dark < 0.9 and contrast(hexed(dark, 0.60), "#171614") < 4.6:
        dark += 0.01
    return hexed(light, 0.62), hexed(dark, 0.60)


def icon(letter: str, colour: str, size: int, path: Path) -> None:
    picture = Image.new("RGB", (size, size), colour)
    draw = ImageDraw.Draw(picture)
    font = ImageFont.truetype(FONT, int(size * 0.62))
    left, top, right, bottom = draw.textbbox((0, 0), letter, font=font)
    draw.text(((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top), letter, font=font, fill="#ffffff")
    picture.save(path)


def render(readme: Path, repo: str) -> str:
    done = subprocess.run(["gh", "api", "markdown", "-f", "mode=gfm", "-f", "context=" + repo, "-F", "text=@" + str(readme)],
                          capture_output=True, text=True)
    if done.returncode != 0 or "<" not in done.stdout:
        raise SystemExit("GitHub did not render the README: " + (done.stderr or done.stdout)[-400:])
    return done.stdout


def tidy(body: str, repo: str, path: str, site: str, checkout: Path, branch: str) -> str:
    # headings: GitHub wraps each in a div with a link icon; keep the heading and give it the id links point at
    def heading(match):
        level, inner, anchor = match.group(1), match.group(2), match.group(3)
        return '<h%s id="%s">%s</h%s>' % (level, anchor, inner, level)
    body = re.sub(r'<div class="markdown-heading"[^>]*><h([1-6])[^>]*>(.*?)</h\1><a id="user-content-([^"]*)"[^>]*>.*?</a></div>', heading, body, flags=re.S)
    body = body.replace('id="user-content-', 'id="').replace('name="user-content-', 'name="')
    body = re.sub(r'<div class="zeroclipboard-container.*?</div>\s*', "", body, flags=re.S)
    body = re.sub(r'<clipboard-copy.*?</clipboard-copy>', "", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    base = (path + "/") if path else ""
    site_dir = checkout / site

    def source(match):
        attribute, value = match.group(1), match.group(2)
        if re.match(r"(https?:|data:|mailto:|#|//)", value):
            return match.group(0)
        target = (base + value).split("#")[0].split("?")[0]
        parts = []
        for part in target.split("/"):  # fold ../ and ./
            if part == "..":
                parts and parts.pop()
            elif part not in (".", ""):
                parts.append(part)
        target = "/".join(parts)
        local = checkout / target
        if attribute == "src":
            if site and local.is_file() and str(local.resolve()).startswith(str(site_dir.resolve()) + "/"):
                return '%s="%s"' % (attribute, str(local.resolve())[len(str(site_dir.resolve())) + 1:])
            return '%s="https://raw.githubusercontent.com/%s/%s/%s"' % (attribute, repo, branch, target)
        kind = "tree" if local.is_dir() else "blob"
        tail = ("#" + value.split("#", 1)[1]) if "#" in value else ""
        return '%s="https://github.com/%s/%s/%s/%s%s"' % (attribute, repo, kind, branch, target, tail)
    body = re.sub(r'\b(src|href)="([^"]*)"', source, body)
    # GitHub proxies outside pictures through camo; the original address is kept next to it
    body = re.sub(r'src="https://camo\.githubusercontent\.com/[^"]*"([^>]*?)data-canonical-src="([^"]*)"', r'src="\2"\1', body)
    body = re.sub(r"<table", '<div class="scroll"><table', body)
    body = body.replace("</table>", "</table></div>")
    body = re.sub(r'<img(?![^>]*\bloading=)', '<img loading="lazy"', body)
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--path", default="")
    parser.add_argument("--name", required=True)
    parser.add_argument("--tagline", default="")
    parser.add_argument("--site", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--accent", default="")
    args = parser.parse_args()

    checkout = Path(args.checkout)
    readme = checkout / args.path / "README.md"
    site_dir = checkout / args.site
    (site_dir / "icons").mkdir(parents=True, exist_ok=True)
    tagline = args.tagline
    if not tagline:
        asked = subprocess.run(["gh", "api", "repos/" + args.repo, "--jq", ".description // \"\""], capture_output=True, text=True).stdout.strip()
        tagline = re.split(r"(?<=[.!?])\s", asked)[0][:140] if asked and not args.path else ""
    if not tagline:
        raise SystemExit("give --tagline")
    accent, accent_dark = (args.accent, args.accent) if args.accent else colours(args.name)
    body = tidy(render(readme, args.repo), args.repo, args.path, args.site, checkout, args.branch)
    commit = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(readme.relative_to(checkout))], cwd=checkout, capture_output=True, text=True).stdout.strip()
    said = commit or dt.date.today().isoformat()
    name, tag = escape_html.escape(args.name), escape_html.escape(tagline, quote=True)
    source = "https://github.com/%s%s" % (args.repo, ("/tree/%s/%s" % (args.branch, args.path)) if args.path else "")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{name} guide: {tag}</title>
<meta name="description" content="{tag}">
<link rel="canonical" href="{args.url}">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{name}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#fbfaf6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171614" media="(prefers-color-scheme: dark)">
<meta property="og:title" content="{name} guide">
<meta property="og:description" content="{tag}">
<style>{CSS.replace("ACCENT_DARK", accent_dark).replace("ACCENT", accent)}</style>
</head>
<body>
<header class="bar">
<img src="icons/icon-192.png" alt="" width="36" height="36">
<div class="name">{name}<small>Guide</small></div>
<a class="source" href="{source}">GitHub</a>
</header>
<main id="guide">
{body}
</main>
<footer>
This is the {name} guide: the project's README, laid out to read on a phone and kept for when there is no connection.
It is the README of {said}. {name} itself is installed and run the way the guide says; the code is at
<a href="{source}">{source.replace("https://", "")}</a>.
</footer>
<script>
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
</script>
</body>
</html>
"""
    (site_dir / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "name": args.name, "short_name": args.name[:12], "description": tagline, "start_url": "./", "scope": "./",
        "display": "standalone", "background_color": "#fbfaf6", "theme_color": accent,
        "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }
    (site_dir / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stamp = hashlib.sha256(page.encode()).hexdigest()[:10]
    (site_dir / "sw.js").write_text(SW.replace("STAMP", stamp), encoding="utf-8")
    letter = next((c for c in args.name if c.isalnum()), "?").upper()
    for size, file in ((192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")):
        icon(letter, accent, size, site_dir / "icons" / file)
    print("%s: %s (%d KB), accent %s, README of %s" % (args.name, site_dir / "index.html", len(page) // 1024, accent, said))


if __name__ == "__main__":
    main()
