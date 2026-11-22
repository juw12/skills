"""Give a web-app project its Windows, Mac and Android versions (the Jeda desktop shell, the Cairn Android shell).

    python web_shells.py survey PROFILE_README.md     # what every profile project has and lacks (writes survey.json)
    python web_shells.py plan  NAME [NAME ...]        # read the repo, print what would be stamped (writes plans/<slug>.json)
    python web_shells.py apply NAME [NAME ...]        # stamp, README, secrets, branch agent/four-versions, pull request
    python web_shells.py plan --all-web               # every project whose only version is the iPhone web app

NAME is the project's name in the profile. Run `survey` first; `plan` shows the page title, icon, colours and
the check that says the app started, and names problems (a private repo, a folder that is already there).
`apply` needs the push account to be juw12 (push_as.py) because it sets secrets and adds workflows.

A project is left alone when web_shells_overrides.json (next to this file) gives it a "skip" with the reason:
a window around a page is a version only where the page does the project's job (ship.md). Other keys there:
"only" ("android" or "mac": the project has the rest), "put" (the folder for desktop/ and android/ when the
project already has a desktop/ of its own), "url", "site", "name", "tagline", "title_has", "started",
"started_says", "mac_note".

Everything it needs it fetches into a work folder (FOUR_WORK, default ~/four-versions-work): the projects,
Jeda and Cairn (the two shells), and the private juw12/web-shells-signing (the Android key). After `apply`:
wait for the pull request's checks, merge, wait for the two workflows on main to publish, read the gate again
(platforms.py), add the app to apps.md in web-shells-signing, and link the README section from the profile.
Works on Windows and on a Mac; needs git, gh, and Pillow or macOS's sips for the icons.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HONE = Path(__file__).resolve().parent
HERE = Path(os.environ.get("FOUR_WORK") or Path.home() / "four-versions-work")
SHIP = HERE / "repos"
KEY = HERE / "web-shells-signing"
GH = shutil.which("gh") or "gh"
BRANCH = "agent/four-versions"
# Names another well-known desktop app already uses for its own folders and its .app.
TAKEN = {"hazel", "rewind", "together", "nudge", "sync"}
EMPTY_ROOT = re.compile(r'<(div|main|section|article)\b[^>]*\bid="([\w-]+)"[^>]*>\s*</\1>', re.I)
LIKELY_ROOTS = ("app", "root", "main", "game", "view", "screen", "content", "stage", "page", "ui", "shell", "container")


def run(*command, cwd=None, check=True, quiet=True):
    done = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    network = command[0] == GH or (command[0] == "git" and command[1] in ("push", "fetch", "clone"))
    for wait in (5, 15, 40):  # the connection drops now and then: the same command again, a little later
        if done.returncode == 0 or not network or not re.search(r"reset by peer|timed? ?out|Could not resolve|HTTP 5\d\d|unexpected disconnect|EOF", done.stderr + done.stdout, re.I):
            break
        time.sleep(wait)
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise SystemExit("FAILED: %s\n%s" % (" ".join(map(str, command)), (done.stderr or done.stdout)[-800:]))
    return done.stdout.strip()


def fetch(repo: str, folder: Path) -> Path:
    """A checkout of juw12/<repo> in the work folder, made the first time it is needed."""
    if not folder.exists():
        folder.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--quiet", "--depth", "1", "https://github.com/juw12/%s.git" % repo, str(folder))
    return folder


def square(picture: Path, size: int) -> None:
    """Scale a PNG to size x size in place: Pillow where it is installed, macOS's own sips otherwise."""
    try:
        from PIL import Image
    except ImportError:
        subprocess.run(["sips", "-z", str(size), str(size), str(picture)], check=True, capture_output=True)
        return
    Image.open(picture).convert("RGBA").resize((size, size), Image.LANCZOS).save(picture)


