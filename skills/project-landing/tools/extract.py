"""Extract landing-page content from a project's README (facts only, no invention).

extract(md) -> dict with: about, features, steps, quickstart, limits, privacy, faq, images, sections
"""
import re

BADGE_HOSTS = ("img.shields.io", "badge.svg", "render.com/images", "deploy", "/badge")


def strip_md(text):
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"<img[^>]*>", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)\*(?!\w)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def split_sections(md):
    """Return list of (level, heading, body) with code fences kept intact."""
    sections = []
    level, heading, buf = 1, "", []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        m = None if in_code else re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            sections.append((level, heading, "\n".join(buf)))
            level, heading, buf = len(m.group(1)), strip_md(m.group(2)), []
        else:
            buf.append(line)
    sections.append((level, heading, "\n".join(buf)))
    return [s for s in sections if s[1] or s[2].strip()]


def paragraphs(body):
    out, cur, in_code = [], [], False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        s = line.strip()
        if not s or s.startswith(("|", ">", "<p", "<a", "<img", "<table", "<tr", "<td", "<div", "---")):
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        if re.match(r"^([-*+]|\d+[.)])\s", s):
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return [strip_md(p) for p in out if len(strip_md(p)) > 40]


def list_items(body, numbered=None):
    items, in_code = [], False
    current = None
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m and len(m.group(1)) < 2:
            is_num = m.group(2)[0].isdigit()
            if numbered is not None and is_num != numbered:
                current = None
                continue
            current = m.group(3).strip()
            items.append(current)
        elif current is not None and line.startswith("  ") and line.strip() and not re.match(r"^\s*([-*+]|\d+[.)])\s", line):
            items[-1] = items[-1] + " " + line.strip()
        elif not line.strip():
            current = None
    return items


def split_title(item):
    """'**Title** — body' / '**Title:** body' / 'Title: body' -> (title, body)."""
    m = re.match(r"^\*\*(.+?)\*\*\s*[:.\-–—]*\s*(.*)$", item)
    if m:
        return strip_md(m.group(1)).rstrip(":. "), strip_md(m.group(2))
    plain = strip_md(item)
    m = re.match(r"^([^:—–]{3,48})\s*[:—–]\s+(.{12,})$", plain)
    if m and not m.group(1).lower().startswith(("http", "run", "the ", "a ")):
        return m.group(1).strip(), m.group(2).strip()
    return None, plain


FEATURE_HEADS = re.compile(r"^about$|^the wedge|feature|what you get|what it does|what[’']?s in|in the box|highlights|what's done|"
                           r"one app|what (?:it|this) is|capabilit|why|what's inside|includes|tools included|"
                           r"what it discovers|modes|apps|working now|fitur", re.I)
STEP_HEADS = re.compile(r"how (?:it|the .*|this) works|how to use|^use$|usage|using|workflow|the growth loop|how the", re.I)
QUICK_HEADS = re.compile(r"quick ?start|install|run|getting started|set ?up|local|develop|menjalankan|try it", re.I)
LIMIT_HEADS = re.compile(r"limit|honest|known issue|caveat|todo|not (?:yet|done)|catatan|what needs you", re.I)
PRIVACY_HEADS = re.compile(r"privacy|data|security|offline|your data", re.I)
FAQ_HEADS = re.compile(r"faq|questions", re.I)
SKIP_HEADS = re.compile(r"license|contribut|see it in action|layout|structure|files|releasing|tests?$|"
                        r"project structure|documentation|repository|changelog|credits", re.I)

CODE_LANGS = ("bash", "sh", "shell", "powershell", "ps1", "pwsh", "cmd", "console", "bat", "")


def code_blocks(body):
    return [(lang.lower(), code.strip("\n")) for lang, code in re.findall(r"```(\w*)[^\n]*\n(.*?)```", body, re.S)]



def tables(body):
    """Markdown tables -> list of rows (list of raw cell strings), header row dropped."""
    out, cur = [], []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
                continue
            cur.append(cells)
        else:
            if cur:
                out.append(cur)
                cur = []
    if cur:
        out.append(cur)
    return out


DEVICE_HEADS = re.compile(r"download|install|get (?:it|glow|the app)|platforms|devices", re.I)


def extract_tables(sections, data):
    for level, head, body in sections:
        for rows in tables(body):
            if len(rows) < 2:
                continue
            body_rows = rows[1:] if "**" not in rows[0][0] else rows
            if DEVICE_HEADS.search(head) and not data.get("devices"):
                devices = []
                for r in body_rows:
                    if len(r) >= 2 and strip_md(r[0]) and strip_md(r[1]):
                        devices.append({"device": strip_md(r[0]), "how": strip_md(r[1])})
                if 2 <= len(devices) <= 7:
                    data["devices"] = devices
                    continue
            header = " ".join(rows[0]).lower()
            loose = bool(re.search(r"activity|feature|what it is|what it does|tool|mode|screen|page|command|app\b", header))
            for r in body_rows:
                if len(r) >= 2 and ("**" in r[0] or (loose and 2 < len(strip_md(r[0])) < 40)):
                    title = strip_md(r[0])
                    text = strip_md(r[1])
                    if text and not text.startswith("http") and len(text) > 15:
                        data.setdefault("table_features", []).append({"title": title, "body": text, "from": head})


