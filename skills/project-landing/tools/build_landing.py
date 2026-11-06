"""Build rich per-project landing pages for juw12.github.io/p/<slug>/.

Inputs (all facts come from these; nothing is invented):
  - the existing generated page (hero copy, accent colours, CTAs, stickers, idea cards, <head> SEO/JSON-LD)
  - the project's README (about, features, steps, quick start, limits, privacy, FAQ)
  - README screenshots (work/gallery/<slug>/g*.jpg)
  - profile README facts (test-file counts, category)
  - optional hand overrides: content/<slug>.json (any key replaces the extracted value)

Usage: python build_landing.py <data.json> <out_p_dir>
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

E = html.escape

TECHY = re.compile(r"`|\b[\w.-]+/[\w./-]+|\b\w+\.(?:js|ts|py|html|json|ps1|cmd|md|webmanifest|ya?ml|sql|exe)\b|"
                   r"\w+\(\)|\?\w+=|#/|\b(?:iframe|manifest|endpoint|localStorage|sw\.js|npm|pip)\b", re.I)


def first_sentence(text, limit=190):
    text = tidy(text)
    m = re.match(r"(.{25,}?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    if len(s) > limit:
        cut = s[:limit].rsplit(" ", 1)[0].rstrip(",;:-–— ")
        s = cut + "…"
    return s


def tidy(text):
    """Clean README list-item artifacts: bold-label joins (': ,'), backticks, dangling colons."""
    text = text.strip().replace("`", "")
    text = re.sub(r":\s*,\s*", ", ", text)
    text = re.sub(r"\s*:\s*$", ".", text)
    return text


def techiness(text):
    return len(TECHY.findall(text))


GENERIC_TITLES = {"settings", "overview", "dashboard", "client", "assets", "anthropic", "openai", "windows", "android",
                  "mac", "macos", "linux", "iphone", "web", "connect a device", "files", "layout", "structure", "server",
                  "backend", "frontend", "tests", "notes", "license", "anything else"}


def pick_features(features, idea_titles, limit=8):
    scored = []
    for i, f in enumerate(features):
        title, body = f.get("title"), f.get("body", "")
        if not title:
            continue
        if title.lower() in idea_titles:
            continue
        if "`" in title or re.fullmatch(r"[A-Z0-9_]{4,}", title.strip()):
            continue
        title = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200d]", "", title).strip()
        if title.lower() in GENERIC_TITLES:
            continue
        if re.fullmatch(r"[a-z]+(_[a-z]+)+", title):
            title = title.replace("_", " ").capitalize()
        if len(title) > 46 or len(body) < 18:
            continue
        if re.match(r"^v?\d+(\.\d+)+", title) or "→" in title or re.match(r"(?i)^(install|run|option|begin|step|add your|put it|honest|not yet|me |live \()", title):
            continue
        if re.fullmatch(r"[A-Z]{2,}|\w{1,4}", title) or re.fullmatch(r"\S{1,3}(\s*/\s*\S{1,3})+", title):
            continue
        if re.search(r"(?i)\b(memory|gi|env|token|api key|port)\b.*[≥=<>]|\(\d+\.\d+\)$", title):
            continue
        score = 10 - i * 0.08
        score -= 2.5 * techiness(title + " " + body)
        if re.search(r"feature|what you get|what it does|in the box|highlight|about|why|capabil|fitur|apps|discover",
                     f.get("from", ""), re.I):
            score += 2
        if f.get("from") == "h3":
            score -= 1
        scored.append((score, i, {"title": title.strip(), "body": first_sentence(body)}))
    good = [s for s in scored if s[0] > 4]
    good.sort(key=lambda s: (-s[0], s[1]))
    chosen = sorted(good[:limit], key=lambda s: s[1])
    return [c[2] for c in chosen]


def pick_checklist(features, limit=8):
    items = []
    for f in features:
        if f.get("title"):
            continue
        body = f.get("body", "").strip()
        if 18 <= len(body) <= 150 and techiness(body) <= 1:
            items.append(first_sentence(body, 150))
    return items[:limit]


def platforms_of(page):
    pill = page["pill"]
    pill = re.sub(r"(in progress|stable|beta|alpha|archived|experimental)$", "", pill, flags=re.I).strip()
    parts = [p.strip() for p in pill.split("·") if p.strip()]
    status = None
    m = re.search(r"(in progress|stable|beta|alpha|archived|experimental)$", page["pill"], re.I)
    if m:
        status = m.group(1)
    return parts, status


def kind_of(page, category):
    blob = (page["pill"] + " " + page["meta"] + " " + (category or "")).lower()
    if category == "Games" or "unity" in blob or "game" in blob:
        return "game"
    if category == "Engineering" and re.search(r"cfd|fortran|gnuplot|matlab|python", blob):
        return "sim"
    consumer = re.search(r"\bweb\b|windows|android|iphone|\bios\b|macos|desktop|pwa", blob)
    if not consumer and re.search(r"\bcli\b|typescript|sdk|agent|skills|drop-in|python|node|proxy|bot|telegram", blob):
        return "dev"
    return "app"


ICONS = {
    "check": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "warn": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l9.5 16.5h-19z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4.5M12 17.4v.1" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4.5" y="10.5" width="15" height="10" rx="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 10.5V8a4 4 0 018 0v2.5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    "copy": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}


def btn(label, href, cls=""):
    label = re.sub(r"^[^\w(]+\s*", "", label).strip() or label
    icon = ""
    low = label.lower()
    if "try" in low or "play" in low or "live" in low or "open" in low:
        icon = "▶ "
    elif "download" in low:
        icon = "↓ "
    return f'<a class="btn {cls}" href="{E(href)}">{icon}{E(label)}</a>'


def faq_items(d):
    items = []
    platforms = ", ".join(d["platforms"])
    links = d["links"]
    if platforms:
        how = []
        if links.get("live"):
            how.append("try it in the browser with nothing to install")
        if links.get("download"):
            how.append("grab a build from the downloads page")
        tail = f" You can {' or '.join(how)}." if how else ""
        items.append(("What does it run on?", f"{platforms}.{tail}"))
    if d.get("quickstart"):
        items.append(("How do I get it running?",
                      f"The commands in the “{d['quickstart']['heading']}” box above come straight from the README. "
                      "Paste them into a terminal; the README covers options and troubleshooting."))
    elif d.get("steps"):
        s = d["steps"][0]
        items.append(("Where do I start?", f"{(s.get('title') + ': ') if s.get('title') else ''}{s['body']}"))
    if d.get("privacy"):
        items.append(("Where does my data go?", " ".join(first_sentence(p, 220) for p in d["privacy"][:2])))
    for q in d.get("readme_faq", [])[:3]:
        items.append((q["q"], first_sentence(q["a"], 300)))
    if d.get("limits"):
        items.append(("What doesn't it do yet?", " ".join(first_sentence(l, 170) for l in d["limits"][:2])))
    if d.get("status"):
        items.append(("Is it finished?", "Not yet: it's marked “" + d["status"] + "” and still changing. "
                      "The README always has the current state."))
    free = "free" in d["meta"].lower()
    items.append(("Is it free?", ("Yes. " if free else "") + "The source is public on GitHub under the MIT licence."))
    items.append(("Who made it?", "Juwen Lie, an R&D mechanical engineer in Batam, Indonesia, as an independent personal project."))
    return items[:8]


def section_heads(name, kind):
    return {
        "why": ("Why it exists", f"The problem {E(name)} solves."),
        "ideas": ("In short", f"{E(name)} in three ideas."),
        "steps": ("How it works", "From zero to useful."),
        "features": ("What's inside", "Small details, real features." if kind != "game" else "What's in the world."),
        "checklist": ("Working today", "Already built and shipping."),
        "gallery": ("Screens", "See more of it." if kind != "game" else "Take a look around."),
        "quick": ("Run it yourself", "Up and running in a minute."),
        "privacy": ("Your data", "Private by design."),
        "limits": ("Good to know", "Honest limits."),
        "faq": ("Questions", "Good questions."),
        "related": ("Keep exploring", "More from the same workbench."),
    }


sys.path.insert(0, str(Path(__file__).resolve().parent))
import design  # noqa: E402  per-project design DNA

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def nice_date(iso, month_only=False):
    y, m, dd = (int(x) for x in iso[:10].split("-"))
    return f"{MONTHS[m - 1]} {y}" if month_only else f"{dd} {MONTHS[m - 1]} {y}"


SPLIT_THEMES = {"clean", "tech", "blueprint"}
THEME_FONTS = {
    "playful": "family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Inter:wght@400;500;600",
    "arcade": "family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Inter:wght@400;500;600",
    "calm": "family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,500&family=Inter:wght@400;500;600",
    "tech": "family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600",
    "clean": "family=Plus+Jakarta+Sans:wght@500;700;800&family=Inter:wght@400;500;600",
    "blueprint": "family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600",
}


def render(d):
    name = d["name"]
    kind = d["kind"]
    theme = d.get("theme", "playful")
    heads = section_heads(name, kind)
    for section, title in design.COPY.get(d["slug"], {}).items():
        if section in heads:
            heads[section] = (heads[section][0], E(title))
    nav = []
    blocks = {}

    # --- stats strip -------------------------------------------------------
    stats = []
    if d.get("tests"):
        stats.append((str(d["tests"]), "test files run in CI"))
    if d["platforms"]:
        n = len(d["platforms"])
        stats.append((str(n), "platform" + ("s" if n != 1 else "") + ": " + ", ".join(d["platforms"][:5])))
    for extra in d.get("extra_stats", []):
        stats.append((extra[0], extra[1]))
    stats.append(("MIT", "open source licence" + (", free to use" if "free" in d["meta"].lower() else "")))
    stats = stats[:4]
    stats_html = "".join(f'<div class="stat"><b>{E(v)}</b><span>{E(l)}</span></div>' for v, l in stats)

    # --- why --------------------------------------------------------------
    def overlap(a, b):
        wa = set(re.findall(r"\w+", a.lower()))
        wb = set(re.findall(r"\w+", b.lower()))
        return len(wa & wb) / max(1, min(len(wa), len(wb)))
    def good_para(a):
        a = a.strip()
        return (len(a) >= 50 and a[0].isalnum() and re.search(r"[.!?)]$", a)
                and not re.search(r"https?://|\w+\.(?:dev|io|com|app)/|\b(by|as|:)$", a)
                and techiness(a) <= 1)
    if d.get("about_locked"):
        about = list(d.get("about", []))
    else:
        about = [a for a in d.get("about", []) if good_para(a) and overlap(a, d["sub"] + " " + d["h1_text"]) < 0.75]
    if not d.get("about_locked"):
        about = [a for a in about if not any(overlap(a, c["title"] + " " + c["body"]) > 0.7 for c in d.get("ideas", []))]
    if about:
        lead = first_sentence(about[0], 260)
        rest = " ".join(first_sentence(a, 260) for a in about[1:2])
        blocks["why"] = f'''
  <section class="block wrap why reveal" id="why">
    <div class="why-grid">
      <div><div class="kicker">{heads["why"][0]}</div><h2>{heads["why"][1]}</h2></div>
      <div><p class="lead">{E(lead)}</p>{f'<p class="lead-2">{E(rest)}</p>' if rest else ''}</div>
    </div>
  </section>'''

    # --- ideas (hand-written cards from the original page) -----------------
    if d.get("ideas"):
        cards = "".join(
            f'<article class="idea{" dark" if i == 0 else ""}"><span class="tag">{i + 1:02d}</span><h3>{E(c["title"])}</h3><p>{E(c["body"])}</p></article>'
            for i, c in enumerate(d["ideas"][:3]))
        blocks["ideas"] = f'''
  <section class="block wrap reveal" id="ideas">
    <div class="kicker">{heads["ideas"][0]}</div>
    <h2>{heads["ideas"][1]}</h2>
    <div class="grid3">{cards}</div>
  </section>'''

    # --- steps --------------------------------------------------------------
    if len(d.get("steps", [])) >= 2:
        steps = d["steps"][:4]
        items = "".join(
            f'<li><span class="num">{i + 1}</span>{f"<h3>{E(s["title"])}</h3>" if s.get("title") else ""}<p>{E(first_sentence(s["body"], 200))}</p></li>'
            for i, s in enumerate(steps))
        blocks["steps"] = f'''
  <section class="block wrap reveal" id="how">
    <div class="kicker">{heads["steps"][0]}</div>
    <h2>{E(d.get("steps_title") or heads["steps"][1])}</h2>
    <ol class="steps n{len(steps)}">{items}</ol>
  </section>'''
        nav.append(("how", "How it works"))

    # --- features bento -----------------------------------------------------
    feats = d.get("features", [])
    if len(feats) >= 3:
        cells = []
        for i, f in enumerate(feats):
            cls = "cell"
            if i == 0:
                cls += " wide dark"
            elif i == 3 and len(feats) >= 5:
                cls += " accent"
            elif i == len(feats) - 1 and len(feats) % 3 == 2 and len(feats) > 3:
                cls += " wide"
            cells.append(f'<article class="{cls}"><h3>{E(f["title"])}</h3><p>{E(f["body"])}</p></article>')
        blocks["features"] = f'''
  <section class="block wrap reveal" id="features">
    <div class="kicker">{heads["features"][0]}</div>
    <h2>{heads["features"][1]}</h2>
    <div class="bento">{"".join(cells)}</div>
  </section>'''
        nav.append(("features", "Features"))

    # --- checklist ----------------------------------------------------------
    if len(d.get("checklist", [])) >= 3:
        lis = "".join(f'<li><i>{ICONS["check"]}</i><span>{E(c)}</span></li>' for c in d["checklist"])
        blocks["checklist"] = f'''
  <section class="block wrap reveal" id="today">
    <div class="kicker">{heads["checklist"][0]}</div>
    <h2>{heads["checklist"][1]}</h2>
    <ul class="checks">{lis}</ul>
  </section>'''

    # --- devices (per-platform install instructions from the README table) ----
    if d.get("devices"):
        cards = "".join(
            f'<div class="dev"><b>{E(x["device"])}</b><p>{E(first_sentence(x["how"], 200))}</p></div>'
            for x in d["devices"][:6])
        dl = d["links"].get("download") or d["links"].get("live")
        blocks["devices"] = f'''
  <section class="block wrap reveal" id="get">
    <div class="kicker">Get it</div>
    <h2>On every device you own.</h2>
    <div class="devices">{cards}</div>
    {f'<p class="center"><a class="go" href="{E(dl)}">Go to downloads {ICONS["arrow"]}</a></p>' if dl else ""}
  </section>'''
        nav.append(("get", "Get it"))

    # --- gallery ------------------------------------------------------------
    if d.get("gallery"):
        figs = "".join(
            f'<a class="shot" href="{E(g["file"])}"><img src="{E(g["file"])}" alt="{E(g["alt"] or name + " screenshot " + str(i + 1))}" loading="lazy" width="{g["w"]}" height="{g["h"]}">'
            f'{f"<span>{E(g["alt"])}</span>" if g["alt"] else ""}</a>'
            for i, g in enumerate(d["gallery"]))
        blocks["gallery"] = f'''
  <section class="block wrap reveal" id="gallery">
    <div class="kicker">{heads["gallery"][0]}</div>
    <h2>{heads["gallery"][1]}</h2>
    <div class="gallery g{min(len(d["gallery"]), 4)}"{f' style="grid-template-columns:minmax(0,{min(820, max(d["gallery"][0]["w"], 420))}px)"' if len(d["gallery"]) == 1 else ""}>{figs}</div>
  </section>'''
        nav.append(("gallery", "Screens"))

    # --- quick start --------------------------------------------------------
    qs = d.get("quickstart")
    if qs:
        code_lines = []
        for line in qs["code"].splitlines():
            if line.strip().startswith(("#", "REM ", "::")):
                code_lines.append(f'<span class="c">{E(line)}</span>')
            else:
                code_lines.append(f'<span class="p">$</span> {E(line)}')
        side = ""
        if d.get("links", {}).get("readme"):
            side = f'<p class="qs-note">From the README’s “{E(qs["heading"])}” section. Full options, requirements and troubleshooting are there too.</p><a class="go" href="{E(d["links"]["readme"])}">Open the README {ICONS["arrow"]}</a>'
        blocks["quick"] = f'''
  <section class="block wrap reveal" id="run">
    <div class="quick">
      <div class="quick-copy">
        <div class="kicker left">{heads["quick"][0]}</div>
        <h2 class="left">{heads["quick"][1]}</h2>
        {side}
      </div>
      <div class="term" role="region" aria-label="Terminal commands">
        <div class="term-bar"><i></i><i></i><i></i><span>{E(qs["lang"] or "shell")}</span>
          <button class="copy" type="button" data-copy="{E(qs["code"])}">{ICONS["copy"]}<span>Copy</span></button></div>
        <pre><code>{chr(10).join(code_lines)}</code></pre>
      </div>
    </div>
  </section>'''
        nav.append(("run", "Run it"))

    # --- privacy ------------------------------------------------------------
    if d.get("privacy"):
        paras = d["privacy"][:4]
        lis = "".join(f'<li>{E(first_sentence(p, 220))}</li>' for p in paras)
        blocks["privacy"] = f'''
  <section class="block wrap reveal" id="privacy">
    <div class="privacy">
      <div class="lock">{ICONS["lock"]}</div>
      <div><div class="kicker left light">{heads["privacy"][0]}</div><h2 class="left">{E(d.get("privacy_title") or heads["privacy"][1])}</h2>
      <ul>{lis}</ul></div>
    </div>
  </section>'''

    # --- limits -------------------------------------------------------------
    if d.get("limits"):
        lis = "".join(f'<li><i>{ICONS["warn"]}</i><span>{E(first_sentence(l, 200))}</span></li>' for l in d["limits"][:5])
        blocks["limits"] = f'''
  <section class="block wrap reveal" id="limits">
    <div class="limits">
      <div><div class="kicker left">{heads["limits"][0]}</div><h2 class="left">{heads["limits"][1]}</h2>
      <p class="muted">Straight from the README, so you know what you're getting before you try it.</p></div>
      <ul>{lis}</ul>
    </div>
  </section>'''

    # --- under the hood: real stack + git history -------------------------
    stack = d.get("stack") or []
    shipped = d.get("shipped") or []
    repo = d.get("repo") or {}
    hood = d.get("hood") or {}
    if len(stack) >= 2 or shipped:
        groups = {}
        for s in stack:
            groups.setdefault(s["group"], []).append(s["name"])
        rows = "".join(
            f'<div class="sg"><span>{E(g)}</span><div class="chips">{"".join(f"<b class=chip>{E(n)}</b>" for n in names)}</div></div>'
            for g, names in groups.items())
        facts_bits = []
        if repo.get("files"):
            facts_bits.append(f'{repo["files"]} files in {hood["where"]}' if hood.get("where") else f'{repo["files"]} files in the repo')
        if repo.get("commits", 0) >= 10 and repo.get("first"):
            facts_bits.append(f'{repo["commits"]} commits since {nice_date(repo["first"], month_only=True)}')
        if repo.get("last"):
            facts_bits.append(f'last updated {nice_date(repo["last"])}')
        repo_line = f'<p class="repo-line">{E(" · ".join(facts_bits))}.</p>' if facts_bits else ""
        src_link = hood.get("link") or d["links"].get("source") or d["links"].get("readme")
        src_text = hood.get("link_text") or "Browse the code"
        note = f'<p class="hood-note">{E(hood["note"])}</p>' if hood.get("note") else ""
        stack_card = f'''<div class="hood-card">
        <h3>Built with</h3>{rows}{repo_line}{note}
        {f'<a class="go" href="{E(src_link)}">{E(src_text)} {ICONS["arrow"]}</a>' if src_link else ""}
      </div>''' if len(stack) >= 2 else ""
        log_card = ""
        if shipped:
            lis = "".join(f'<li><time datetime="{E(c["date"])}">{E(nice_date(c["date"]))}</time><p>{E(c["msg"])}</p></li>' for c in shipped)
            more = f'<a class="go" href="{E(repo["commits_url"])}">Full history on GitHub {ICONS["arrow"]}</a>' if repo.get("commits_url") else ""
            log_card = f'<div class="hood-card"><h3>Recently shipped</h3><ol class="log">{lis}</ol>{more}</div>'
        solo = " solo" if not (stack_card and log_card) else ""
        blocks["hood"] = f'''
  <section class="block wrap reveal" id="hood">
    <div class="kicker">Under the hood</div>
    <h2>How it's built.</h2>
    <div class="hood{solo}">{stack_card}{log_card}</div>
  </section>'''
        nav.append(("hood", "Built with"))

    # --- faq ----------------------------------------------------------------
    faqs = "".join(
        f'<details{" open" if i == 0 else ""}><summary>{E(q)}</summary><p>{E(a)}</p></details>'
        for i, (q, a) in enumerate(faq_items(d)))
    blocks["faq"] = f'''
  <section class="block wrap reveal" id="faq">
    <div class="kicker">{heads["faq"][0]}</div>
    <h2>{heads["faq"][1]}</h2>
    <div class="faq">{faqs}</div>
  </section>'''
    nav.append(("faq", "FAQ"))

    # --- related ------------------------------------------------------------
    if d.get("related"):
        cards = "".join(
            f'<a class="rel" href="../{E(r["slug"])}/">'
            f'{f"<img src=\"../{E(r["slug"])}/shot.jpg\" alt=\"\" loading=\"lazy\">" if r["shot"] else f"<div class=\"rel-ph\" style=\"background:{E(r["accent"])}\">{E(r["name"][:1])}</div>"}'
            f'<div><b>{E(r["name"])}</b><span>{E(first_sentence(r["description"], 110))}</span></div></a>'
            for r in d["related"])
        blocks["related"] = f'''
  <section class="block wrap reveal" id="more">
    <div class="kicker">{heads["related"][0]}</div>
    <h2>{heads["related"][1]}</h2>
    <div class="related">{cards}</div>
  </section>'''

    order = {
        "app": ["why", "ideas", "steps", "features", "checklist", "gallery", "devices", "quick", "privacy", "limits", "hood", "faq", "related"],
        "dev": ["why", "ideas", "quick", "steps", "features", "checklist", "gallery", "devices", "privacy", "limits", "hood", "faq", "related"],
        "game": ["why", "gallery", "ideas", "features", "steps", "quick", "checklist", "limits", "hood", "faq", "related"],
        "sim": ["why", "gallery", "ideas", "steps", "features", "quick", "checklist", "limits", "hood", "faq", "related"],
    }[kind]
    present = [k for k in order if k in blocks]
    parts = []
    for i, k in enumerate(present):
        html_block = blocks[k]
        if i % 2 == 1:
            html_block = html_block.replace('class="block wrap', 'class="block alt wrap', 1)
        parts.append(html_block)
    body_sections = "".join(parts)

    # --- hero ---------------------------------------------------------------
    def nbh(s):
        return re.sub(r"\b(\w{1,2})-(\w{1,2})\b", "\\1\u2011\\2", s)
    d = dict(d, h1_text=nbh(d["h1_text"]), h1_hl=nbh(d["h1_hl"]) if d.get("h1_hl") else None)
    h1 = E(d["h1_text"])
    if d.get("h1_hl") and d["h1_hl"] in d["h1_text"]:
        hl = E(d["h1_hl"])
        h1 = h1.replace(hl, f'<span class="hl">{hl}<svg viewBox="0 0 200 20" preserveAspectRatio="none" aria-hidden="true"><path d="M2 14 C 40 4, 80 4, 110 11 S 170 18, 198 7" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></span>', 1)
    stickers = "".join(f'<span class="sticker s{i + 1}" aria-hidden="true">{E(s)}</span>' for i, s in enumerate(d["stickers"][:3]))
    ctas = d["cta"]
    hero_btns = "".join(btn(t, h, "primary" if i == 0 else "") for i, (t, h) in enumerate(ctas))
    status = f'<span class="status">{E(d["status"])}</span>' if d.get("status") else ""
    pill = " · ".join(E(p) for p in d["platforms"]) or E(d["pill"])
    if d["has_shot"]:
        showcase = f'''
    <figure class="frame reveal" id="showcase">
      <div class="bar"><i></i><i></i><i></i><span>{E(d["frame_label"])}</span><em>{E(d.get("shot_kind") or ("live demo" if d["links"].get("live") else "screenshot"))}</em></div>
      <img src="shot.jpg" alt="{E(name)} screenshot" width="1280" height="800" fetchpriority="high">
    </figure>'''
    else:
        showcase = ""
    primary_label, primary_href = ctas[0]
    switch = f'''<div class="view-switch" title="Pick how you want to read about {E(name)}">
      <a class="on" href="{E(d["landing"])}" aria-current="page">Landing page</a>
      <a href="{E(d["links"]["readme"])}">README</a>
    </div>''' if d["links"].get("readme") else ""
    nav_html = "".join(f'<a href="#{a}">{E(t)}</a>' for a, t in nav[:4])

    band_btns = "".join(btn(t, h, "primary" if i == 0 else "ghost") for i, (t, h) in enumerate(ctas[:3]))
    footer_links = " · ".join(f'<a href="{E(h)}">{E(t)}</a>' for t, h in d["footer_links"])

    layout = design.hero_layout(d["slug"])
    if not d["has_shot"] and layout in ("split", "split-r"):
        layout = "center"
    hero_cls = {"split": " split", "split-r": " split rev", "poster": " poster", "editorial": " editorial"}.get(layout, "")
    emblem = design.art_svg(d["slug"], name)
    wide = layout in ("poster", "editorial")
    art_inline = "" if wide else emblem
    art_side = emblem if wide else ""
    top_open = '<div class="hero-top">' if wide else ""
    top_close = "</div>" if wide else ""
    if wide:
        stickers = ""
    return f'''<!doctype html>
<html lang="{E(d.get("lang", "en"))}" class="k-{kind} t-{theme} dna {design.html_classes(d["slug"])}">
<head>
{d["head"]}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?{THEME_FONTS[theme]}&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
{design.fonts_link(d["slug"])}
<style>
:root {{
  --accent: {d["accent"]}; --accent-soft: {d["accent_soft"]}; --accent-ink: {d["accent_ink"]};
  --paper: {d["paper"]}; --ink: {d["ink"]}; --muted: #5d6273; --line: {d["line"]}; --card: #fff; --dark: {d["dark"]};
}}
{CSS}
{design.ART_CSS}
{design.DNA_CSS}
html.dna.dna.dna {{ {design.root_vars(d["slug"])} --fd-fallback: system-ui, sans-serif; }}
</style>
<script>document.documentElement.classList.add("js")</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap">
    <a class="brand" href="#top"><span class="logo" aria-hidden="true">{E(name[:1])}</span>{E(name)}</a>
    <nav class="links" aria-label="On this page">{nav_html}</nav>
    {switch}
    {btn(primary_label, primary_href, "primary small")}
  </div>
</header>

<main id="main">
  <section class="hero wrap{hero_cls}" id="top">
    {stickers}
    {top_open}<div class="hero-copy">
      {art_inline}<span class="pill"><span class="dot"></span>{pill}{status}</span>
      <h1>{h1}</h1>
      <p class="sub">{E(d["sub"])}</p>
      <div class="cta">{hero_btns}</div>
      <div class="meta">{E(d["meta"])}</div>
    </div>
    {art_side}{top_close}
    {showcase}
    <div class="stats reveal">{stats_html}</div>
  </section>
{body_sections}

  <div class="wrap">
    <section class="band reveal" aria-label="Get {E(name)}">
      <h2>{E(d.get("band_title") or design.COPY.get(d["slug"], {}).get("band") or ("Try " + name + "." if d["links"].get("live") else "Explore " + name + "."))}</h2>
      <p>{E(d["h1_text"])}</p>
      <div class="cta">{band_btns}</div>
    </section>
  </div>
</main>

<footer class="wrap">
  <div>{E(name)} · made by <a href="https://juwenlie.pages.dev/">Juwen Lie</a></div>
  <div class="foot-links">{footer_links} · <a href="https://juw12.github.io/p/">All projects</a> · <a href="https://github.com/juw12">GitHub profile</a></div>
  <div class="foot-note"><small>An independent personal project. No employer endorsement implied.</small></div>
</footer>
<script>
(function () {{
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var els = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) {{
    els.forEach(function (el) {{ el.classList.add("in"); }});
  }} else {{
    var io = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{ if (e.isIntersecting) {{ e.target.classList.add("in"); io.unobserve(e.target); }} }});
    }}, {{ rootMargin: "0px 0px -8% 0px" }});
    els.forEach(function (el) {{ io.observe(el); }});
  }}
  document.querySelectorAll("button.copy").forEach(function (b) {{
    b.addEventListener("click", function () {{
      var label = b.querySelector("span");
      var done = function () {{ label.textContent = "Copied"; setTimeout(function () {{ label.textContent = "Copy"; }}, 1600); }};
      if (navigator.clipboard) {{ navigator.clipboard.writeText(b.getAttribute("data-copy")).then(done, done); }} else {{ done(); }}
    }});
  }});
}})();
</script>
</body>
</html>
'''


CSS = r"""
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } *, *::before, *::after { animation: none !important; transition: none !important; } }
body {
  margin: 0; font-family: var(--fb); color: var(--ink);
  background-color: var(--paper); background-image: radial-gradient(color-mix(in srgb, var(--ink) 11%, transparent) 1px, transparent 1px);
  background-size: 22px 22px; line-height: 1.6; -webkit-font-smoothing: antialiased;
}
.k-sim body, html.k-sim body {
  background-image: linear-gradient(color-mix(in srgb, var(--accent) 9%, transparent) 1px, transparent 1px),
                    linear-gradient(90deg, color-mix(in srgb, var(--accent) 9%, transparent) 1px, transparent 1px);
  background-size: 28px 28px;
}
html.k-game { --paper: #12131a; --ink: #f3f1ea; --muted: #b3b5c2; --line: #2a2c38; --card: #1b1d27; --dark: #0b0c11; }
html.k-game body { background-image: radial-gradient(color-mix(in srgb, var(--accent) 22%, transparent) 1px, transparent 1px); background-size: 26px 26px; }
a { color: inherit; }
img { max-width: 100%; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; border-radius: 6px; }
.skip { position: absolute; left: -999px; top: 8px; background: var(--ink); color: var(--paper); padding: 8px 14px; border-radius: 8px; z-index: 50; }
.skip:focus { left: 12px; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
h1, h2, h3, .brand, .stat b { font-family: var(--fd); letter-spacing: -0.02em; }

header.top { position: sticky; top: 0; z-index: 20; background: color-mix(in srgb, var(--paper) 86%, transparent);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
header.top .wrap { display: flex; align-items: center; gap: 20px; height: 64px; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 20px; text-decoration: none; white-space: nowrap; }
.logo { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; background: var(--accent);
  color: #fff; font-weight: 800; font-size: 17px; box-shadow: 0 3px 0 var(--accent-ink); }
nav.links { display: flex; gap: 22px; margin-left: auto; font-size: 15px; color: var(--muted); }
nav.links a { text-decoration: none; }
nav.links a:hover { color: var(--ink); }
.view-switch { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; background: var(--card); padding: 3px; font-size: 13px; font-weight: 600; white-space: nowrap; }
.view-switch a { padding: 6px 12px; border-radius: 999px; text-decoration: none; color: var(--muted); }
.view-switch a.on { background: var(--ink); color: var(--paper); }

.btn { display: inline-flex; align-items: center; gap: 8px; justify-content: center; padding: 14px 26px; border-radius: 999px;
  font-weight: 600; font-size: 17px; text-decoration: none; border: 1.5px solid var(--line); background: var(--card); color: var(--ink);
  transition: transform .15s ease, box-shadow .15s ease; white-space: nowrap; }
.btn:hover { transform: translateY(-2px); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 6px 0 var(--accent-ink), 0 14px 30px -10px var(--accent); }
.btn.primary:hover { box-shadow: 0 8px 0 var(--accent-ink), 0 18px 34px -10px var(--accent); }
.btn.small { padding: 9px 18px; font-size: 15px; box-shadow: 0 4px 0 var(--accent-ink); }

.hero { position: relative; text-align: center; padding: 80px 24px 10px; }
.pill { display: inline-flex; align-items: center; gap: 8px; background: var(--card); border: 1px solid var(--line); border-radius: 999px;
  padding: 7px 16px; font-size: 14px; font-weight: 500; flex-wrap: wrap; justify-content: center; }
.pill .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.status { font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 999px; background: var(--accent-soft); color: var(--accent-ink); }
.hero h1 { font-size: clamp(40px, 7.2vw, 90px); line-height: 1.02; margin: 26px auto 22px; max-width: 980px; font-weight: 800; text-wrap: balance; }
.hero h1 .hl { color: var(--accent); position: relative; white-space: nowrap; }
.hero h1 .hl svg { position: absolute; left: 0; right: 0; bottom: -0.16em; width: 100%; height: 0.28em; color: var(--ink); }
.hero p.sub { font-size: clamp(17px, 2vw, 21px); color: var(--muted); max-width: 690px; margin: 0 auto 34px; text-wrap: pretty; }
.cta { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
.meta { margin-top: 20px; font-size: 14px; color: var(--muted); }
.sticker { position: absolute; background: var(--card); border: 2px solid var(--ink); border-radius: 12px; padding: 7px 14px;
  font-weight: 600; font-size: 14px; box-shadow: 4px 4px 0 var(--ink); }
.sticker.s1 { left: 3%; top: 120px; transform: rotate(-8deg); background: var(--accent-soft); color: var(--accent-ink); }
.sticker.s2 { right: 3%; top: 96px; transform: rotate(7deg); }
.sticker.s3 { left: calc(50% + 372px); top: 410px; transform: rotate(-5deg); }
@media (max-width: 1100px) { .sticker.s3 { display: none; } }
html.k-game .sticker.s1 { color: var(--accent-ink); }

.frame { margin: 56px auto 0; max-width: 980px; background: var(--card); border: 2px solid var(--ink); border-radius: 18px; overflow: hidden; box-shadow: 10px 10px 0 var(--ink); }
.frame .bar { display: flex; align-items: center; gap: 7px; padding: 11px 16px; border-bottom: 2px solid var(--ink); font-size: 13px; font-weight: 600; background: var(--paper); }
.frame .bar i { width: 11px; height: 11px; border-radius: 50%; border: 1.5px solid var(--ink); display: inline-block; }
.frame .bar i:first-child { background: var(--accent); }
.frame .bar span { margin-left: 8px; }
.frame .bar em { margin-left: auto; font-style: normal; color: var(--muted); font-weight: 500; }
.frame img { display: block; width: 100%; height: auto; }

.stats { display: flex; flex-wrap: wrap; justify-content: center; gap: 14px; max-width: 980px; margin: 44px auto 0; text-align: left; }
.stats .stat { flex: 1 1 200px; max-width: 300px; }
.stat { background: var(--card); border: 1.5px solid var(--line); border-radius: 16px; padding: 16px 18px; display: flex; gap: 12px; align-items: center; }
.stat b { font-size: 30px; color: var(--accent-ink); line-height: 1; white-space: nowrap; }
html.k-game .stat b { color: var(--accent); }
.stat span { font-size: 13.5px; color: var(--muted); line-height: 1.35; }

section.block { padding-top: 104px; }
.kicker { text-align: center; font-size: 13px; font-weight: 700; letter-spacing: .14em; color: var(--accent-ink); text-transform: uppercase; }
html.k-game .kicker { color: var(--accent); }
.kicker.left { text-align: left; }
.kicker.light { color: color-mix(in srgb, var(--accent) 70%, #fff); }
section.block h2 { text-align: center; font-size: clamp(32px, 4.6vw, 54px); margin: 10px 0 44px; line-height: 1.08; text-wrap: balance; }
section.block h2.left { text-align: left; margin-bottom: 18px; }
.muted { color: var(--muted); }

.why-grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 48px; align-items: start; border-top: 2px solid var(--ink); padding-top: 34px; }
.why-grid .kicker { text-align: left; }
.why-grid h2 { text-align: left !important; margin: 10px 0 0 !important; font-size: clamp(30px, 3.8vw, 44px) !important; }
.lead { font-family: var(--fd); font-size: clamp(22px, 2.5vw, 30px); line-height: 1.3; margin: 0; font-weight: 600; letter-spacing: -0.01em; }
.lead-2 { color: var(--muted); font-size: 18px; margin: 18px 0 0; }

.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.idea { background: var(--card); border: 1.5px solid var(--line); border-radius: 20px; padding: 28px; }
.idea .tag { font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--accent-ink); }
.idea h3 { font-size: 24px; margin: 10px 0 8px; line-height: 1.15; }
.idea p { margin: 0; color: var(--muted); }
.idea.dark { background: var(--dark); color: #fff; border-color: var(--dark); }
.idea.dark p { color: #c9ccd6; }
.idea.dark .tag { color: var(--accent); }

.steps { list-style: none; padding: 0; margin: 0; display: grid; gap: 18px; counter-reset: s; position: relative; }
.steps.n2 { grid-template-columns: repeat(2, 1fr); } .steps.n3 { grid-template-columns: repeat(3, 1fr); } .steps.n4 { grid-template-columns: repeat(4, 1fr); }
.steps li { background: var(--card); border: 1.5px solid var(--line); border-radius: 20px; padding: 26px 24px; position: relative; }
.steps li:not(:last-child)::after { content: ""; position: absolute; top: 44px; right: -19px; width: 20px; height: 2px; background: var(--ink); }
.steps .num { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; font-weight: 800; background: var(--accent);
  color: #fff; font-family: var(--fd); box-shadow: 0 4px 0 var(--accent-ink); margin-bottom: 16px; font-size: 18px; }
.steps h3 { font-size: 20px; margin: 0 0 6px; line-height: 1.2; }
.steps p { margin: 0; color: var(--muted); font-size: 15.5px; }

.bento { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.cell { background: var(--card); border: 1.5px solid var(--line); border-radius: 22px; padding: 26px 26px 28px; position: relative; overflow: hidden; }
.cell::before { content: ""; display: block; width: 28px; height: 6px; border-radius: 6px; background: var(--accent); margin-bottom: 18px; }
.cell h3 { font-size: 22px; margin: 0 0 8px; line-height: 1.15; }
.cell p { margin: 0; color: var(--muted); }
.cell.wide { grid-column: span 2; }
.cell.dark { background: var(--dark); color: #fff; border-color: var(--dark); }
.cell.dark h3 { font-size: 30px; }
.cell.dark p { color: #c9ccd6; font-size: 17px; max-width: 560px; }
.cell.accent { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 6px 0 var(--accent-ink); }
.cell.accent::before { background: #fff; }
.cell.accent p { color: rgba(255,255,255,.9); }

.checks { list-style: none; padding: 0; margin: 0 auto; max-width: 900px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px; }
.checks li { display: flex; gap: 12px; align-items: flex-start; background: var(--card); border: 1.5px solid var(--line); border-radius: 14px; padding: 14px 16px; }
.checks i { flex: none; width: 26px; height: 26px; border-radius: 8px; background: var(--accent-soft); color: var(--accent-ink); display: grid; place-items: center; }
.checks svg, .limits svg { width: 18px; height: 18px; }

.gallery { display: grid; gap: 18px; }
.gallery.g1 { grid-template-columns: minmax(0, 820px); justify-content: center; }
.gallery.g2 { grid-template-columns: 1fr 1fr; } .gallery.g3 { grid-template-columns: repeat(3, 1fr); } .gallery.g4 { grid-template-columns: repeat(3, 1fr); }
.gallery.g4 .shot:first-child { grid-column: span 2; grid-row: span 2; }
.shot { display: block; position: relative; border: 2px solid var(--ink); border-radius: 16px; overflow: hidden; background: var(--card); box-shadow: 6px 6px 0 var(--ink); transition: transform .15s ease; }
.shot:hover { transform: translate(-2px, -2px); }
.shot img { display: block; width: 100%; height: 100%; object-fit: cover; aspect-ratio: 16 / 10; }
.gallery.g1 .shot img { aspect-ratio: auto; object-fit: contain; }
.shot span { position: absolute; left: 10px; bottom: 10px; background: var(--card); border: 1.5px solid var(--ink); border-radius: 999px; padding: 3px 10px; font-size: 12.5px; font-weight: 600; }

.quick { display: grid; grid-template-columns: 0.9fr 1.3fr; gap: 40px; align-items: center; }
.qs-note { color: var(--muted); margin: 0 0 16px; }
.go { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; color: var(--accent-ink); text-decoration: none; }
html.k-game .go { color: var(--accent); }
.go svg { width: 18px; height: 18px; }
.go:hover { text-decoration: underline; }
.term { background: #15161d; color: #e9e9ef; border-radius: 16px; border: 2px solid var(--ink); box-shadow: 8px 8px 0 var(--accent); overflow: hidden; min-width: 0; }
.term-bar { display: flex; align-items: center; gap: 7px; padding: 10px 14px; background: #1f2029; font-size: 12.5px; color: #9ea0ad; }
.term-bar i { width: 10px; height: 10px; border-radius: 50%; background: #3a3c48; }
.term-bar i:first-child { background: var(--accent); }
.term-bar span { margin-left: 8px; font-family: "JetBrains Mono", monospace; }
.copy { margin-left: auto; display: inline-flex; gap: 6px; align-items: center; background: #2b2d39; color: #e9e9ef; border: 0; border-radius: 8px; padding: 5px 10px; font: 600 12.5px Inter, sans-serif; cursor: pointer; }
.copy svg { width: 14px; height: 14px; }
.term pre { margin: 0; padding: 18px 20px 20px; overflow-x: auto; font: 14px/1.75 "JetBrains Mono", ui-monospace, monospace; }
.term .p { color: var(--accent); user-select: none; }
.term .c { color: #7d8091; }

.privacy { display: grid; grid-template-columns: auto 1fr; gap: 28px; background: var(--dark); color: #fff; border-radius: 28px; padding: 44px; }
.privacy .lock { width: 64px; height: 64px; border-radius: 18px; background: var(--accent); display: grid; place-items: center; color: #fff; box-shadow: 0 5px 0 var(--accent-ink); }
.privacy .lock svg { width: 32px; height: 32px; }
.privacy h2 { color: #fff; }
.privacy ul { margin: 0; padding-left: 20px; color: #d3d5de; display: grid; gap: 8px; }

.limits { display: grid; grid-template-columns: 0.8fr 1.2fr; gap: 40px; align-items: start; }
.limits ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.limits li { display: flex; gap: 12px; align-items: flex-start; background: var(--card); border: 1.5px dashed color-mix(in srgb, var(--ink) 30%, transparent); border-radius: 14px; padding: 14px 16px; }
.limits i { flex: none; color: #b7791f; margin-top: 2px; }

.devices { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
.dev { background: var(--card); border: 1.5px solid var(--line); border-top: 5px solid var(--accent); border-radius: 16px; padding: 18px 18px 20px; }
.dev b { font-family: var(--fd); font-size: 18px; display: block; margin-bottom: 6px; }
.dev p { margin: 0; color: var(--muted); font-size: 14.5px; }
.center { text-align: center; margin-top: 26px; }
.faq { max-width: 780px; margin: 0 auto; }
.faq details { background: var(--card); border: 1.5px solid var(--line); border-radius: 16px; padding: 18px 22px; margin-bottom: 12px; }
.faq summary { cursor: pointer; font-weight: 600; font-size: 17px; list-style: none; display: flex; justify-content: space-between; gap: 16px; }
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after { content: "+"; color: var(--accent-ink); font-weight: 700; font-size: 20px; line-height: 1; }
html.k-game .faq summary::after { color: var(--accent); }
.faq details[open] summary::after { content: "\2212"; }
.faq details p { margin: 10px 0 0; color: var(--muted); }

.related { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.rel { display: block; background: var(--card); border: 1.5px solid var(--line); border-radius: 18px; overflow: hidden; text-decoration: none; transition: transform .15s ease, box-shadow .15s ease; }
.rel:hover { transform: translateY(-3px); box-shadow: 0 12px 30px -16px rgba(0,0,0,.35); }
.rel img, .rel-ph { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-bottom: 1.5px solid var(--line); }
.rel-ph { display: grid; place-items: center; color: #fff; font: 800 44px var(--fd); }
.rel div { padding: 14px 16px 18px; }
.rel b { display: block; font-family: var(--fd); font-size: 19px; }
.rel span { font-size: 14px; color: var(--muted); }

.band { margin: 120px auto 0; border-radius: 28px; background: var(--accent); color: #fff; text-align: center; padding: 72px 24px; box-shadow: 0 8px 0 var(--accent-ink); }
.band h2 { font-size: clamp(36px, 5vw, 60px); margin: 0 0 10px; }
.band p { margin: 0 auto 30px; font-size: 18px; opacity: .93; max-width: 640px; }
.band .btn { border-color: #fff; }
.band .btn.primary { background: #fff; color: var(--accent-ink); border-color: #fff; box-shadow: 0 6px 0 rgba(0,0,0,.18); }
.band .btn.ghost { background: transparent; color: #fff; }

footer { padding: 46px 0 60px; text-align: center; color: var(--muted); font-size: 14px; }
footer a { text-decoration: none; }
footer a:hover { color: var(--ink); text-decoration: underline; }
.foot-links, .foot-note { margin-top: 10px; }

.js .reveal { opacity: 0; transform: translateY(18px); transition: opacity .6s ease, transform .6s ease; }
.js .reveal.in { opacity: 1; transform: none; }


/* ---------- theme systems ---------- */
:root { --fd: "Bricolage Grotesque", Inter, sans-serif; --fb: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }

/* under the hood */
.hood { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; align-items: start; }
.hood.solo { grid-template-columns: minmax(0, 860px); justify-content: center; }
.hood-card { background: var(--card); border: 1.5px solid var(--line); border-radius: 20px; padding: 26px 28px; min-width: 0; }
.hood-card h3 { margin: 0 0 14px; font-size: 21px; }
.sg { display: flex; gap: 14px; align-items: baseline; padding: 11px 0; border-top: 1px dashed var(--line); }
.hood-card h3 + .sg { border-top: 0; }
.hood-note { margin: 12px 0 0; font-size: 14.5px; line-height: 1.55; color: var(--muted); }
.sg > span { width: 96px; flex: none; font: 600 11.5px "JetBrains Mono", monospace; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 14px; font-weight: 600; padding: 4px 12px; border-radius: 999px; background: var(--accent-soft); color: var(--accent-ink); }
html.k-game .chip, html.t-blueprint .chip { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--ink); }
.repo-line { margin: 16px 0 12px; font-size: 14px; color: var(--muted); }
.log { list-style: none; margin: 0 0 14px; padding: 0; }
.log li { position: relative; padding: 0 0 16px 28px; }
.log li::before { content: ""; position: absolute; left: 4px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.log li:not(:last-child)::after { content: ""; position: absolute; left: 8px; top: 22px; bottom: 2px; width: 2px; background: var(--line); }
.log time { font: 600 12.5px "JetBrains Mono", monospace; color: var(--muted); }
.log p { margin: 2px 0 0; font-size: 15px; line-height: 1.45; overflow-wrap: anywhere; }

/* split hero (clean / tech / blueprint) */
.hero.split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.08fr); gap: 52px; align-items: center; text-align: left; padding-top: 72px; max-width: 1280px; }
.hero.split h1 { font-size: clamp(38px, 4.9vw, 64px); margin: 22px 0 18px; max-width: none; }
.hero.split p.sub { margin: 0 0 30px; }
.hero.split .cta { justify-content: flex-start; }
.hero.split .frame { margin: 0; max-width: none; }
.hero.split .stats { grid-column: 1 / -1; margin: 40px 0 0; max-width: none; justify-content: flex-start; }
.hero.split .sticker { display: none; }

/* calm: serif, soft, warm */
html.t-calm { --fd: "Fraunces", Georgia, serif; }
html.t-calm body { background-image: radial-gradient(60rem 40rem at 90% -10%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%),
  radial-gradient(48rem 34rem at -10% 25%, color-mix(in srgb, var(--accent) 9%, transparent), transparent 70%); background-size: auto; background-repeat: no-repeat; }
html.t-calm h1, html.t-calm h2, html.t-calm h3 { font-weight: 600; letter-spacing: -0.015em; }
html.t-calm .hero h1 { font-weight: 500; }
html.t-calm .hero h1 .hl { font-style: italic; }
html.t-calm .hero h1 .hl svg { color: var(--accent); opacity: .35; }
html.t-calm .kicker { text-transform: none; letter-spacing: 0; font: italic 500 19px var(--fd); }
html.t-calm .sticker { display: none; }
html.t-calm .logo, html.t-calm .steps .num { border-radius: 50%; box-shadow: none; }
html.t-calm .btn.primary { box-shadow: 0 12px 26px -12px var(--accent); }
html.t-calm .btn.small { box-shadow: none; }
html.t-calm .frame, html.t-calm .shot, html.t-calm .term { border: 0; border-radius: 26px; box-shadow: 0 0 0 1px rgba(0,0,0,.06), 0 40px 70px -36px rgba(70,45,20,.45); }
html.t-calm .frame .bar { border-bottom: 1px solid var(--line); }
html.t-calm .frame .bar i { border: 0; background: #ddd5c9; }
html.t-calm .shot span { border: 0; }
html.t-calm :is(.idea, .cell, .steps li, .checks li, .faq details, .stat, .dev, .rel, .limits li, .hood-card) { border-color: transparent; border-radius: 26px;
  box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 14px 34px -20px rgba(70,45,20,.3); }
html.t-calm .cell.accent, html.t-calm .band { box-shadow: none; }
html.t-calm .band { border-radius: 36px; }
html.t-calm .why-grid { border-top: 1px solid var(--line); }
html.t-calm .steps li::after { display: none; }

/* tech: grotesk + mono, grid paper, sharp */
html.t-tech { --fd: "Space Grotesk", Inter, sans-serif; }
html.t-tech body { background-image: linear-gradient(color-mix(in srgb, var(--ink) 6%, transparent) 1px, transparent 1px),
  linear-gradient(90deg, color-mix(in srgb, var(--ink) 6%, transparent) 1px, transparent 1px); background-size: 44px 44px; }
html.t-tech .kicker { font: 600 13px "JetBrains Mono", monospace; letter-spacing: 0; text-transform: none; }
html.t-tech .kicker::before { content: "// "; opacity: .55; }
html.t-tech .hero h1 { font-weight: 700; letter-spacing: -0.04em; }
html.t-tech .hero h1 .hl svg { display: none; }
html.t-tech .hero h1::after { content: "_"; color: var(--accent); margin-left: .04em; animation: caret 1.1s steps(1) infinite; }
@keyframes caret { 50% { opacity: 0; } }
html.t-tech :is(.idea, .cell, .steps li, .checks li, .faq details, .stat, .dev, .rel, .limits li, .hood-card, .pill, .view-switch, .view-switch a, .status, .chip) { border-radius: 8px; }
html.t-tech .btn { border-radius: 8px; }
html.t-tech .btn.primary { box-shadow: 4px 4px 0 var(--ink); }
html.t-tech .btn.small { box-shadow: 3px 3px 0 var(--ink); }
html.t-tech .logo, html.t-tech .steps .num { border-radius: 8px; box-shadow: none; font-family: "JetBrains Mono", monospace; }
html.t-tech .frame { border: 1px solid var(--ink); border-radius: 10px; box-shadow: 0 40px 80px -40px rgba(0,0,0,.5); }
html.t-tech .frame .bar { border-bottom: 1px solid var(--line); font-family: "JetBrains Mono", monospace; font-weight: 500; }
html.t-tech .shot { border-width: 1px; border-radius: 8px; box-shadow: none; }
html.t-tech .term { border: 1px solid #000; border-radius: 10px; box-shadow: 0 30px 60px -30px rgba(0,0,0,.55); }
html.t-tech .stat b { font-family: "JetBrains Mono", monospace; letter-spacing: -0.03em; }
html.t-tech .cell::before { width: 18px; height: 3px; border-radius: 0; }
html.t-tech .band { border-radius: 14px; background: var(--dark); box-shadow: 8px 8px 0 var(--accent); }
html.t-tech .band .btn.primary { background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: none; }
html.t-tech .why-grid { border-top: 1px dashed color-mix(in srgb, var(--ink) 40%, transparent); }

/* clean: white, product-grade, alternating bands */
html.t-clean { --fd: "Plus Jakarta Sans", Inter, sans-serif; --paper: #ffffff; --line: #e6e8ee; }
html.t-clean body { background-image: none; }
html.t-clean section.block.alt { background: #f5f6f9; box-shadow: 0 0 0 100vmax #f5f6f9; clip-path: inset(0 -100vmax); padding-bottom: 96px; }
html.t-clean .hero h1 { font-weight: 800; letter-spacing: -0.035em; }
html.t-clean .hero h1 .hl svg { display: none; }
html.t-clean .hero h1 .hl { background: linear-gradient(transparent 70%, var(--accent-soft) 70%); }
html.t-clean .sticker { display: none; }
html.t-clean .logo { border-radius: 9px; box-shadow: none; }
html.t-clean .btn { border-radius: 10px; }
html.t-clean .btn.primary { box-shadow: 0 10px 24px -10px var(--accent); }
html.t-clean .btn.small { box-shadow: none; }
html.t-clean :is(.idea, .cell, .steps li, .checks li, .faq details, .stat, .dev, .rel, .limits li, .hood-card) { border: 1px solid var(--line); border-radius: 16px; box-shadow: 0 1px 2px rgba(16,24,40,.05); }
html.t-clean .idea.dark, html.t-clean .cell.dark { border-color: var(--dark); }
html.t-clean .cell.accent { box-shadow: none; }
html.t-clean .frame { border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 50px 90px -40px rgba(16,24,40,.35); }
html.t-clean .frame .bar { border-bottom: 1px solid var(--line); background: #f8f9fb; }
html.t-clean .frame .bar i { border: 0; background: #dcdfe6; }
html.t-clean .shot { border: 1px solid var(--line); box-shadow: 0 24px 48px -28px rgba(16,24,40,.35); }
html.t-clean .shot span { border-width: 1px; }
html.t-clean .term { border: 0; box-shadow: 0 30px 60px -30px rgba(16,24,40,.55); }
html.t-clean .why-grid { border-top: 0; }
html.t-clean .steps .num { border-radius: 10px; box-shadow: none; }
html.t-clean .steps li::after { display: none; }
html.t-clean .band { border-radius: 22px; box-shadow: none; background: linear-gradient(135deg, var(--accent), var(--accent-ink)); }

/* blueprint: engineering drawing, navy + plex */
html.t-blueprint { --fd: "IBM Plex Sans", Inter, sans-serif; --fb: "IBM Plex Sans", Inter, sans-serif;
  --paper: #0c1a2b; --ink: #e5eef8; --muted: #9db1c7; --line: #223a54; --card: #10233a; --dark: #07111d; }
html.t-blueprint body { background-image: linear-gradient(rgba(120,170,230,.10) 1px, transparent 1px), linear-gradient(90deg, rgba(120,170,230,.10) 1px, transparent 1px),
  linear-gradient(rgba(120,170,230,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(120,170,230,.045) 1px, transparent 1px);
  background-size: 120px 120px, 120px 120px, 24px 24px, 24px 24px; }
html.t-blueprint :is(.kicker, .stat b, .go, .idea .tag, .faq summary::after, .steps .num) { color: var(--accent); }
html.t-blueprint .kicker, html.t-blueprint .stat b, html.t-blueprint .sg > span { font-family: "IBM Plex Mono", monospace; }
html.t-blueprint .kicker { letter-spacing: .08em; }
html.t-blueprint .hero h1 { font-weight: 600; letter-spacing: -0.03em; }
html.t-blueprint .hero h1 .hl svg { display: none; }
html.t-blueprint .hero h1 .hl { color: var(--accent); }
html.t-blueprint :is(.idea, .cell, .steps li, .checks li, .faq details, .stat, .dev, .rel, .limits li, .hood-card, .pill, .view-switch) { border: 1px solid var(--line); border-radius: 4px; box-shadow: none; }
html.t-blueprint .btn { border-radius: 4px; }
html.t-blueprint .btn.primary, html.t-blueprint .btn.small { box-shadow: none; }
html.t-blueprint .logo { border-radius: 4px; box-shadow: none; }
html.t-blueprint .steps .num { background: transparent; border: 1px solid var(--accent); box-shadow: none; border-radius: 4px; font-family: "IBM Plex Mono", monospace; }
html.t-blueprint .steps li::after { background: var(--accent); }
html.t-blueprint .frame { border: 1px solid var(--accent); border-radius: 4px; box-shadow: 0 0 0 8px color-mix(in srgb, var(--accent) 12%, transparent); }
html.t-blueprint .frame .bar { border-bottom: 1px solid var(--line); background: var(--dark); font-family: "IBM Plex Mono", monospace; }
html.t-blueprint .frame .bar i { border-color: var(--muted); }
html.t-blueprint .shot { border: 1px solid var(--accent); border-radius: 4px; box-shadow: none; }
html.t-blueprint .shot span { border-width: 1px; }
html.t-blueprint .term { border: 1px solid var(--line); border-radius: 4px; box-shadow: none; }
html.t-blueprint .sticker { display: none; }
html.t-blueprint .why-grid { border-top: 1px solid var(--accent); }
html.t-blueprint .cell.accent { box-shadow: none; }
html.t-blueprint .band { background: transparent; border: 1px solid var(--accent); border-radius: 4px; box-shadow: inset 0 0 0 8px color-mix(in srgb, var(--accent) 10%, transparent); }
html.t-blueprint .band .btn.primary { background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: none; }
html.t-blueprint .status { color: var(--ink); background: color-mix(in srgb, var(--accent) 30%, transparent); }
html.t-blueprint .checks i { color: var(--accent); background: color-mix(in srgb, var(--accent) 18%, transparent); }

/* arcade: games, dark with neon glow */
html.t-arcade .hero::before { content: ""; position: absolute; left: 50%; top: -60px; width: min(1400px, 140vw); height: 900px; transform: translateX(-50%);
  background: radial-gradient(45% 45% at 50% 45%, color-mix(in srgb, var(--accent) 34%, transparent), transparent 72%); z-index: -1; pointer-events: none; }
html.t-arcade .hero { isolation: isolate; }
html.t-arcade main { overflow-x: clip; }
html.t-arcade .hero h1 { text-shadow: 0 0 44px color-mix(in srgb, var(--accent) 45%, transparent); }
html.t-arcade .kicker { letter-spacing: .32em; }
html.t-arcade .frame { max-width: 1080px; border: 2px solid var(--accent); box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 18%, transparent), 0 50px 130px -30px color-mix(in srgb, var(--accent) 60%, transparent); }
html.t-arcade .frame .bar { border-bottom-color: var(--accent); }
html.t-arcade .shot { border-color: color-mix(in srgb, var(--accent) 70%, #000); box-shadow: 0 24px 60px -24px color-mix(in srgb, var(--accent) 65%, transparent); }
html.t-arcade .band { box-shadow: 0 0 80px -10px color-mix(in srgb, var(--accent) 60%, transparent); }

@media (max-width: 980px) {
  .hero.split { grid-template-columns: 1fr; text-align: center; gap: 36px; }
  .hero.split .cta, .hero.split .stats { justify-content: center; }
  .hero.split p.sub { margin: 0 auto 30px; }
}
@media (max-width: 860px) {
  .hood { grid-template-columns: 1fr; }
  .sg { flex-direction: column; gap: 6px; }
  .sg > span { width: auto; }
  html.t-clean section.block.alt { padding-bottom: 72px; }
}

@media (max-width: 980px) {
  nav.links { display: none; }
  .view-switch { margin-left: auto; }
  .steps.n4 { grid-template-columns: repeat(2, 1fr); }
  .steps li::after { display: none; }
}
@media (max-width: 860px) {
  .sticker { display: none; }
  .grid3, .bento, .related, .steps.n2, .steps.n3, .steps.n4, .checks, .quick, .limits, .why-grid, .gallery.g2, .gallery.g3, .gallery.g4 { grid-template-columns: 1fr; }
  .cell.wide, .gallery.g4 .shot:first-child { grid-column: auto; grid-row: auto; }
  .hero { padding-top: 52px; }
  header.top .wrap { gap: 12px; }
  header.top .btn.small { display: none; }
  .privacy { grid-template-columns: 1fr; padding: 30px; }
  .why-grid { gap: 18px; }
  section.block { padding-top: 80px; }
  .frame { box-shadow: 6px 6px 0 var(--ink); }
}
@media (max-width: 600px) {
  .view-switch { display: none; }
  .brand { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .hero h1 .hl { white-space: normal; }
  .hero h1 { font-size: clamp(34px, 10vw, 46px); overflow-wrap: anywhere; }
}
@media (max-width: 480px) {
  .stats, .hero.split .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .stats .stat { max-width: none; flex-direction: column; align-items: flex-start; gap: 6px; padding: 14px; }
  .stats .stat:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .stat b { font-size: 26px; }
  .stat span { font-size: 12.5px; }
  .btn { padding: 13px 20px; font-size: 16px; }
  .brand { font-size: 18px; }
  .view-switch a { padding: 6px 9px; }
}
"""


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_root = Path(sys.argv[2])
    gallery_root = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    for slug, d in data.items():
        out_dir = out_root / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        page = render(d)
        page = page.replace('class="stats reveal"', f'class="stats reveal" style="--n:{page.count("class=\"stat\"")}"', 1)
        (out_dir / "index.html").write_text(page, encoding="utf-8")
        if gallery_root and d.get("gallery"):
            for g in d["gallery"]:
                shutil.copyfile(gallery_root / slug / g["file"], out_dir / g["file"])
    print(f"built {len(data)} pages -> {out_root}")


if __name__ == "__main__":
    main()