def make_survey(profile: str) -> None:
    """What each profile project has and lacks, as the four-versions gate reads it. Read twice and joined:
    a dropped connection looks like a missing version, and only ever hides things."""
    sys.path.insert(0, str(HONE))
    import featured
    import platforms

    projects = [p for p in featured.read_projects(Path(profile).read_text(encoding="utf-8")) if p["section"] != "Archive"]
    readings = [platforms.check_all(projects), platforms.check_all(projects)]
    rows = []
    for index, project in enumerate(projects):
        first, second = readings[0][index], readings[1][index]
        if first.get("no_app"):
            continue
        has = {name: bool(first[name]["ok"] or second[name]["ok"]) for name in platforms.PLATFORMS}
        gaps = min((platforms.gaps(first), platforms.gaps(second)), key=len)
        rows.append({
            "name": project["name"], "section": project["section"], "repo": "%s/%s" % (project["owner"], project["repo"]),
            "path": project["path"], "demo": project["demo"], "has": has,
            "gaps": [gap for gap in gaps if not any(has[p] and gap == p + " missing" for p in has)],
        })
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "survey.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    done = [row["name"] for row in rows if all(row["has"].values()) and not row["gaps"]]
    print("%d of %d have all four. %s" % (len(done), len(rows), ", ".join("%s %d" % (p, sum(1 for r in rows if r["has"][p])) for p in platforms.PLATFORMS)))
    for row in rows:
        if row["name"] not in done:
            marks = "".join(letter if row["has"][name] else "-" for name, letter in zip(platforms.PLATFORMS, "WMIA"))
            print("%s  %-24s %s%s  %s" % (marks, row["name"][:24], row["repo"], "/" + row["path"] if row["path"] else "", "; ".join(row["gaps"])[:90]))


def survey() -> dict:
    return {row["name"].lower(): row for row in json.loads((HERE / "survey.json").read_text(encoding="utf-8"))}


def overrides() -> dict:
    path = HONE / "web_shells_overrides.json"
    return {k.lower(): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()} if path.exists() else {}


def checkout(row: dict) -> Path:
    """A fresh checkout of the repo's main branch (the monorepo: the sparse clone that is already there)."""
    repo = row["repo"].split("/")[1]
    folder = SHIP / repo
    if not folder.exists():
        folder.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--quiet", "--depth", "1", *(["--filter=blob:none", "--sparse"] if row["path"] else []),
            "https://github.com/%s.git" % row["repo"], str(folder))
    run("git", "config", "user.email", "73946469+juw12@users.noreply.github.com", cwd=folder)
    run("git", "config", "user.name", "Juwen Lie", cwd=folder)
    if row["path"]:
        run("git", "sparse-checkout", "add", row["path"], ".github/workflows", cwd=folder, check=False)
    return folder


def file_name(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    joined = "".join(word if word.isupper() or len(words) == 1 else word[0].upper() + word[1:] for word in words)
    return joined + "App" if joined.lower() in TAKEN else joined


def first_sentence(text: str, limit: int = 70) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    cut = re.split(r"(?<=[.!?])\s", text)[0].rstrip(".")
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0]
        if "," in cut[25:]:  # end at a comma when there is one, so it does not stop in the middle of a list
            cut = cut[:25] + cut[25:].rsplit(",", 1)[0]
        words = cut.rstrip(",;:(").split(" ")
        while words and words[-1].lower().strip(",;:(") in ("and", "with", "for", "your", "a", "an", "the", "to", "of", "on", "in", "or", "dan", "di", "yang", "untuk", "dengan"):
            words.pop()
        cut = " ".join(words).rstrip(",;:(")
    cut = re.sub(r"\s+", " ", cut.replace("\u2014", "-").replace("\u2013", "-").replace("\u00b7", "-"))
    # it goes into an installer script and a Windows version record: plain letters, no quotes
    cut = cut.replace("\u2019", "").replace("'", "").replace('"', "").replace("&amp;", "and").replace("&", "and")
    return cut.encode("ascii", "ignore").decode().strip() or "A web app in its own window"