def extract(md, repo_raw_base=None):
    sections = split_sections(md)
    data = {"about": [], "features": [], "steps": [], "quickstart": None, "limits": [],
            "privacy": [], "faq": [], "images": [], "headings": [h for _, h, _ in sections if h]}

    for level, head, body in sections:
        if head.lower() in ("about",) or (level <= 1 and not data["about"]):
            data["about"] += paragraphs(body)[:2]

    seen_titles = set()

    def add_feature(title, body, source):
        if not body or len(body) < 12:
            return
        key = (title or body[:30]).lower()
        if key in seen_titles:
            return
        seen_titles.add(key)
        data["features"].append({"title": title, "body": body, "from": source})

    # pass 1: feature-like sections
    for level, head, body in sections:
        if SKIP_HEADS.search(head) or not FEATURE_HEADS.search(head):
            continue
        for item in list_items(body):
            title, text = split_title(item)
            add_feature(title, text, head)
        if level >= 3 and not list_items(body):
            paras = paragraphs(body)
            if paras:
                add_feature(head, paras[0], head)
    # pass 2: bold-led bullets anywhere else
    for level, head, body in sections:
        if SKIP_HEADS.search(head) or LIMIT_HEADS.search(head) or FAQ_HEADS.search(head):
            continue
        for item in list_items(body):
            if item.startswith("**"):
                title, text = split_title(item)
                add_feature(title, text, head)
    # pass 3: h3 subsections with a paragraph (e.g. "### Dashboard")
    for level, head, body in sections:
        if level == 3 and not SKIP_HEADS.search(head) and not QUICK_HEADS.search(head):
            paras = paragraphs(body)
            if paras:
                add_feature(head, paras[0], "h3")

    for level, head, body in sections:
        if STEP_HEADS.search(head):
            nums = list_items(body, numbered=True)
            src = nums if len(nums) >= 2 else []
            if not src:
                bullets = list_items(body, numbered=False)
                src = bullets if 2 <= len(bullets) <= 6 else []
            if not src:
                paras = paragraphs(body)
                src = paras if 2 <= len(paras) <= 5 else []
            for item in src[:5]:
                title, text = split_title(item)
                data["steps"].append({"title": title, "body": text})
            if data["steps"]:
                data["steps_heading"] = head
                break

    quick_groups = []
    for idx, (level, head, body) in enumerate(sections):
        if not QUICK_HEADS.search(head) or re.search(r"tests?\b", head, re.I):
            continue
        group_body = body
        for lvl2, head2, body2 in sections[idx + 1:]:
            if lvl2 <= level:
                break
            group_body += "\n" + body2
        quick_groups.append((head, group_body))
    for head, body in quick_groups:
        merged = [(lang, code) for lang, code in code_blocks(body) if lang in CODE_LANGS]
        if len(merged) > 1:
            lines = []
            for lang, code in merged:
                lines += [l for l in code.splitlines() if l.strip()]
            if 2 <= len(lines) <= 9 and max(len(l) for l in lines) <= 110:
                data["quickstart"] = {"heading": head, "lang": merged[0][0] or "shell", "code": "\n".join(lines)}
                break
        for lang, code in code_blocks(body):
            lines = [l for l in code.splitlines() if l.strip()]
            if lang in CODE_LANGS and 1 <= len(lines) <= 9 and max(len(l) for l in lines) <= 110:
                data["quickstart"] = {"heading": head, "lang": lang or "shell", "code": "\n".join(lines)}
                break
        if data["quickstart"]:
            break

    for level, head, body in sections:
        if LIMIT_HEADS.search(head):
            for item in list_items(body):
                title, text = split_title(item)
                txt = f"{title}: {text}" if title else text
                if 15 < len(txt) < 260:
                    data["limits"].append(txt)
            if not list_items(body):
                data["limits"] += [p for p in paragraphs(body) if len(p) < 260][:3]

    for level, head, body in sections:
        if PRIVACY_HEADS.search(head) and not SKIP_HEADS.search(head):
            items = [strip_md(i) for i in list_items(body)]
            paras = paragraphs(body)
            data["privacy"] = (paras[:1] + items[:4]) if (paras or items) else []
            if data["privacy"]:
                data["privacy_heading"] = head
                break

    for level, head, body in sections:
        if level >= 3 and head.endswith("?"):
            paras = paragraphs(body)
            if paras:
                data["faq"].append({"q": head, "a": paras[0]})
        if FAQ_HEADS.search(head):
            for item in list_items(body):
                m = re.match(r"^\*\*(.+?\?)\*\*\s*(.*)$", item)
                if m:
                    data["faq"].append({"q": strip_md(m.group(1)), "a": strip_md(m.group(2))})

    extract_tables(sections, data)
    if data.get("table_features"):
        data["features"] = data["table_features"] + data["features"]

    for m in re.finditer(r'!\[([^\]]*)\]\(([^)\s]+)[^)]*\)|<img[^>]+src="([^"]+)"[^>]*?(?:alt="([^"]*)")?', md):
        src = m.group(2) or m.group(3)
        alt = m.group(1) or m.group(4) or ""
        if not src or any(h in src for h in BADGE_HOSTS) or src.endswith(".svg"):
            continue
        if "banner" in src.lower():
            continue
        data["images"].append({"src": src, "alt": strip_md(alt)})
    return data
