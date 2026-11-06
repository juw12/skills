"""Turn one project into a data.json entry: original generated page + README (+ screenshots).

Facts only. Every value comes from:
  - the page the gallery generator wrote at <site>/p/<slug>/index.html (hero copy, CTAs, colours, <head> SEO)
  - the project's README (fetched from GitHub via `gh`, or a local file with --readme)
  - README screenshots (downloaded to state/gallery/<slug>/g*.jpg)
  - optional hand overrides in state/content/<slug>.json (any key replaces the extracted value)

Usage:
  python ingest.py <data.json> <slug> --site <repo clone> [--readme README.md] [--category "Featured"]
                   [--state <state dir>] [--force]

The page must still be in the ORIGINAL generator format. If it was already rebuilt by this skill
(<html class="dna ...">), ingest refuses unless --force is given, because hero copy would then be
read back from our own output.
"""
import argparse
import base64
import html
import io
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_landing import kind_of, pick_checklist, pick_features, platforms_of  # noqa: E402
from extract import extract  # noqa: E402
from repo_facts import parse_source  # noqa: E402


def text_of(fragment):
    fragment = re.sub(r"<svg.*?</svg>", "", fragment or "", flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def first(pattern, source, flags=re.S):
    m = re.search(pattern, source, flags)
    return m.group(1) if m else None


def parse_page(page, slug):
    """Read hero copy, links and colours from an original generator page."""
    out = {}
    head = first(r"<head>(.*?)</head>", page) or ""
    keep = []
    for line in head.strip().splitlines():
        if re.search(r"fonts\.googleapis|fonts\.gstatic|<style|preconnect", line):
            break
        keep.append(line)
    out["head"] = "\n".join(keep).strip()
    out["lang"] = first(r'<html[^>]*lang="([^"]+)"', page) or "en"
    out["name"] = text_of(first(r'<a class="brand"[^>]*>(?:<span class="logo">.*?</span>)?(.*?)</a>', page))
    hero = first(r'<section class="hero[^"]*"[^>]*>(.*?)</section>', page) or ""
    h1 = first(r"<h1[^>]*>(.*?)</h1>", hero) or ""
    out["h1_text"] = text_of(h1)
    out["h1_hl"] = text_of(first(r'<span class="hl">(.*?)</span>', h1)) or None
    out["sub"] = text_of(first(r'<p class="sub">(.*?)</p>', hero))
    out["stickers"] = [text_of(s) for s in re.findall(r'<span class="sticker[^"]*"[^>]*>(.*?)</span>', hero, re.S)]
    pill_html = first(r'<span class="pill">(.*?)</span>\s*<h1', hero) or ""
    out["pill"] = text_of(pill_html)
    status = text_of(first(r'<span class="status">(.*?)</span>', pill_html)) or None
    platforms, pill_status = platforms_of({"pill": text_of(re.sub(r'<span class="status">.*?</span>', "", pill_html, flags=re.S))})
    out["platforms"] = platforms
    out["status"] = status or pill_status
    cta_html = first(r'<div class="cta">(.*?)</div>', hero) or ""
    out["cta"] = [[text_of(label), html.unescape(href)]
                  for href, label in re.findall(r'<a class="btn[^"]*" href="([^"]+)"[^>]*>(.*?)</a>', cta_html, re.S)]
    out["meta"] = text_of(first(r'<div class="meta">(.*?)</div>', hero))
    out["has_shot"] = 'src="shot.jpg"' in hero
    out["frame_label"] = text_of(first(r'<div class="bar">.*?<span>(.*?)</span>', hero)) or f"{slug} · preview"

    links = {}
    readme = first(r'<div class="view-switch".*?<a href="([^"]+)"[^>]*>README</a>', page)
    if readme:
        links["readme"] = html.unescape(readme)
    for label, href in [(c[0], c[1]) for c in out["cta"]]:
        low = label.lower()
        if "source" in low and "source" not in links:
            links["source"] = href
        elif ("live" in low or "open" in low or "play" in low) and "github.com" not in href and "live" not in links:
            links["live"] = href
        elif "download" in low and "download" not in links:
            links["download"] = href
    out["links"] = links

    root = first(r":root\s*\{(.*?)\}", page) or ""
    colours = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,8})", root))
    for key, var, default in (("accent", "accent", "#4f46e5"), ("accent_soft", "accent-soft", "#eef"),
                              ("accent_ink", "accent-ink", "#312e81"), ("paper", "paper", "#fffaf3"),
                              ("ink", "ink", "#1f2330"), ("line", "line", "#ece4d6"), ("dark", "dark", "#1f2330")):
        out[key] = colours.get(var, default)

    features_section = first(r'<section[^>]*id="features"[^>]*>(.*?)</section>', page) or ""
    out["ideas"] = [{"title": text_of(t), "body": text_of(b)}
                    for t, b in re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", features_section, re.S)][:3]
    out["footer_links"] = [[label, v] for label, v in (("README", links.get("readme")), ("Source", links.get("source"))) if v]
    return out


def gh_bytes(endpoint):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("content"):
        return base64.b64decode(payload["content"])
    return None


def fetch_readme(links):
    src = (links.get("readme") or links.get("source") or "").split("#")[0]
    parsed = parse_source(src)
    if not parsed:
        return None, None
    owner, repo, branch, path = parsed
    ref = f"?ref={branch}" if branch else ""
    for name in ("README.md", "readme.md", "Readme.md"):
        file_path = f"{path}/{name}" if path else name
        raw = gh_bytes(f"repos/{owner}/{repo}/contents/{file_path}{ref}")
        if raw:
            return raw.decode("utf-8", errors="replace"), (owner, repo, branch or "HEAD", path)
    return None, None


def download_gallery(images, origin, gallery_dir, limit=4):
    """Save README screenshots as g1.jpg.. (min 500px wide). Returns gallery entries."""
    try:
        from PIL import Image
    except ImportError:
        return []
    if not origin:
        return []
    owner, repo, branch, path = origin
    entries = []
    gallery_dir.mkdir(parents=True, exist_ok=True)
    for img in images:
        src = img["src"]
        if src.startswith("http"):
            if "github.com" in src and "/blob/" in src:
                src = src.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            try:
                import urllib.request
                raw = urllib.request.urlopen(src, timeout=20).read()
            except Exception:
                continue
        else:
            rel = re.sub(r"^\./", "", src)
            file_path = f"{path}/{rel}" if path else rel
            raw = gh_bytes(f"repos/{owner}/{repo}/contents/{file_path}?ref={branch}")
            if not raw:
                continue
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            continue
        if im.width < 500:
            continue
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)))
        name = f"g{len(entries) + 1}.jpg"
        im.save(gallery_dir / name, "JPEG", quality=84, optimize=True)
        entries.append({"file": name, "alt": img.get("alt") or "", "w": im.width, "h": im.height})
        if len(entries) == limit:
            break
    return entries