def plan(row: dict, extra: dict) -> dict:
    folder = checkout(row)
    slug_repo = row["repo"]
    path = row["path"]
    page = "index.html"
    live = (extra.get("url") or row["demo"]).split("?")[0].split("#")[0]
    if live.endswith(".html"):
        live, page = live.rsplit("/", 1)[0] + "/", live.rsplit("/", 1)[1]
    if page == "index.html" and not live.endswith("/"):
        live += "/"
    if "site" in extra:
        site = extra["site"]
    elif path:
        site = path + "/web" if (folder / path / "web" / page).is_file() else path
    else:
        pages = run(GH, "api", "repos/%s/pages" % slug_repo, "--jq", '[.build_type, (.source.path // "")] | @tsv', check=False)
        kind, _, source = pages.partition("\t")
        site = source.strip("/") if kind == "legacy" else ("docs" if (folder / "docs" / page).is_file() and not (folder / page).is_file() else "")
    site_dir = folder / site if site else folder
    problems = []
    if not (site_dir / page).is_file():
        problems.append("no %s in %s" % (page, site or "the repo's top folder"))
        html = ""
    else:
        html = (site_dir / page).read_text(encoding="utf-8", errors="replace")
    title = (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1].strip()
    title = re.sub(r"\s+", " ", title).replace("&amp;", "&").replace("&middot;", "·")
    name = extra.get("name") or file_name(row["name"])
    display = row["name"]
    # the word of the title that names the app, as the title spells it
    title_has = extra.get("title_has", "")
    if not title_has:
        for candidate in (display, display.split()[0], re.split(r"\s*[—–·|:\-]\s*", title)[0]):
            found = re.search(re.escape(candidate), title, re.I)
            if candidate and found:
                title_has = found.group(0)
                break
    if not title_has:
        problems.append("the page title %r does not name the app" % title)

    manifest = {}
    link = re.search(r'<link[^>]+rel="manifest"[^>]*>', html, re.I)
    href = re.search(r'href="([^"]+)"', link.group(0)) if link else None
    manifest_file = (site_dir / href.group(1).split("?")[0]) if href else None
    if manifest_file and manifest_file.is_file():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except ValueError:
            problems.append("the web manifest is not valid JSON")
    icon = ""
    best = 0
    for entry in manifest.get("icons", []):
        size = int((re.search(r"(\d+)x", entry.get("sizes", "0x")) or [0, 0])[1] or 0)
        candidate = (manifest_file.parent / entry.get("src", "").split("?")[0]).resolve()
        if entry.get("src", "").lower().endswith(".png") and "maskable" not in entry.get("purpose", "any") and size > best and candidate.is_file():
            icon, best = str(candidate), size
    if not icon:
        for entry in manifest.get("icons", []):
            candidate = (manifest_file.parent / entry.get("src", "").split("?")[0]).resolve()
            if entry.get("src", "").lower().endswith(".png") and candidate.is_file():
                icon, best = str(candidate), max(best, 1)
    if not icon:
        touch = re.search(r'<link[^>]+rel="apple-touch-icon"[^>]*href="([^"]+\.png)[^"]*"', html, re.I)
        if touch and (site_dir / touch.group(1)).is_file():
            icon, best = str((site_dir / touch.group(1)).resolve()), 180
    if not icon:
        problems.append("no PNG icon found")
    theme = (re.search(r'<meta[^>]+name="theme-color"[^>]*content="(#[0-9a-fA-F]{3,8})"', html) or [None, ""])[1]
    background = manifest.get("background_color") or theme or "#111111"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", background):
        background = "#111111"
    accent = manifest.get("theme_color") or theme or "#d9481f"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent) or accent.lower() == background.lower():
        accent = "#d9481f"
    description = manifest.get("description") or (re.search(r'<meta[^>]+name="description"[^>]*content="([^"]+)"', html) or [None, ""])[1]
    tagline = extra.get("tagline") or first_sentence(description or title or display)

    started, says = extra.get("started", ""), extra.get("started_says", "what the app draws when it starts")
    if not started:
        roots = [m.group(2) for m in EMPTY_ROOT.finditer(html)]
        roots.sort(key=lambda found: LIKELY_ROOTS.index(found.lower()) if found.lower() in LIKELY_ROOTS else 99)
        if roots and roots[0].lower() in LIKELY_ROOTS:
            started = "!!(document.getElementById('%s') && document.getElementById('%s').children.length)" % (roots[0], roots[0])
            says = "what the app draws into #%s when it starts" % roots[0]
        else:
            started = "!!(document.body && document.body.children.length && document.scripts.length && document.body.innerText.trim().length + document.querySelectorAll('canvas').length > 0)"
            says = "the page with its scripts and something on it"
    slug = re.sub(r"[^a-z0-9]", "", (path.split("/")[-1] if path else slug_repo.split("/")[1]).lower())
    tag_base = path.split("/")[-1] if path else ""
    existing = set(p.name for p in (folder / ".github" / "workflows").glob("*.yml")) if (folder / ".github" / "workflows").is_dir() else set()
    desktop_flow = (tag_base + "-desktop.yml") if tag_base else ("desktop.yml" if "desktop.yml" not in existing else "desktop-apps.yml")
    desktop_tag = (tag_base + "-desktop") if tag_base else "desktop"
    if extra.get("only") == "mac":  # the project has its Windows app already
        desktop_flow = (tag_base + "-mac.yml") if tag_base else "mac.yml"
        desktop_tag = (tag_base + "-mac") if tag_base else "mac"
    android_flow = (tag_base + "-android.yml") if tag_base else ("android.yml" if "android.yml" not in existing else "android-app.yml")
    put = extra.get("put", path)  # the folder that gets desktop/ and android/
    only = extra.get("only", "")   # "android": the project has its desktop versions already
    prefix = (put + "/") if put else ""
    for there in (("android",) if only == "android" else ("desktop",) if only == "mac" else ("desktop", "android")):
        if (folder / prefix / there).exists() if prefix else (folder / there).exists():
            problems.append("%s%s/ is already there" % (prefix, there))
    visibility = run(GH, "api", "repos/%s" % slug_repo, "--jq", ".visibility", check=False)
    if visibility != "public":
        problems.append("the repo is %s (runner minutes are paid there)" % (visibility or "unknown"))
    result = {
        "key": row["name"].lower(), "repo": slug_repo, "path": path, "put": put, "only": only, "checkout": str(folder), "site": site, "page": page,
        "title": title, "problems": problems + ([extra["skip"]] if extra.get("skip") else []),
        "desktop": {
            "name": name, "title": display, "display": display, "slug": slug, "tagline": tagline, "url": live if page == "index.html" else live + page,
            "repo": slug_repo, "target": str(folder), "folder": put, "site": site, "icon": icon, "title_has": title_has,
            "started": started, "started_says": says, "keeps": "what you saved in it", "light": background, "dark": background,
            "tag": desktop_tag, "workflow": desktop_flow,
            "android_note": "[%s-android.apk](https://github.com/%s/releases/download/%s/%s-android.apk) | Open the file on the phone and allow your browser to install apps once." % (
                name, slug_repo, (tag_base + "-android") if tag_base else "android", name),
        },
        "android": {
            "name": name, "display": display, "slug": slug, "id": "io.github.juw12." + slug, "url": live if page == "index.html" else live + page,
            "repo": slug_repo, "target": str(folder), "folder": put, "icon": icon, "background": background, "accent": accent,
            "tag": (tag_base + "-android") if tag_base else "android", "workflow": android_flow, "alias": "shells",
            "cert": (fetch("web-shells-signing", KEY) / "shells-release-cert-sha256.txt").read_text().strip().replace(":", "").lower(),
            "signing": "juw12/web-shells-signing",
        },
        "icon_px": best, "mac_note": extra.get("mac_note", ""),
    }
    (HERE / "plans").mkdir(exist_ok=True)
    (HERE / "plans" / (slug + ".json")).write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return result


