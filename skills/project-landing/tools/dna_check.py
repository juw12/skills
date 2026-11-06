"""Gate: every page in data.json has complete, unique design DNA.

Checks per slug:
  D1 FONTS entry exists, font family not used by any other slug
  D2 STYLE entry exists, (hero, background, card, heading) combo unique, values valid
  D3 ART emblem exists and is not a copy of another slug's emblem
  D4 COPY headlines exist (at least why/features/band)
  D5 theme assigned explicitly in enrich.THEMES (or slug is meant to be "playful": listed in PLAYFUL_OK)
  D6 (--fonts) every Google Fonts css2 URL answers 200

Usage: python dna_check.py <data.json> [--fonts] [--only slug,slug]
Exit code 1 when anything fails.
"""
import argparse
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design  # noqa: E402
import enrich  # noqa: E402

HEROES = {"center", "split", "split-r", "poster", "editorial"}
BACKGROUNDS = {"dots", "grid", "fine", "lines", "diag", "plus", "waves", "topo", "rings", "stars", "checker", "paper"}
CARDS = {"soft", "outline", "brutal", "flat", "ticket", "pill"}
HEADINGS = {"center", "marker", "left", "upper", "italic", "outline"}
PLAYFUL_OK = {"glow", "hazel", "sortie", "sync", "pips", "fade", "crewcup", "kinibuka", "house-of-articles", "atomize"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--fonts", action="store_true", help="also fetch every css2 URL")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    slugs = list(json.loads(Path(args.data).read_text(encoding="utf-8")))
    focus = [s for s in args.only.split(",") if s] or slugs
    themed = {s for group in enrich.THEMES.values() for s in group} | PLAYFUL_OK
    font_users = Counter(design.FONTS[s][1] for s in slugs if s in design.FONTS)
    combo_users = Counter(tuple(design.STYLE[s]) for s in slugs if s in design.STYLE)
    art_users = Counter(design.ART[s] for s in slugs if s in design.ART)
    problems = []

    for slug in focus:
        font = design.FONTS.get(slug)
        if not font:
            problems.append((slug, "D1", "no FONTS entry"))
        elif font_users[font[1]] > 1:
            problems.append((slug, "D1", f"font {font[1]!r} shared with another page"))
        style = design.STYLE.get(slug)
        if not style:
            problems.append((slug, "D2", "no STYLE entry"))
        else:
            hero, bg, card, heading = style
            bad = [v for v, ok in ((hero, HEROES), (bg, BACKGROUNDS), (card, CARDS), (heading, HEADINGS)) if v not in ok]
            if bad:
                problems.append((slug, "D2", f"unknown STYLE values {bad}"))
            if combo_users[tuple(style)] > 1:
                problems.append((slug, "D2", f"STYLE combo {style} shared with another page"))
        art = design.ART.get(slug)
        if not art:
            problems.append((slug, "D3", "no ART emblem"))
        elif art_users[art] > 1:
            problems.append((slug, "D3", "emblem identical to another page's"))
        copy = design.COPY.get(slug, {})
        missing = [k for k in ("why", "features", "band") if k not in copy]
        if missing:
            problems.append((slug, "D4", f"COPY missing {missing}"))
        if slug not in themed:
            problems.append((slug, "D5", "not in enrich.THEMES (defaults to playful); add it to a theme or PLAYFUL_OK"))
        if args.fonts and font:
            url = f"https://fonts.googleapis.com/css2?family={font[0]}&display=swap"
            try:
                status = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).status
            except Exception as exc:
                status = str(exc)[:60]
            if status != 200:
                problems.append((slug, "D6", f"font URL -> {status}"))

    for slug, gate, msg in problems:
        print(f"FAIL {gate} {slug}: {msg}")
    print(f"dna: {len(focus) - len({p[0] for p in problems})}/{len(focus)} pages complete")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
