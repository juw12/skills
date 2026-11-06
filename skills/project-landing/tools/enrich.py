"""Add verifiable repo-derived content and a visual theme to every page in data.json.

Adds per page:
  theme   - one of playful / calm / tech / clean / blueprint / arcade (chosen per project character)
  stack   - [{"name", "group"}] detected from real files + dependency manifests in the repo
  shipped - recent, project-specific commit subjects (date + message) from git history
  repo    - {"files", "commits", "first", "last", "commits_url", "tree_url"}

Usage: python enrich.py <data.json> <repo_facts.json>
"""
import json
import re
import sys
from pathlib import Path

THEMES = {
    "arcade": ["cozy-island", "game-library", "hearthwood", "townsquare-3d", "vale"],
    "blueprint": ["maccormack", "upwind", "datum-cad", "datum-bench"],
    "tech": ["steward", "scopeguard", "pushlab", "respark", "shiphub", "signals", "e-coder", "tools",
             "skillmouse", "vitals", "launchkit", "sweep", "handoff"],
    "calm": ["jeda", "haru", "teman-sehat", "morning-paper", "nudge", "rewind", "guang-yao-together", "undanu", "cairn"],
    "clean": ["plm-aml-approval", "outlook-archiver", "airiz-motor", "etsy-prompts", "twin", "mint",
              "earlystar", "orbis", "lingua", "peers"],
    # everything else: playful (glow, hazel, sortie, sync, pips, fade, crewcup, kinibuka, house-of-articles, atomize)
}

EXT_LANG = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".cs": "C#", ".swift": "Swift", ".kt": "Kotlin", ".rs": "Rust", ".go": "Go",
    ".f90": "Fortran", ".f": "Fortran", ".ps1": "PowerShell", ".bat": "Batch", ".html": "HTML/CSS",
    ".sql": "SQL", ".dart": "Dart",
}

NPM = {
    "react": ("React", "Framework"), "react-native": ("React Native", "Mobile"), "expo": ("Expo", "Mobile"),
    "next": ("Next.js", "Framework"), "vite": ("Vite", "Tooling"), "three": ("Three.js", "Graphics"),
    "electron": ("Electron", "Desktop"), "@tauri-apps/api": ("Tauri", "Desktop"),
    "@capacitor/core": ("Capacitor", "Mobile"), "express": ("Express", "Server"), "hono": ("Hono", "Server"),
    "wrangler": ("Cloudflare Workers", "Hosting"), "tailwindcss": ("Tailwind CSS", "Styling"),
    "typescript": ("TypeScript", "Language"), "socket.io": ("Socket.IO", "Realtime"), "ws": ("WebSockets", "Realtime"),
    "better-sqlite3": ("SQLite", "Data"), "pg": ("PostgreSQL", "Data"), "playwright": ("Playwright", "Testing"),
    "@playwright/test": ("Playwright", "Testing"), "vitest": ("Vitest", "Testing"), "jest": ("Jest", "Testing"),
    "openai": ("OpenAI SDK", "AI"), "@anthropic-ai/sdk": ("Anthropic SDK", "AI"), "puppeteer": ("Puppeteer", "Tooling"),
    "web-push": ("Web Push", "Platform"), "nostr-tools": ("Nostr", "Network"), "recharts": ("Recharts", "UI"),
    "ffmpeg-static": ("FFmpeg", "Media"), "remotion": ("Remotion", "Media"),
}