def get_it(planned: dict) -> str:
    d, a = planned["desktop"], planned["android"]
    base = "https://github.com/%s/releases/download" % planned["repo"]
    # links in a README are relative to its own folder
    inside = planned["put"][len(planned["path"]):].strip("/") if planned["put"].startswith(planned["path"]) else planned["put"]
    prefix = (inside + "/") if inside else ""
    android = f"- **Android:** [`{a['name']}-android.apk`]({base}/{a['tag']}/{a['name']}-android.apk): open the file on the phone and allow your browser to install apps once.\n"
    if planned["only"] == "mac":
        return (
            "## On a Mac\n\n"
            f"- **Mac:** [`{d['name']}-macOS-AppleSilicon.dmg`]({base}/{d['tag']}/{d['name']}-macOS-AppleSilicon.dmg) (M1 and newer) or "
            f"[`{d['name']}-macOS-Intel.dmg`]({base}/{d['tag']}/{d['name']}-macOS-Intel.dmg). Open it and drag {d['name']} to Applications. The first time, "
            "macOS blocks it because it is not notarized: **System Settings → Privacy & Security → Open Anyway**.\n\n"
            f"It is the web edition ({d['url']}) in its own window ([`desktop/`]({prefix}desktop/README.md)) and changes with it. {planned['mac_note']}"
            "Each build is opened on an Apple-silicon Mac and an Intel Mac on GitHub before it is published: the page loads, the app starts and can store data. "
            "No Mac of ours has run it yet.\n\n"
        )
    if planned["only"] == "android":
        return (
            "## On an Android phone\n\n" + android +
            f"\nIt is the web app ({a['url']}) in a full-screen window of its own ([`android/`]({prefix}android/README.md)) and changes with it. "
            "The build is opened on an Android emulator on GitHub before it is published: it installs, opens and stays up. No real phone has run it yet.\n\n"
        )
    return (
        "## Get it on your device\n\n"
        f"- **Windows:** [`{d['name']}-Windows-Setup.exe`]({base}/{d['tag']}/{d['name']}-Windows-Setup.exe) (no admin needed; if Windows says it "
        f"protected your PC, choose *More info → Run anyway*), or without installing [`{d['name']}-Windows-Portable.zip`]({base}/{d['tag']}/{d['name']}-Windows-Portable.zip).\n"
        f"- **Mac:** [`{d['name']}-macOS-AppleSilicon.dmg`]({base}/{d['tag']}/{d['name']}-macOS-AppleSilicon.dmg) (M1 and newer) or "
        f"[`{d['name']}-macOS-Intel.dmg`]({base}/{d['tag']}/{d['name']}-macOS-Intel.dmg). The first time, macOS blocks it because it is not notarized: "
        "**System Settings → Privacy & Security → Open Anyway**.\n" + android +
        f"- **iPhone:** open {d['url']} in Safari, tap Share, then **Add to Home Screen**.\n\n"
        f"The Windows, Mac and Android apps are the web app in its own window ([`desktop/`]({prefix}desktop/README.md), [`android/`]({prefix}android/README.md)) "
        "and change with it. Each build is opened on GitHub's machines before it is published: on Windows and on a Mac the page loads, the app starts "
        "and can store data; on an Android emulator it installs, opens and stays up. They are not code-signed or notarised, and no real phone or PC "
        "has run them yet.\n\n"
    )