def related_for(slug, entry, data, limit=3):
    words = set(re.findall(r"[a-z]{4,}", (entry["sub"] + " " + " ".join(entry["platforms"])).lower()))
    scored = []
    for other_slug, other in data.items():
        if other_slug == slug:
            continue
        other_words = set(re.findall(r"[a-z]{4,}", (other.get("sub", "") + " " + " ".join(other.get("platforms", []))).lower()))
        score = len(words & other_words) + (2 if other.get("kind") == entry["kind"] else 0)
        scored.append((score, other_slug))
    scored.sort(key=lambda s: (-s[0], s[1]))
    out = []
    for _, other_slug in scored[:limit]:
        other = data[other_slug]
        out.append({"slug": other_slug, "name": other["name"], "description": other.get("sub", ""),
                    "shot": bool(other.get("has_shot")), "accent": other.get("accent")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("slug")
    ap.add_argument("--site", required=True, help="clone of the <user>.github.io repo")
    ap.add_argument("--readme", help="local README.md instead of fetching from GitHub")
    ap.add_argument("--category", default=None)
    ap.add_argument("--state", default=str(Path(__file__).resolve().parent.parent / "state"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    data_path = Path(args.data)
    data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {}
    state = Path(args.state)
    page_path = Path(args.site) / "p" / args.slug / "index.html"
    page = page_path.read_text(encoding="utf-8-sig")
    if re.search(r'<html[^>]*class="[^"]*\bdna\b', page) and not args.force:
        sys.exit(f"{page_path} was already rebuilt by this skill; use the stored data.json entry or --force.")

    entry = {"slug": args.slug}
    entry.update(parse_page(page, args.slug))
    entry["landing"] = first(r'<link rel="canonical" href="([^"]+)"', page) or f"/p/{args.slug}/"
    entry["category"] = args.category
    entry["kind"] = kind_of({"pill": entry["pill"], "meta": entry["meta"]}, args.category)

    if args.readme:
        md, origin = Path(args.readme).read_text(encoding="utf-8"), None
        parsed = parse_source((entry["links"].get("readme") or "").split("#")[0])
        if parsed:
            origin = (parsed[0], parsed[1], parsed[2] or "HEAD", parsed[3])
    else:
        md, origin = fetch_readme(entry["links"])
    if not md:
        sys.exit("README not found; pass --readme <file>.")
    (state / "readmes").mkdir(parents=True, exist_ok=True)
    (state / "readmes" / f"{args.slug}.md").write_text(md, encoding="utf-8")

    ex = extract(md)
    idea_titles = {i["title"].lower() for i in entry["ideas"]}
    entry["about"] = ex["about"][:4]
    entry["features"] = pick_features(ex["features"], idea_titles)
    entry["checklist"] = pick_checklist(ex["features"])
    entry["steps"] = ex["steps"][:4]
    entry["steps_title"] = ex.get("steps_heading")
    entry["quickstart"] = ex["quickstart"]
    entry["privacy"] = ex["privacy"]
    heading = ex.get("privacy_heading") or ""
    entry["privacy_title"] = heading if re.search(r"privacy|your data|security", heading, re.I) else None
    entry["limits"] = ex["limits"][:6]
    entry["readme_faq"] = ex["faq"][:6]
    entry["gallery"] = download_gallery(ex["images"], origin, state / "gallery" / args.slug)
    entry["tests"] = None
    entry["devices"] = []
    entry["related"] = related_for(args.slug, entry, data)

    override_path = state / "content" / f"{args.slug}.json"
    if override_path.exists():
        entry.update(json.loads(override_path.read_text(encoding="utf-8")))

    data[args.slug] = entry
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in entry.items() if k not in ("head",)}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"\ningested {args.slug} -> {data_path}. Review it, then write state/content/{args.slug}.json "
          "for anything the README extraction got wrong.")


if __name__ == "__main__":
    main()