PY = {
    "fastapi": ("FastAPI", "Server"), "flask": ("Flask", "Server"), "django": ("Django", "Server"),
    "uvicorn": ("Uvicorn", "Server"), "langgraph": ("LangGraph", "AI"), "langchain": ("LangChain", "AI"),
    "openai": ("OpenAI SDK", "AI"), "anthropic": ("Anthropic SDK", "AI"), "playwright": ("Playwright", "Tooling"),
    "pandas": ("pandas", "Data"), "numpy": ("NumPy", "Data"), "ccxt": ("ccxt", "Data"), "yfinance": ("yfinance", "Data"),
    "python-telegram-bot": ("Telegram Bot API", "Platform"), "cadquery": ("CadQuery", "CAD"),
    "sqlalchemy": ("SQLAlchemy", "Data"), "streamlit": ("Streamlit", "UI"), "pillow": ("Pillow", "Media"),
    "opencv-python": ("OpenCV", "Vision"), "requests": ("requests", "Network"), "httpx": ("httpx", "Network"),
    "pywin32": ("pywin32", "Windows"), "psutil": ("psutil", "System"), "faster-whisper": ("faster-whisper", "AI"),
    "openpyxl": ("openpyxl", "Data"), "pytest": ("pytest", "Testing"), "selenium": ("Selenium", "Tooling"),
    "matplotlib": ("Matplotlib", "Data"), "reportlab": ("ReportLab", "Media"), "pydantic": ("Pydantic", "Data"),
    "psycopg2-binary": ("PostgreSQL", "Data"), "psycopg": ("PostgreSQL", "Data"), "edge-tts": ("Edge TTS", "Media"),
    "moviepy": ("MoviePy", "Media"), "trimesh": ("trimesh", "CAD"),
}

NOISE = re.compile(
    r"(?i)(mit everywhere|licen[sc]e|readme|\bdocs?\b|hero for every|portfolio|catalog|landing|banner|badge|"
    r"every app|all apps|typo|format|lint|chore|merge|bump .*version|cache pin|gitignore|rename|wip\b|^update\b|"
    r"profile|screenshot|\bci\b|add files via upload|^initial commit$|^(create|update|delete) \S+$)")

# repos where the source link is a whole monorepo, not this project: repo facts would mislead
SKIP_REPO_FACTS = {"atomize"}


# "How it's built" for projects whose code isn't at their listed source link
HOOD = {
    "scopeguard": {
        "note": "ScopeGuard now lives inside Steward as apps/playground, so these facts come from that folder.",
        "where": "juw12/steward/apps/playground",
        "link": "https://github.com/juw12/steward/tree/main/apps/playground",
        "link_text": "Browse apps/playground",
    },
    "atomize": {
        "stack": [
            {"name": "Next.js 14", "group": "Framework"},
            {"name": "Claude", "group": "AI"},
            {"name": "Lemon Squeezy", "group": "Payments"},
        ],
        "note": "Stack as stated in the README. The Atomize app code isn't in the public repo yet, "
                "so there's no file count or commit history to show.",
        "link": "https://github.com/juw12/atomize#readme",
        "link_text": "Read the README",
    },
}


def rel_files(facts):
    return facts.get("files", [])