def edit_readme(planned: dict) -> str:
    folder = Path(planned["checkout"])
    readme = (folder / planned["path"] / "README.md") if planned["path"] else folder / "README.md"
    if not readme.is_file():
        readme.write_text("# %s\n\n%s\n" % (planned["desktop"]["display"], get_it(planned)), encoding="utf-8")
        return "README made"
    text = readme.read_text(encoding="utf-8")
    if "## Get it on your device" in text or ("## On an Android phone" in text and planned["only"] == "android") or "## On a Mac\n" in text:
        return "README already has the section"
    after = text.find("<!-- HERO:END -->")
    heading = re.search(r"^## ", text[max(after, 0):], re.M)
    if heading:
        at = max(after, 0) + heading.start()
        text = text[:at] + get_it(planned) + text[at:]
    else:
        text = text.rstrip("\n") + "\n\n" + get_it(planned)
    readme.write_text(text, encoding="utf-8")
    return "README edited"


def apply(planned: dict) -> str:
    if planned["problems"]:
        return "SKIPPED: " + "; ".join(planned["problems"])
    folder = Path(planned["checkout"])
    if not planned["path"] and run("git", "status", "--short", cwd=folder):
        # a run that stopped half way left its files here: start this repo again from its main branch
        run("git", "checkout", "--quiet", "--force", "-B", BRANCH + "-old", cwd=folder)
        run("git", "clean", "-fdq", cwd=folder)
    run("git", "fetch", "--quiet", "origin", cwd=folder)
    default = run("git", "rev-parse", "--abbrev-ref", "origin/HEAD", cwd=folder, check=False).replace("origin/", "") or "main"
    branch = BRANCH  # a repo of many apps: one branch and one pull request for all of them
    if run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=folder) != branch:
        run("git", "checkout", "--quiet", "-B", branch, "origin/" + default, cwd=folder)
    spec_dir = HERE / "plans"
    for kind, tool, template in (("desktop", HONE / "desktop_shell.py", fetch("jeda", HERE / "jeda")), ("android", HONE / "android_shell.py", fetch("cairn", HERE / "cairn"))):
        if (kind == "desktop" and planned["only"] == "android") or (kind == "android" and planned["only"] == "mac"):
            continue
        spec_file = spec_dir / ("%s-%s.json" % (planned["desktop"]["slug"], kind))
        spec_file.write_text(json.dumps(planned[kind], indent=1, ensure_ascii=False), encoding="utf-8")
        out = run(sys.executable, str(tool), str(spec_file), "--template", str(template))
        if "STILL NAMES" in out:
            return "STOPPED: " + out[out.index("STILL NAMES"):][:400]
    shells = (folder / planned["put"]) if planned["put"] else folder
    if planned["only"] == "mac":
        # the same shell without its Windows half: one Windows app is enough
        flow = folder / ".github" / "workflows" / planned["desktop"]["workflow"]
        content = flow.read_text(encoding="utf-8")
        for old_part in ("          - name: Windows\n            os: windows-latest\n",):
            assert old_part in content
            content = content.replace(old_part, "")
        content, count = re.subn(r"for name in \S+-Windows-Setup\.exe \S+-Windows-Portable\.zip \\\n\s+", "for name in ", content)
        assert count == 1
        content = re.sub(r"          \| \*\*Windows 10/11\*\* \|[^\n]*\n", "", content)
        content = re.sub(r"#   Windows  [^\n]*\n", "", content)
        content = content.replace("for Windows and Mac", "for Mac").replace("on Windows, an Apple-chip Mac and an Intel Mac", "on an Apple-chip Mac and an Intel Mac")
        flow.write_text(content, encoding="utf-8")
    if planned["page"] != "index.html" and planned["only"] != "android":
        smoke = shells / "desktop" / "smoke_test.py"
        text = smoke.read_text(encoding="utf-8")
        old = 'return "http://127.0.0.1:%d/" % server.server_address[1]'
        assert old in text
        smoke.write_text(text.replace(old, 'return "http://127.0.0.1:%%d/%s" %% server.server_address[1]' % planned["page"]), encoding="utf-8")
    if planned["icon_px"] < 512 and planned["only"] != "android":  # the desktop build draws its icons from a 512 px picture
        target_icon = shells / "desktop" / "icon-512.png"
        square(target_icon, 512)
    note = edit_readme(planned)
    repo = planned["repo"]
    if planned["only"] != "mac":
        password = (KEY / "shells-release-password.txt").read_text().strip()
        for secret, value in (("ANDROID_KEYSTORE_B64", (KEY / "keystore.b64").read_text()), ("ANDROID_KEYSTORE_PASSWORD", password)):
            for wait in (0, 5, 15, 40, 90):
                time.sleep(wait)
                if subprocess.run([GH, "secret", "set", secret, "--repo", repo], input=value, text=True, capture_output=True).returncode == 0:
                    break
            else:
                return "STOPPED: could not set the secret %s (the connection kept dropping)" % secret
    display = planned["desktop"]["display"]
    run("git", "add", "-A", cwd=folder)
    what = {"android": "Android", "mac": "Mac"}.get(planned["only"], "Windows, Mac and Android")
    run("git", "commit", "--quiet", "-m", "%s for %s: the web app in its own window, built and opened on each system before it is published" % (display, what), cwd=folder)
    run("git", "push", "--quiet", "--force", "-u", "origin", branch, cwd=folder)
    body = (
        "Adds `desktop/` (Windows and Mac: a native window around the live site, the shell Jeda uses) and `android/` (a full-screen "
        "window around it, the shell Cairn uses), stamped for %s by hone's `desktop_shell.py` and `android_shell.py`.\n\n"
        "The two workflows build on Windows, an Apple-silicon Mac, an Intel Mac and for Android; open each build (page title, the app started, "
        "the page can store data; on an Android 14 emulator: installs, opens, stays up); and publish what passed to the `%s` and `%s` releases "
        "(not marked latest). The README names the four versions.\n\nThe .apk is signed with the web-shells key (backup: private `juw12/web-shells-signing`). "
        "Nothing is code-signed for Windows or notarised for the Mac. No real phone or PC has run them yet."
    ) % (display, planned["desktop"]["tag"], planned["android"]["tag"])
    url = run(GH, "pr", "create", "--repo", repo, "--base", default, "--head", branch,
              "--title", "%s for %s" % (display, what), "--body", body, check=False)
    return "%s; %s" % (note, url.splitlines()[-1] if url else "pull request not made")


def main(argv: list[str]) -> int:
    action, names = argv[0], argv[1:]
    if action == "survey":
        make_survey(names[0])
        return 0
    rows, extra = survey(), overrides()
    if names == ["--all-web"]:
        names = [row["name"] for row in rows.values() if row["has"] == {"Windows": False, "Mac": False, "iPhone": True, "Android": False}]
    for name in names:
        row = rows[name.lower()]
        planned = plan(row, extra.get(name.lower(), {}))
        d = planned["desktop"]
        if action == "plan":
            print("%-18s %-16s site=%-22s icon=%spx  title_has=%r  started: %s%s" % (
                row["name"][:18], d["name"], planned["site"] or ".", planned["icon_px"], d["title_has"], d["started_says"],
                ("  !! " + "; ".join(planned["problems"])) if planned["problems"] else ""))
            print("    title=%r  tagline=%r  bg=%s  url=%s" % (planned["title"][:60], d["tagline"], d["light"], d["url"]))
        else:
            print("%-18s %s" % (row["name"][:18], apply(planned)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
