"""Does a project have its four versions (Windows, Mac, iPhone, Android), and has each one been run?

What counts as published, read from what is really there and not from what a README claims:

    Windows   a download: a file in a GitHub release, or a direct link in the README that answers
              (.exe, .msi, an install script such as .cmd or .ps1, or a file named for win / windows)
    Mac       the same (.dmg, .pkg, or a file named for mac / macos / darwin)
    Android   an .apk (or .aab), in a release or linked from the README
    iPhone    the live web app, added to the home screen: the page answers, has an apple-touch-icon
              and opens as its own app (manifest `display: standalone`, or apple-mobile-web-app-capable)

The gate also fails when the README does not name all four, when a download the README links is not
there, and when a version was left behind (its newest build sits in an older release than the others).
A project that is no app at all is listed, with the reason, in `no_app.txt` next to this file.

Published is not run. `--run` starts what this computer can start (a Mac build on a Mac, a Windows build
on Windows, the iPhone web app's page, icon, start page and offline worker anywhere) and writes one line
per result to a ledger. Every computer keeps its own ledger in the brain, so the gate can say which
computer ran which upload, and which uploads nobody has run.

    python platforms.py --repo juw12/ruang                       # one project; exit 1 = the gate fails
    python platforms.py --repo juw12/projects/apps/twin --demo https://juw12.github.io/projects/twin/
    python platforms.py PROFILE_README.md                        # every project the profile lists
    python platforms.py PROFILE_README.md --only twin
    python platforms.py ... --brain VAULT                        # show the runs every computer recorded
    python platforms.py ... --run --ledger VAULT/devices/<this computer>/notes/platform-runs.md
    python platforms.py ... --brain VAULT --need-run mac,iphone  # gate: those versions must have been run
    python platforms.py --selftest                               # offline checks

Standard library only; GitHub is read through `gh`. `--run` downloads the user's own release files into
a temporary folder, starts them for a few seconds, stops them and deletes the folder.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform as computer
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import featured  # noqa: E402  (same folder: how the profile is read and how GitHub and the web are asked)

PLATFORMS = ("Windows", "Mac", "iPhone", "Android")
ASSET = {
    "Windows": re.compile(r"\.(exe|msi|msix|cmd|bat|ps1)$|(^|[-_.])win(dows)?(32|64)?([-_.]|$)", re.I),
    "Mac": re.compile(r"\.(dmg|pkg|command)$|(^|[-_.])(mac|macos|osx|darwin)([-_.]|$)", re.I),
    "Android": re.compile(r"\.(apk|aab)$", re.I),
}
# Checksums, update feeds and pictures sit next to builds and carry their names; they are not builds.
NOT_A_BUILD = re.compile(r"\.(sha256|sig|asc|txt|ya?ml|json|png|jpe?g|gif|svg|md|html?|blockmap)$", re.I)
README_NAMES = {
    "Windows": re.compile(r"\bwindows\b", re.I),
    "Mac": re.compile(r"\bmac(os)?\b|\bos x\b", re.I),
    "iPhone": re.compile(r"\biphone\b|\bios\b", re.I),
    "Android": re.compile(r"\bandroid\b", re.I),
}
URL_RE = re.compile(r"""https?://[^\s)"'<>\]`]+""")
PROMISED_RE = re.compile(r"/releases/(latest/)?download/")
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.I)
ATTRIBUTE_RE = re.compile(r"""\b(rel|href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
CAPABLE_RE = re.compile(r"""<meta\b[^>]*\b(?:apple-)?mobile-web-app-capable\b[^>]*\bcontent\s*=\s*["']?yes""", re.I)
SCRIPT_RE = re.compile(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)""", re.I)
WORKER_RE = re.compile(r"""serviceWorker\s*\.\s*register\(\s*["'`]([^"'`]+)""")
OTHER_CHIP = {"x86_64": re.compile(r"arm64|aarch64|apple-?silicon", re.I), "arm64": re.compile(r"intel|x86_64|x64|amd64", re.I)}
INSTALLER_RE = re.compile(r"setup|install|\.(msi|msix|pkg|cmd|bat|ps1|command)$", re.I)
RUN_SECONDS = 12
RUN_WORD = {"ok": "RAN    ", "failed": "FAIL   ", "unclear": "UNCLEAR", "skipped": "not run"}
NO_APP_FILE = Path(__file__).resolve().parent / "no_app.txt"
LEDGER_HEAD = (
    "---\ntitle: Platform runs\ntype: note\ntags: [platforms, hone]\n---\n# Platform runs\n\nWritten by `platforms.py --run` on this computer: one line per upload it started. "
    "Other computers keep their own file.\n\n"
    "| when | computer | project | version | release | file | uploaded | result | how |\n|---|---|---|---|---|---|---|---|---|\n"
)


# ---------------------------------------------------------------- pure checks

def series(tag: str) -> str:
    """The part of a tag that stays the same from release to release: v1.3.0 -> "", glow-mac -> glow-mac."""
    return re.sub(r"[-_]?v?\d[\d.\-]*$", "", tag).lower()


def own_releases(releases: list, path: str, tag: str) -> list:
    """The releases of one project. A whole repo owns all of them; a folder of a monorepo owns the tags that
    start with its folder name or with the first word of the tag its profile card links (airiz-desktop-v1.2
    and airiz-mobile-v1.0 both belong to the folder apps/airiz-motor)."""
    if not path:
        return releases
    stems = {path.rsplit("/", 1)[-1].lower()}
    if tag:
        stems.update({series(tag), tag.split("-", 1)[0].lower()})
    stems.discard("")
    return [release for release in releases if any(release[0].lower() == stem or release[0].lower().startswith(stem + "-") for stem in stems)]


def is_build(name: str, platform: str) -> bool:
    return bool(ASSET[platform].search(name)) and not NOT_A_BUILD.search(name)


def find_builds(releases: list, platform: str) -> dict | None:
    """The newest release that carries a build for `platform`: {"tag", "assets", "behind"}. `behind` names a
    newer release of the same series that has downloads but none for this platform: the version left behind."""
    for index, (tag, assets) in enumerate(releases):
        mine = [asset for asset in assets if is_build(asset[0], platform)]
        if not mine:
            continue
        newer = next(
            (other_tag for other_tag, other_assets in releases[:index] if series(other_tag) == series(tag) and any(is_build(asset[0], other) for asset in other_assets for other in ASSET)),
            "",
        )
        return {"tag": tag, "assets": mine, "behind": newer}
    return None


def readme_downloads(readme: str) -> dict:
    """{"Windows": [links], ..., "promised": [links]}: direct download links the README gives a reader."""
    found = {platform: [] for platform in ASSET}
    found["promised"] = []
    for url in dict.fromkeys(match.rstrip(".,;:") for match in URL_RE.findall(readme or "")):
        if "<" in url or "{" in url or "img.shields.io" in url:
            continue  # a placeholder such as <version>, or a badge
        name = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
        if PROMISED_RE.search(url):
            found["promised"].append(url)
        for platform in ASSET:
            if name and is_build(name, platform):
                found[platform].append(url)
    return found


def link_tags(html: str) -> list[tuple[str, str]]:
    """(rel, href) of every <link> in the page, whatever order its attributes come in."""
    found = []
    for tag in LINK_TAG_RE.findall(html):
        attributes = {match.group(1).lower(): next(value for value in match.groups()[1:] if value is not None) for match in ATTRIBUTE_RE.finditer(tag)}
        found.append((attributes.get("rel", "").lower(), attributes.get("href", "")))
    return found


def home_screen(url: str, fetch) -> tuple[bool, str]:
    """Whether the page at `url` is a web app an iPhone can keep on its home screen, and why or why not."""
    if not url:
        return False, "no live web app to add to the home screen"
    final_url, html = fetch(url)
    if html is None:
        return False, f"{url} does not answer"
    links = link_tags(html)
    has_icon = any(rel.startswith("apple-touch-icon") and href for rel, href in links)
    own_app = bool(CAPABLE_RE.search(html))
    manifest = next((href for rel, href in links if rel == "manifest" and href), "")
    if manifest and not own_app:
        _, body = fetch(urllib.parse.urljoin(final_url, manifest))
        try:
            own_app = json.loads(body or "").get("display") in ("standalone", "fullscreen")
        except (ValueError, AttributeError):
            own_app = False
    lacks = [] if has_icon else ["an apple-touch-icon"]
    if not own_app:
        lacks.append("a manifest with display: standalone")
    if lacks:
        return False, f"{url} lacks {' and '.join(lacks)}"
    return True, f"home-screen web app at {url}"


def open_web_app(url: str, fetch) -> tuple[bool, str]:
    """What an iPhone fetches when the icon is tapped: the page, its touch icon, the manifest's start page and
    the offline worker. No browser engine is involved, so this proves the parts are there, not how it looks."""
    final_url, html = fetch(url)
    if html is None:
        return False, "the page does not answer"
    links = link_tags(html)
    icon = next((href for rel, href in links if rel.startswith("apple-touch-icon") and href), "")
    if not icon or not fetch(urllib.parse.urljoin(final_url, icon))[1]:
        return False, "the touch icon does not answer"
    manifest = next((href for rel, href in links if rel == "manifest" and href), "")
    if manifest:
        manifest_url = urllib.parse.urljoin(final_url, manifest)
        try:
            start = json.loads(fetch(manifest_url)[1] or "").get("start_url", "")
        except (ValueError, AttributeError):
            return False, "the manifest is not readable"
        if start and fetch(urllib.parse.urljoin(manifest_url, start))[1] is None:
            return False, f"the manifest's start page ({start}) does not answer"
    sources = [html] + [fetch(urllib.parse.urljoin(final_url, src))[1] or "" for src in SCRIPT_RE.findall(html)[:8] if not src.startswith(("http://", "https://", "//"))]
    worker = next((match.group(1) for source in sources for match in [WORKER_RE.search(source)] if match), "")
    offline = bool(worker) and fetch(urllib.parse.urljoin(final_url, worker))[1] is not None
    return True, "page, icon and start page answer; " + ("offline worker answers" if offline else "no offline worker found") + " (no browser engine)"


def pick_for_this_computer(assets: list, system: str, chip: str) -> tuple[list | None, str]:
    """The upload this computer can start, or (None, why not). Installers are not started: they change the computer."""
    wrong_chip = OTHER_CHIP.get(chip)
    fits = [asset for asset in assets if not (wrong_chip and wrong_chip.search(asset[0]))]
    if not fits:
        return None, f"no build for this computer's chip ({chip})"
    plain = [asset for asset in fits if not INSTALLER_RE.search(asset[0]) or (system == "Darwin" and asset[0].lower().endswith(".dmg"))]
    if not plain:
        return None, "only an installer is published: not started by a script"
    return sorted(plain, key=lambda asset: ("universal" not in asset[0].lower(), asset[0].lower()))[0], ""


def inspect(releases: list | None, demo: str, readme: str | None, fetch) -> dict:
    """Per platform {"ok", "how", "stale", "tag", "assets"}, plus "README" (platforms it does not name) and
    "broken" (downloads it links that are not there)."""
    links = readme_downloads(readme or "")
    result = {}
    for platform in ASSET:
        found = find_builds(releases or [], platform)
        if found:
            names = ", ".join(asset[0] for asset in found["assets"][:2]) + (" ..." if len(found["assets"]) > 2 else "")
            result[platform] = {"ok": True, "how": f"{names} ({found['tag']})", "stale": found["behind"], "tag": found["tag"], "assets": found["assets"]}
            continue
        live = next((url for url in links[platform] if fetch(url)[1] is not None), "")
        why = "releases could not be read" if releases is None else "no build in any release, none linked in the README"
        result[platform] = {"ok": bool(live), "how": f"linked in the README: {live}" if live else why, "stale": "", "tag": "", "assets": []}
    ok, how = home_screen(demo, fetch)
    result["iPhone"] = {"ok": ok, "how": how, "stale": "", "tag": "", "assets": [], "url": demo}
    result["README"] = [platform for platform in PLATFORMS if readme is None or not README_NAMES[platform].search(readme)]
    result["broken"] = [url for url in links["promised"] if fetch(url)[1] is None]
    return result


def gaps(result: dict, runs: dict | None = None, need_run: tuple = ()) -> list[str]:
    """Everything that keeps the gate from passing, as short phrases. Empty = pass."""
    if result.get("no_app"):
        return []
    found = [f"{platform} missing" for platform in PLATFORMS if not result[platform]["ok"]]
    found += [f"{platform} left behind at {result[platform]['tag']} (newest is {result[platform]['stale']})" for platform in PLATFORMS if result[platform]["stale"]]
    if result["README"]:
        found.append("README does not name " + ", ".join(result["README"]))
    found += [f"README links a download that is not there: {url}" for url in result["broken"]]
    found += [f"{platform} published but not run" for platform in need_run if result[platform]["ok"] and not run_of(result, platform, runs or {})]
    return found


# ---------------------------------------------------------------- the ledger of runs

def upload_key(project_key: str, platform: str, release: str, file: str, uploaded: str) -> tuple:
    return (project_key.lower(), platform.lower(), release, file, uploaded)


def read_ledgers(paths: list[Path]) -> dict:
    """{upload key: newest line about it} from every ledger given. A line is the dict of its table cells."""
    runs: dict = {}
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != 9 or cells[0] in ("when", "---"):
                continue
            row = dict(zip(("when", "computer", "project", "version", "release", "file", "uploaded", "result", "how"), cells))
            key = upload_key(row["project"], row["version"], row["release"], row["file"], row["uploaded"])
            if key not in runs or row["when"] >= runs[key]["when"]:  # a later line of the same minute wins
                runs[key] = row
    return runs


def write_run(ledger: Path, row: dict) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if not ledger.exists():
        ledger.write_text(LEDGER_HEAD, encoding="utf-8")
    cells = [str(row[name]).replace("|", "/").replace("\n", " ") for name in ("when", "computer", "project", "version", "release", "file", "uploaded", "result", "how")]
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("| " + " | ".join(cells) + " |\n")


def run_of(result: dict, platform: str, runs: dict) -> dict | None:
    """The recorded run of what is published now for `platform` (an `ok` one), or None: nobody ran this upload."""
    entry = result[platform]
    candidates = [("web", entry.get("url", ""), "")] if platform == "iPhone" else [(entry["tag"], asset[0], asset[1]) for asset in entry["assets"]]
    for release, file, uploaded in candidates:
        row = runs.get(upload_key(result.get("key", ""), platform, release, file, uploaded))
        if row and row["result"] == "ok":
            return row
    return None


# ---------------------------------------------------------------- the facts (read only)

def web_fetch(url: str) -> tuple[str, str | None]:
    """(address after redirects, text) or (url, None) when the page does not answer. Asked as an iPhone would."""
    return featured.web_get(url, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) hone-platforms")


def repo_releases(slug: str) -> list | None:
    """Every release of a repo, newest first, as [tag, [[file, uploaded, size], ...]]. None when GitHub could not be asked."""
    code, out = featured.gh("--paginate", f"repos/{slug}/releases?per_page=100", "--jq", ".[] | [.tag_name, [.assets[] | [.name, .updated_at, .size]]] | @json")
    return [json.loads(line) for line in out.splitlines() if line.strip()] if code == 0 else None


def read_readme(slug: str, path: str) -> str | None:
    code, out = featured.gh(f"repos/{slug}/readme" + (f"/{path}" if path else ""), "-H", "Accept: application/vnd.github.raw")
    return out if code == 0 else None


def no_app_list() -> dict:
    """{project key: reason} from no_app.txt: projects that are no app, so there is nothing to version."""
    listed = {}
    if NO_APP_FILE.exists():
        for line in NO_APP_FILE.read_text(encoding="utf-8").splitlines():
            entry, _, reason = line.partition("#")
            if entry.strip():
                listed[entry.strip().lower().rstrip("/")] = reason.strip() or "no reason given"
    return listed


def check_project(project: dict, releases: list | None, exempt: dict) -> dict:
    slug = f"{project['owner']}/{project['repo']}"
    key = featured.key_of(project)
    if key in exempt:
        return {"no_app": exempt[key], "key": key}
    demo = project["demo"]
    if not demo and not project["path"]:
        code, out = featured.gh(f"repos/{slug}", "--jq", '.homepage // ""')
        demo = out.strip() if code == 0 else ""
    owned = None if releases is None else own_releases(releases, project["path"], project["tag"])
    result = inspect(owned, demo, read_readme(slug, project["path"]), web_fetch)
    result["key"] = key
    return result


def check_all(projects: list[dict]) -> list[dict]:
    exempt = no_app_list()
    slugs = sorted({f"{project['owner']}/{project['repo']}" for project in projects})
    with ThreadPoolExecutor(max_workers=8) as pool:
        releases = dict(zip(slugs, pool.map(repo_releases, slugs)))
        return list(pool.map(lambda project: check_project(project, releases[f"{project['owner']}/{project['repo']}"], exempt), projects))


# ---------------------------------------------------------------- running a build on this computer

def this_computer() -> str:
    if computer.system() == "Darwin":
        try:
            return subprocess.run(["sysctl", "-n", "hw.model"], capture_output=True, text=True, timeout=10).stdout.strip() or computer.node()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return computer.node() or "this computer"


def find_program(folder: Path) -> Path | None:
    """The thing to start inside an unpacked download: a Mac app's own executable, a Windows .exe, or a lone binary."""
    for app in sorted(folder.rglob("*.app"), key=lambda path: len(path.parts)):
        try:
            name = plistlib.loads((app / "Contents" / "Info.plist").read_bytes()).get("CFBundleExecutable", "")
        except (OSError, ValueError):
            continue
        if name and (app / "Contents" / "MacOS" / name).exists():
            return app / "Contents" / "MacOS" / name
    if computer.system() == "Windows":
        programs = [path for path in folder.rglob("*.exe") if not INSTALLER_RE.search(path.name.replace(".exe", ""))]
    else:
        programs = [path for path in folder.rglob("*") if path.is_file() and os.access(path, os.X_OK) and path.read_bytes()[:4] in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xcf", b"\x7fELF")]
    return min(programs, key=lambda path: (len(path.parts), len(path.name))) if programs else None


def screen_locked() -> bool:
    """A Mac with its screen locked kills an app that asks for the microphone or the screen: no fair test."""
    if computer.system() != "Darwin":
        return False
    try:
        return '"CGSSessionScreenIsLocked" = Yes' in subprocess.run(["ioreg", "-n", "Root", "-d1"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def processes_under(folder: Path) -> list[int]:
    """Every process started from a file under `folder` (its real path: /tmp is /private/tmp on a Mac)."""
    out = subprocess.run(["pgrep", "-f", "^" + re.escape(str(folder.resolve()) + os.sep)], capture_output=True, text=True).stdout
    return [int(pid) for pid in out.split()]


def stop(pids: list[int]) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and any(_alive(pid) for pid in pids):
            time.sleep(0.25)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def open_mac_app(bundle: Path, seconds: int = RUN_SECONDS) -> tuple[str, str]:
    """Open a Mac app the way a double-click does (LaunchServices), behind the other windows, watch it, stop
    it. Started as a bare program instead, an app that asks for the microphone or the screen is killed by
    macOS before it shows anything, which says nothing about the app."""
    reports = Path.home() / "Library" / "Logs" / "DiagnosticReports"
    before = set(os.listdir(reports)) if reports.is_dir() else set()
    try:
        if subprocess.run(["open", "-n", "-g", str(bundle)], capture_output=True, timeout=60).returncode != 0:
            return "failed", "macOS refused to open it"
    except (OSError, subprocess.TimeoutExpired):
        return "failed", "macOS did not open it"
    deadline, seen, alive = time.monotonic() + seconds, False, []
    while time.monotonic() < deadline:
        alive = processes_under(bundle)
        seen = seen or bool(alive)
        if seen and not alive:
            break
        time.sleep(0.5)
    stop(processes_under(bundle))
    if alive:
        return "ok", f"opened and stayed up {seconds} s"
    crashed = [name for name in sorted(set(os.listdir(reports)) - before) if name.lower().startswith(bundle.stem.lower())] if reports.is_dir() else []
    if crashed:
        return "failed", f"crashed after opening (report {crashed[-1]})"
    if not seen:
        return "unclear", "opened, but it was gone before it could be seen: a launcher that hands over and leaves, or it failed at once"
    twin = subprocess.run(["pgrep", "-f", f"/{re.escape(bundle.name)}/Contents/MacOS/"], capture_output=True, text=True).stdout.split()
    return "unclear", "opened, then left by itself" + (": a copy of it is already running on this computer" if twin else "")


def start_and_stop(program: Path, log_folder: Path, seconds: int = RUN_SECONDS) -> tuple[str, str]:
    """Start a bare program, watch it, stop it. It ran when it is still up after `seconds`, or left with code 0."""
    log = log_folder / "hone-run.log"
    options = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)} if computer.system() == "Windows" else {"start_new_session": True}
    try:
        with log.open("wb") as output:
            process = subprocess.Popen([str(program)], stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=str(log_folder), **options)
    except OSError as error:
        return "failed", f"could not be started: {error}"
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and process.poll() is None:
        time.sleep(0.25)
    code = process.poll()
    if code is None:
        try:
            os.killpg(process.pid, signal.SIGTERM) if computer.system() != "Windows" else process.terminate()
            process.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
        return "ok", f"started and stayed up {seconds} s"
    said = " ".join(log.read_text(encoding="utf-8", errors="replace").split())[-160:]
    return ("ok", "started and left by itself with code 0") if code == 0 else ("failed", f"left with code {code}" + (f": {said}" if said else ""))


def run_build(slug: str, tag: str, asset: list) -> tuple[str, str]:
    """Download one release file into a temporary folder, start what is in it, stop it, delete the folder.
    Returns ("ok" | "failed" | "unclear" | "skipped", what happened)."""
    name, _, size = asset
    work = Path(tempfile.mkdtemp(prefix="hone-run-"))
    mounted = None
    try:
        unpacked = 4 if name.lower().endswith((".zip", ".tar.gz", ".tgz")) else 1.2  # a disk image is opened in place
        if shutil.disk_usage(work).free < unpacked * size + 200_000_000:
            return "skipped", "too little free disk to unpack it"
        code = subprocess.run([featured.gh_program(), "release", "download", tag, "-R", slug, "-p", name, "-D", str(work)], capture_output=True, timeout=900).returncode
        file = work / name
        if code != 0 or not file.exists():
            return "failed", "the file could not be downloaded"
        if file.stat().st_size < 4096:
            return "failed", f"the file is {file.stat().st_size} bytes: not a build"
        lower = name.lower()
        inside = work / "inside"
        inside.mkdir()
        if lower.endswith(".dmg"):
            if subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", str(inside), str(file)], capture_output=True, timeout=180).returncode != 0:
                return "failed", "the disk image does not open"
            mounted = inside
        elif lower.endswith(".zip"):
            if computer.system() == "Darwin":  # ditto keeps the permissions and links a Mac app needs; zipfile does not
                if subprocess.run(["ditto", "-x", "-k", str(file), str(inside)], capture_output=True, timeout=300).returncode != 0:
                    return "failed", "the zip does not unpack"
            else:
                zipfile.ZipFile(file).extractall(inside)
        elif lower.endswith((".tar.gz", ".tgz")):
            with tarfile.open(file) as archive:
                archive.extractall(inside)
        else:
            shutil.copy2(file, inside / name)
            (inside / name).chmod(0o755)
        program = find_program(inside)
        if not program:
            return "failed", "nothing to start was found inside it"
        if computer.system() != "Darwin":
            return start_and_stop(program, work)
        chips = subprocess.run(["lipo", "-archs", str(program)], capture_output=True, text=True).stdout.split()
        if chips and computer.machine() not in chips:
            return "skipped", f"built for {' '.join(chips)}, this Mac is {computer.machine()}"
        bundle = next((parent for parent in program.parents if parent.suffix == ".app"), None)
        accepted = subprocess.run(["spctl", "--assess", "--type", "execute", str(bundle or program)], capture_output=True).returncode == 0
        note = "" if accepted else "; not notarised, so a downloaded copy needs right-click > Open the first time"
        if bundle and screen_locked():
            return "skipped", "the screen is locked, and a Mac app opened behind a locked screen is no fair test"
        state, how = open_mac_app(bundle) if bundle else start_and_stop(program, work)
        return state, how + note
    except (OSError, subprocess.TimeoutExpired, zipfile.BadZipFile, tarfile.TarError) as error:
        return "failed", f"could not be unpacked or started: {error}"
    finally:
        if mounted:
            subprocess.run(["hdiutil", "detach", "-force", str(mounted)], capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


def run_project(project: dict, result: dict, ledger: Path | None, which: set) -> list[str]:
    """Run what this computer can run of one project. Returns the lines to print; writes each result to the ledger."""
    if result.get("no_app"):
        return []
    system, chip, lines = computer.system(), computer.machine().replace("AMD64", "x86_64"), []
    here = {"Darwin": "Mac", "Windows": "Windows"}.get(system)
    jobs = []
    if here and here.lower() in which and result[here]["ok"] and result[here]["assets"]:
        asset, why_not = pick_for_this_computer(result[here]["assets"], system, chip)
        if asset:
            jobs.append((here, result[here]["tag"], asset[0], asset[1], lambda asset=asset: run_build(f"{project['owner']}/{project['repo']}", result[here]["tag"], asset)))
        else:
            lines.append(f"  {here:<8} not run: {why_not}")
    if "iphone" in which and result["iPhone"]["ok"]:
        jobs.append(("iPhone", "web", result["iPhone"]["url"], "", lambda: (lambda ok, how: ("ok" if ok else "failed", how))(*open_web_app(result["iPhone"]["url"], web_fetch))))
    for platform, release, file, uploaded, job in jobs:
        state, how = job()
        lines.append(f"  {platform:<8} {RUN_WORD[state]}  {file}: {how}")
        if ledger and state != "skipped":
            write_run(ledger, {
                "when": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "computer": this_computer(), "project": result["key"], "version": platform,
                "release": release, "file": file, "uploaded": uploaded, "result": state, "how": how,
            })
    return lines


# ---------------------------------------------------------------- report

def one_report(name: str, result: dict, runs: dict, need_run: tuple) -> str:
    if result.get("no_app"):
        return f"{name}\n  no app: {result['no_app']} (no_app.txt)\nGATE PASS: nothing to version."
    lines = [name]
    for platform in PLATFORMS:
        entry = result[platform]
        state = "MISSING" if not entry["ok"] else "OLD    " if entry["stale"] else "yes    "
        ran = run_of(result, platform, runs)
        tail = "" if not entry["ok"] else f" · run on {ran['computer']} {ran['when'][:10]}: {ran['how']}" if ran else " · not run by any computer"
        lines.append(f"  {platform:<8} {state}  {entry['how']}{tail}")
    lines.append("  README   " + ("names all four" if not result["README"] else "does not name: " + ", ".join(result["README"])))
    problems = gaps(result, runs, need_run)
    lines.append("GATE PASS: all four versions are published and named." if not problems else "GATE FAIL: " + "; ".join(problems))
    return "\n".join(lines)


def table(projects: list[dict], results: list[dict], runs: dict) -> str:
    def mark(result: dict, platform: str) -> str:
        entry = result[platform]
        return " - " if not entry["ok"] else "OLD" if entry["stale"] else "RUN" if run_of(result, platform, runs) else "yes"

    lines = [f"{'project':<26}{'Win':>5}{'Mac':>5}{'iPhone':>8}{'Android':>9}   section", "(RUN = published and run by a computer, yes = published, OLD = left behind, - = missing)"]
    apps = [(project, result) for project, result in zip(projects, results) if not result.get("no_app")]
    for project, result in sorted(apps, key=lambda row: (sum(1 for platform in PLATFORMS if not row[1][platform]["ok"]), row[0]["name"].lower())):
        lines.append(f"{project['name'][:25]:<26}" + "".join(f"{mark(result, platform):>{width}}" for platform, width in zip(PLATFORMS, (5, 5, 8, 9))) + f"   {project['section']}")
    lines.append("")
    complete = sum(1 for _, result in apps if all(result[platform]["ok"] for platform in PLATFORMS))
    lines.append(f"All four published: {complete} of {len(apps)} apps. " + ", ".join(f"{platform} {sum(1 for _, result in apps if result[platform]['ok'])}" for platform in PLATFORMS) + ".")
    published = sum(1 for _, result in apps for platform in PLATFORMS if result[platform]["ok"])
    lines.append(f"Run by a computer: {sum(1 for _, result in apps for platform in PLATFORMS if run_of(result, platform, runs))} of {published} published versions.")
    passing = [project["name"] for project, result in apps if not gaps(result)]
    lines.append(f"Gate passes (published, named, no dead link, nothing left behind): {len(passing)}" + (": " + ", ".join(passing) if passing else "") + ".")
    for project, result in apps:
        extra = [gap for gap in gaps(result) if "missing" not in gap]
        if extra and all(result[platform]["ok"] for platform in PLATFORMS):
            lines.append(f"  {project['name']}: " + "; ".join(extra))
    skipped = [(project["name"], result["no_app"]) for project, result in zip(projects, results) if result.get("no_app")]
    if skipped:
        lines.append("No app, so nothing to version (no_app.txt): " + "; ".join(f"{name} ({reason})" for name, reason in skipped) + ".")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    failures = []

    def expect(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        if not condition:
            failures.append(label)

    kind = lambda name: [platform for platform in ASSET if is_build(name, platform)]
    real_names = {
        "Buddy-win64.zip": ["Windows"], "Buddy-mac.zip": ["Mac"], "EarlyStar-Setup-x64.exe": ["Windows"], "EarlyStar-macOS.dmg": ["Mac"],
        "Ruang-1.3.0-android.apk": ["Android"], "Twin-macOS-Intel.dmg": ["Mac"], "Twin-Windows-Portable.zip": ["Windows"],
        "spry-macos-universal.tar.gz": ["Mac"], "kilat.exe": ["Windows"], "Cairn-Setup.cmd": ["Windows"], "mac-install.sh": ["Mac"],
        "Tagalong-unsigned.ipa": [], "cairn.mcpb": [], "Spry-macos.zip.sha256": [], "SHA256SUMS.txt": [], "latest.yml": [],
        "spry-linux-x64.tar.gz": [], "AIRIZ-Mobile-1.0-ios-project.zip": [], "sync-iphone-simulator.png": [], "Twin-notes.zip": [],
    }
    expect("files are told apart by platform, and 'Twin' is not Windows", all(kind(name) == wanted for name, wanted in real_names.items()))
    asset = lambda name, uploaded="2026-01-01": [name, uploaded, 5_000_000]
    releases = [["glow-mac", [asset("Glow-mac.dmg")]], ["airiz-mobile-v1.0.7", [asset("A-android.apk")]], ["twin", [asset("Twin-Windows-Setup.exe")]], ["glow-windows", [asset("Glow-Setup.exe")]], ["airiz-desktop-v1.11.29", [asset("A-Setup-x64.exe")]]]
    expect("a monorepo folder owns the tags that start with its name", [r[0] for r in own_releases(releases, "apps/glow", "glow-windows")] == ["glow-mac", "glow-windows"])
    expect("...or with the first word of the tag its card links", [r[0] for r in own_releases(releases, "apps/airiz-motor", "airiz-desktop-v1.11.25")] == ["airiz-mobile-v1.0.7", "airiz-desktop-v1.11.29"])
    expect("...and nobody else's; a whole repo owns every release", [r[0] for r in own_releases(releases, "apps/twin", "")] == ["twin"] and own_releases(releases, "", "") == releases)

    buddy = [["v1.10.0", [asset("Buddy-win64.zip")]], ["v1.9.0", [asset("Buddy-win64.zip")]], ["v1.6.0", [asset("Buddy-win64.zip"), asset("Buddy-mac.zip")]]]
    expect("a version left behind is named with the release that passed it", find_builds(buddy, "Mac")["behind"] == "v1.10.0" and find_builds(buddy, "Windows")["behind"] == "")
    expect("tags of different series do not leave each other behind", find_builds(releases, "Windows")["behind"] == "" and series("glow-mac") != series("glow-windows") and series("v1.3.0") == series("v2.0.1-3") == "")

    pages = {
        "https://a.dev/": '<link rel="manifest" href="m.webmanifest"><link href="i.png" rel="apple-touch-icon"><script src="app.js"></script>',
        "https://a.dev/m.webmanifest": '{"display": "standalone", "start_url": "./?source=pwa"}',
        "https://a.dev/?source=pwa": "<h1>app</h1>", "https://a.dev/i.png": "PNG", "https://a.dev/app.js": 'navigator.serviceWorker.register("sw.js")', "https://a.dev/sw.js": "self",
        "https://b.dev/": "<link rel='manifest' href='m.json'><link rel=apple-touch-icon href=i.png>", "https://b.dev/m.json": '{"display": "browser"}',
        "https://c.dev/": '<meta name="apple-mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="gone.png">',
        "https://d.dev/": "<h1>a landing page</h1>", "https://x.dev/Cairn-Setup.cmd": "@echo off",
    }
    fetch = lambda url: (url, pages.get(url))
    expect("manifest standalone + touch icon is a home-screen app", home_screen("https://a.dev/", fetch)[0])
    expect("a manifest that opens in the browser is not", home_screen("https://b.dev/", fetch) == (False, "https://b.dev/ lacks a manifest with display: standalone"))
    expect("a plain page, a dead link and no link at all are not", not home_screen("https://d.dev/", fetch)[0] and not home_screen("https://gone.dev/", fetch)[0] and not home_screen("", fetch)[0])
    expect("opening it: page, icon, start page and offline worker all answer", open_web_app("https://a.dev/", fetch) == (True, "page, icon and start page answer; offline worker answers (no browser engine)"))
    expect("opening it: a touch icon that is not there fails", open_web_app("https://c.dev/", fetch) == (False, "the touch icon does not answer"))

    readme = (
        "Windows: [Download](https://x.dev/Cairn-Setup.cmd). Mac: https://github.com/me/app/releases/latest/download/App-macOS.dmg, "
        "`Ruang-<version>-windows-x64.exe`, ![b](https://img.shields.io/badge/win-ok.svg). iPhone: Add to Home Screen. Android: soon."
    )
    links = readme_downloads(readme)
    expect("README download links are found by platform; placeholders and badges are not", links["Windows"] == ["https://x.dev/Cairn-Setup.cmd"] and links["Mac"] == links["promised"] == ["https://github.com/me/app/releases/latest/download/App-macOS.dmg"])
    result = inspect([], "https://a.dev/", readme, fetch)
    result["key"] = "me/app"
    expect("an installer linked from the README counts when it answers", result["Windows"]["ok"] and "Cairn-Setup.cmd" in result["Windows"]["how"])
    expect("a promised download that is not there fails the gate", not result["Mac"]["ok"] and any("not there" in gap for gap in gaps(result)))
    expect("a README that leaves a platform out is caught; 'machine' is not Mac", inspect([], "", "A Windows machine with Macros.", fetch)["README"] == ["Mac", "iPhone", "Android"])
    expect("unreadable releases are not reported as 'no build'", inspect(None, "", "", fetch)["Mac"]["how"] == "releases could not be read")

    mac_assets = [asset("Twin-macOS-AppleSilicon.dmg"), asset("Twin-macOS-Intel.dmg")]
    expect("the build for this computer's chip is picked", pick_for_this_computer(mac_assets, "Darwin", "x86_64")[0][0] == "Twin-macOS-Intel.dmg" and pick_for_this_computer(mac_assets, "Darwin", "arm64")[0][0] == "Twin-macOS-AppleSilicon.dmg")
    expect("a universal build wins; an installer is not started", pick_for_this_computer([asset("spry-macos.zip"), asset("spry-macos-universal.tar.gz")], "Darwin", "arm64")[0][0] == "spry-macos-universal.tar.gz" and pick_for_this_computer([asset("X-Windows-Setup.exe")], "Windows", "x86_64")[0] is None)
    expect("a portable Windows build is picked over the installer", pick_for_this_computer([asset("X-Windows-Setup.exe"), asset("X-Windows-Portable.zip")], "Windows", "x86_64")[0][0] == "X-Windows-Portable.zip")

    with tempfile.TemporaryDirectory() as folder:
        mine, other = Path(folder) / "devices" / "mac" / "notes" / "platform-runs.md", Path(folder) / "devices" / "pc" / "notes" / "platform-runs.md"
        full = inspect([["v2", [asset("App-macOS.dmg", "2026-02-02"), asset("App-Setup.exe")]]], "https://a.dev/", "Windows Mac iPhone Android", fetch)
        full["key"] = "me/app"
        row = {"when": "2026-02-03 10:00", "computer": "Mac A", "project": "me/app", "version": "Mac", "release": "v2", "file": "App-macOS.dmg", "uploaded": "2026-02-02", "result": "ok", "how": "started | stayed up"}
        write_run(mine, row)
        write_run(other, {**row, "computer": "PC B", "version": "Windows", "file": "App-Setup.exe", "uploaded": "2026-01-01", "result": "failed", "how": "left with code 1"})
        runs = read_ledgers([mine, other])
        expect("a run is found again in the ledgers of every computer", run_of(full, "Mac", runs)["computer"] == "Mac A" and "|" not in run_of(full, "Mac", runs)["how"])
        expect("a failed run is not a run", run_of(full, "Windows", runs) is None)
        full["Mac"]["assets"][0][1] = "2026-03-03"
        expect("a new upload under the same name has not been run", run_of(full, "Mac", runs) is None)
        expect("--need-run turns 'published but not run' into a gate failure", "Mac published but not run" in gaps(full, runs, ("Mac",)) and "Mac published but not run" not in gaps(full, runs, ()))
    expect("a project listed as no app passes with its reason", gaps({"no_app": "model files", "key": "me/models"}) == [])
    expect("the real no_app.txt reads as project: reason", all("/" in key and reason != "no reason given" for key, reason in no_app_list().items()))
    print(f"  {'OK' if not failures else 'FAILED'}: platforms selftest")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("profile", nargs="?", help="README.md of the profile repo: check every project it lists")
    parser.add_argument("--repo", help="one project: OWNER/REPO, or OWNER/REPO/path/in/the/monorepo")
    parser.add_argument("--demo", default="", help="--repo: its live web app (default: the repo's homepage)")
    parser.add_argument("--tag", default="", help="--repo: a release tag of a monorepo project, when its tags do not start with the folder name")
    parser.add_argument("--only", default="", help="profile: only the project with this name")
    parser.add_argument("--brain", default=os.environ.get("CAIRN_BRAIN", ""), help="the vault: read every computer's devices/*/notes/platform-runs.md")
    parser.add_argument("--run", nargs="?", const="mac,windows,iphone", default="", help="start what this computer can start, for a few seconds each; optionally only some: --run mac")
    parser.add_argument("--ledger", default="", help="--run: this computer's own ledger file to add the results to")
    parser.add_argument("--need-run", default="", help="gate: these versions must have been run, e.g. mac,iphone")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.repo:
        parts = args.repo.strip("/").split("/")
        if len(parts) < 2:
            parser.error("--repo needs OWNER/REPO")
        projects = [{"name": args.repo, "section": "", "owner": parts[0], "repo": parts[1], "path": "/".join(parts[2:]), "branch": "", "demo": args.demo, "tag": args.tag}]
    elif args.profile:
        projects = [project for project in featured.read_projects(Path(args.profile).read_text(encoding="utf-8")) if project["section"] != "Archive"]
        if args.only:
            projects = [project for project in projects if project["name"].lower() == args.only.lower()]
            if not projects:
                raise SystemExit(f"The profile lists no project named '{args.only}'.")
    else:
        parser.error("give --repo OWNER/REPO or the profile README.md")
    need_run = tuple(platform for platform in PLATFORMS if platform.lower() in {name.strip().lower() for name in args.need_run.split(",")})
    ledger = Path(args.ledger) if args.ledger else None
    ledgers = (sorted(Path(args.brain).glob("devices/*/notes/platform-runs.md")) if args.brain else []) + ([ledger] if ledger else [])
    results = check_all(projects)
    if args.run:
        for project, result in zip(projects, results):
            lines = run_project(project, result, ledger, {name.strip().lower() for name in args.run.split(",")})
            if lines:
                print(f"{project['name']}\n" + "\n".join(lines), flush=True)
        print()
    runs = read_ledgers(ledgers)
    if args.json:
        print(json.dumps([
            {"name": project["name"], "section": project["section"], "noApp": result.get("no_app", ""), "gaps": gaps(result, runs, need_run),
             **({} if result.get("no_app") else {platform: {"ok": result[platform]["ok"], "how": result[platform]["how"], "run": bool(run_of(result, platform, runs))} for platform in PLATFORMS})}
            for project, result in zip(projects, results)
        ], indent=1))
    elif len(projects) == 1:
        print(one_report(projects[0]["name"], results[0], runs, need_run))
    else:
        print(table(projects, results, runs))
    return 1 if any(gaps(result, runs, need_run) for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