def detect_stack(facts):
    files = rel_files(facts)
    found = {}

    def add(name, group):
        found.setdefault(name, group)

    counts = {}
    for f in files:
        if re.search(r"(^|/)(tests?|__tests__)/", f):
            continue
        lang = EXT_LANG.get(Path(f).suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    for lang, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if lang == "Batch" and len(counts) > 1:
            continue  # a run.bat launcher is not part of the stack
        if n >= 2 or len(counts) <= 4:
            add(lang, "Language")
    names = {Path(f).name.lower() for f in files}
    if any(f.endswith(".asmdef") for f in files) or any("/Assets/" in "/" + f for f in files if f.endswith(".cs")):
        add("Unity", "Engine")
    if "manifest.webmanifest" in names or "manifest.json" in names and "sw.js" in names:
        add("PWA", "Platform")
    if "sw.js" in names or "service-worker.js" in names:
        add("Offline service worker", "Platform")
    if "wrangler.toml" in names or "wrangler.jsonc" in names:
        add("Cloudflare Workers", "Hosting")
    if "dockerfile" in names or "docker-compose.yml" in names:
        add("Docker", "Hosting")
    if any(f.endswith(".glb") or f.endswith(".gltf") for f in files):
        add("glTF 3D models", "Graphics")
    if any(f.endswith(".plt") for f in files):
        add("Tecplot / Gnuplot data", "Output")
    if any(f.endswith(".db") or "sqlite" in f.lower() for f in files):
        add("SQLite", "Data")
    for path, text in facts.get("manifests", {}).items():
        low = path.lower()
        if low.endswith("package.json"):
            try:
                pkg = json.loads(text)
            except json.JSONDecodeError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for dep in deps:
                if dep in NPM:
                    add(*NPM[dep])
        elif low.endswith(("requirements.txt", "pyproject.toml")):
            for dep_line in re.findall(r"^[\s\"']*([A-Za-z0-9_.\-]+)", text, re.M):
                key = dep_line.lower()
                if key in PY:
                    add(*PY[key])
        elif low.endswith("cargo.toml"):
            add("Rust", "Language")
            if "tauri" in text:
                add("Tauri", "Desktop")
    if "sqlite" in json.dumps(facts.get("manifests", {})).lower():
        add("SQLite", "Data")
    if any(re.search(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]+\.py$|\.(test|spec)\.[jt]sx?$", f) for f in files):
        add("Automated tests", "Testing")
    if any("i18n" in f.lower() or "/locales/" in f.lower() for f in files):
        add("Multi-language UI", "UI")
    return [{"name": n, "group": g} for n, g in found.items()][:12]


def project_words(slug, d):
    words = {slug.lower(), d["name"].lower()}
    words |= {w.lower() for w in re.findall(r"[A-Za-z]{4,}", d["name"])}
    return words


def shipped_log(slug, d, facts, other_names):
    out = []
    seen = set()
    for c in facts.get("recent", []):
        msg = re.sub(r"\s+", " ", c["msg"]).strip()
        if len(msg) < 14 or NOISE.search(msg):
            continue
        low = msg.lower()
        mentions_other = any(o in low for o in other_names)
        mentions_self = any(w in low for w in project_words(slug, d))
        if mentions_other and not mentions_self:
            continue
        # strip a leading "<Name>:" or "<name> 1.2.3:" prefix, it's implied by the page
        msg = re.sub(rf"(?i)^({re.escape(d['name'])}|{re.escape(slug)})(\s+v?\d+(\.\d+)*)?\s*[:\-–]\s*", "", msg)
        msg = msg[0].upper() + msg[1:] if msg else msg
        if len(msg) > 150:
            msg = msg[:150].rsplit(" ", 1)[0].rstrip(",;:-") + "…"
        key = msg.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append({"date": c["date"], "msg": msg})
        if len(out) == 5:
            break
    return out


def main():
    data_path = Path(sys.argv[1])
    data = json.loads(data_path.read_text(encoding="utf-8"))
    facts = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    theme_of = {slug: theme for theme, slugs in THEMES.items() for slug in slugs}
    all_names = {d["name"].lower() for d in data.values()} | set(data)
    for slug, d in data.items():
        f = {} if slug in SKIP_REPO_FACTS else (facts.get(slug) or {})
        d["theme"] = theme_of.get(slug, "playful")
        d["stack"] = detect_stack(f) if f else []
        others = {n for n in all_names if n not in project_words(slug, d) and len(n) >= 4}
        shipped = shipped_log(slug, d, f, others) if f else []
        d["shipped"] = shipped if len(shipped) >= 2 else []
        d.pop("repo", None)
        if f:
            base = f"https://github.com/{f['repo']}"
            path = f["path"]
            d["repo"] = {
                "files": f["file_count"],
                "commits": f["commit_count"],
                "first": f["first_commit"],
                "last": f["last_commit"],
                "commits_url": f"{base}/commits/{f['branch']}/{path}".rstrip("/"),
            }
        d.pop("hood", None)
        hood = HOOD.get(slug)
        if hood:
            if hood.get("stack") and not d["stack"]:
                d["stack"] = hood["stack"]
            d["hood"] = {k: v for k, v in hood.items() if k != "stack"}
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for slug, d in sorted(data.items()):
        print(f"{slug:20} {d['theme']:9} stack={len(d['stack']):2} shipped={len(d['shipped'])}")


if __name__ == "__main__":
    main()
