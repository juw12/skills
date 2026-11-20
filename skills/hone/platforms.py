"""Does a project have its four versions: Windows, Mac, iPhone and Android?

What counts, each read from what is really published and not from what a README says:

    Windows   a download in a GitHub release (.exe, .msi, or a file named for win / windows)
    Mac       a download in a GitHub release (.dmg, .pkg, or a file named for mac / macos / darwin)
    Android   an .apk (or .aab) in a GitHub release
    iPhone    the live web app, added to the home screen: the page answers, has an apple-touch-icon
              and opens as its own app (manifest `display: standalone`, or apple-mobile-web-app-capable)

and the project's README has to name all four, so a person can find them.

    python platforms.py --repo juw12/ruang                         # one project; exit 1 = a version is missing
    python platforms.py --repo juw12/projects/apps/twin --demo https://juw12.github.io/projects/twin/
    python platforms.py PROFILE_README.md                          # every project the profile lists, as a table
    python platforms.py PROFILE_README.md --only twin              # one of them, with its demo link from the profile
    python platforms.py --selftest                                 # offline checks

This says a version is published, not that it was run. Standard library only; GitHub is read through `gh`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import featured  # noqa: E402  (same folder: how the profile is read and how GitHub is asked)

PLATFORMS = ("Windows", "Mac", "iPhone", "Android")
ASSET = {
    "Windows": re.compile(r"\.(exe|msi|msix)$|(^|[-_.])win(dows)?(32|64)?([-_.]|$)", re.I),
    "Mac": re.compile(r"\.(dmg|pkg)$|(^|[-_.])(mac|macos|osx|darwin)([-_.]|$)", re.I),
    "Android": re.compile(r"\.(apk|aab)$", re.I),
}
# Checksums, update feeds and pictures sit next to builds and carry their names; they are not builds.
NOT_A_BUILD = re.compile(r"\.(sha256|sig|asc|txt|ya?ml|json|png|jpe?g|blockmap)$", re.I)
README_NAMES = {
    "Windows": re.compile(r"\bwindows\b", re.I),
    "Mac": re.compile(r"\bmac(os)?\b|\bos x\b", re.I),
    "iPhone": re.compile(r"\biphone\b|\bios\b", re.I),
    "Android": re.compile(r"\bandroid\b", re.I),
}
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.I)
ATTRIBUTE_RE = re.compile(r"""\b(rel|href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
CAPABLE_RE = re.compile(r"""<meta\b[^>]*\b(?:apple-)?mobile-web-app-capable\b[^>]*\bcontent\s*=\s*["']?yes""", re.I)


# ---------------------------------------------------------------- pure checks

def own_releases(releases: list, path: str, tag: str) -> list:
    """The releases of one project. A whole repo owns all of them; a folder of a monorepo owns the tags that
    start with its folder name or with the first word of the tag its profile card links (airiz-desktop-v1.2
    and airiz-mobile-v1.0 both belong to the folder apps/airiz-motor)."""
    if not path:
        return releases
    stems = {path.rsplit("/", 1)[-1].lower()}
    if tag:
        stems.update({re.sub(r"-v?\d[\d.]*$", "", tag).lower(), tag.split("-", 1)[0].lower()})
    return [release for release in releases if any(release[0].lower() == stem or release[0].lower().startswith(stem + "-") for stem in stems)]


def find_build(releases: list, platform: str) -> tuple[str, str]:
    """(file, tag) of the newest release that carries a build for `platform`, or ("", "")."""
    for tag, names in releases:
        for name in names:
            if ASSET[platform].search(name) and not NOT_A_BUILD.search(name):
                return name, tag
    return "", ""


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


def inspect(releases: list | None, demo: str, readme: str | None, fetch) -> dict:
    """{platform: (ok, how)} for the four, plus "README": the platforms its README does not name."""
    result = {}
    for platform in ("Windows", "Mac", "Android"):
        name, tag = find_build(releases or [], platform)
        result[platform] = (True, f"{name} ({tag})") if name else (False, "releases could not be read" if releases is None else "no build in any release")
    result["iPhone"] = home_screen(demo, fetch)
    result["README"] = [platform for platform in PLATFORMS if readme is None or not README_NAMES[platform].search(readme)]
    return result


def missing(result: dict) -> list[str]:
    return [platform for platform in PLATFORMS if not result[platform][0]]


# ---------------------------------------------------------------- the facts (read only)

def web_fetch(url: str) -> tuple[str, str | None]:
    """(address after redirects, text) or (url, None) when the page does not answer. Asked as an iPhone would."""
    return featured.web_get(url, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) hone-platforms")


def repo_releases(slug: str) -> list | None:
    """Every release of a repo, newest first, as [tag, [file names]]. None when GitHub could not be asked."""
    code, out = featured.gh("--paginate", f"repos/{slug}/releases?per_page=100", "--jq", ".[] | [.tag_name, [.assets[].name]] | @json")
    return [json.loads(line) for line in out.splitlines() if line.strip()] if code == 0 else None


def read_readme(slug: str, path: str) -> str | None:
    code, out = featured.gh(f"repos/{slug}/readme" + (f"/{path}" if path else ""), "-H", "Accept: application/vnd.github.raw")
    return out if code == 0 else None


def check_project(project: dict, releases: list | None) -> dict:
    slug = f"{project['owner']}/{project['repo']}"
    demo = project["demo"]
    if not demo and not project["path"]:
        code, out = featured.gh(f"repos/{slug}", "--jq", '.homepage // ""')
        demo = out.strip() if code == 0 else ""
    owned = None if releases is None else own_releases(releases, project["path"], project["tag"])
    return inspect(owned, demo, read_readme(slug, project["path"]), web_fetch)


def check_all(projects: list[dict]) -> list[dict]:
    slugs = sorted({f"{project['owner']}/{project['repo']}" for project in projects})
    with ThreadPoolExecutor(max_workers=8) as pool:
        releases = dict(zip(slugs, pool.map(repo_releases, slugs)))
        return list(pool.map(lambda project: check_project(project, releases[f"{project['owner']}/{project['repo']}"]), projects))


# ---------------------------------------------------------------- report

def one_report(name: str, result: dict) -> str:
    lines = [name]
    for platform in PLATFORMS:
        ok, how = result[platform]
        lines.append(f"  {platform:<8} {'yes    ' if ok else 'MISSING'}  {how}")
    lines.append("  README   " + ("names all four" if not result["README"] else "does not name: " + ", ".join(result["README"])))
    gaps = missing(result) + ([f"README ({', '.join(result['README'])})"] if result["README"] else [])
    lines.append("GATE PASS: all four versions are published and named." if not gaps else "GATE FAIL: " + "; ".join(gaps))
    return "\n".join(lines)


def table(projects: list[dict], results: list[dict]) -> str:
    mark = lambda ok: "yes" if ok else " - "
    lines = [f"{'project':<26}{'Win':>5}{'Mac':>5}{'iPhone':>8}{'Android':>9}   section"]
    rows = sorted(zip(projects, results), key=lambda row: (len(missing(row[1])), row[0]["name"].lower()))
    for project, result in rows:
        lines.append(
            f"{project['name'][:25]:<26}{mark(result['Windows'][0]):>5}{mark(result['Mac'][0]):>5}{mark(result['iPhone'][0]):>8}{mark(result['Android'][0]):>9}   {project['section']}"
        )
    complete = sum(1 for result in results if not missing(result))
    lines.append("")
    lines.append(f"All four: {complete} of {len(results)} projects. " + ", ".join(f"{platform} {sum(1 for result in results if result[platform][0])}" for platform in PLATFORMS) + ".")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    failures = []

    def expect(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        if not condition:
            failures.append(label)

    kind = lambda name: [platform for platform in ASSET if ASSET[platform].search(name) and not NOT_A_BUILD.search(name)]
    real_names = {
        "Buddy-win64.zip": ["Windows"], "Buddy-mac.zip": ["Mac"], "EarlyStar-Setup-x64.exe": ["Windows"], "EarlyStar-macOS.dmg": ["Mac"],
        "Ruang-1.3.0-android.apk": ["Android"], "Twin-macOS-Intel.dmg": ["Mac"], "Twin-Windows-Portable.zip": ["Windows"],
        "spry-macos-universal.tar.gz": ["Mac"], "kilat.exe": ["Windows"], "Tagalong-unsigned.ipa": [], "cairn.mcpb": [],
        "Spry-macos.zip.sha256": [], "SHA256SUMS.txt": [], "latest.yml": [], "spry-linux-x64.tar.gz": [], "AIRIZ-Mobile-1.0-ios-project.zip": [],
    }
    expect("release files are told apart by platform", all(kind(name) == wanted for name, wanted in real_names.items()))
    expect("'Twin' is not a Windows build because of the letters w-i-n", kind("Twin-notes.zip") == [])
    releases = [["glow-mac", ["Glow-mac.dmg"]], ["airiz-mobile-v1.0.7", ["A-android.apk"]], ["twin", ["Twin-Windows-Setup.exe"]], ["glow-windows", ["Glow-Setup.exe"]], ["airiz-desktop-v1.11.29", ["A-Setup-x64.exe"]]]
    expect("a monorepo folder owns the tags that start with its name", [r[0] for r in own_releases(releases, "apps/glow", "glow-windows")] == ["glow-mac", "glow-windows"])
    expect("...or with the first word of the tag its card links", [r[0] for r in own_releases(releases, "apps/airiz-motor", "airiz-desktop-v1.11.25")] == ["airiz-mobile-v1.0.7", "airiz-desktop-v1.11.29"])
    expect("...and nobody else's", [r[0] for r in own_releases(releases, "apps/twin", "")] == ["twin"])
    expect("a whole repo owns every release", own_releases(releases, "", "") == releases)

    pages = {
        "https://a.dev/": '<link rel="manifest" href="m.webmanifest"><link href="i.png" rel="apple-touch-icon">',
        "https://a.dev/m.webmanifest": '{"display": "standalone"}',
        "https://b.dev/": "<link rel='manifest' href='m.json'><link rel=apple-touch-icon href=i.png>",
        "https://b.dev/m.json": '{"display": "browser"}',
        "https://c.dev/": '<meta name="apple-mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="i.png">',
        "https://d.dev/": "<h1>a landing page</h1>",
    }
    fetch = lambda url: (url, pages.get(url))
    expect("manifest standalone + touch icon is a home-screen app", home_screen("https://a.dev/", fetch)[0])
    expect("a manifest that opens in the browser is not", home_screen("https://b.dev/", fetch) == (False, "https://b.dev/ lacks a manifest with display: standalone"))
    expect("apple-mobile-web-app-capable counts without a manifest", home_screen("https://c.dev/", fetch)[0])
    expect("a plain page is not an app", "apple-touch-icon and a manifest" in home_screen("https://d.dev/", fetch)[1])
    expect("a dead link is not an app", home_screen("https://gone.dev/", fetch) == (False, "https://gone.dev/ does not answer"))
    expect("no live page at all is said plainly", not home_screen("", fetch)[0])

    result = inspect(own_releases(releases, "apps/glow", ""), "https://a.dev/", "Get it on Windows, macOS and Android. On iOS add it to the Home Screen.", fetch)
    expect("three of four published: only Android is missing", missing(result) == ["Android"] and result["README"] == [])
    expect("a README that leaves a platform out is caught", inspect([], "", "Windows only, runs on a mac mini too.", fetch)["README"] == ["iPhone", "Android"])
    expect("'machine' and 'Macro' do not name the Mac", inspect([], "", "A machine with Macros.", fetch)["README"] == list(PLATFORMS))
    expect("unreadable releases are not reported as 'no build'", inspect(None, "", "", fetch)["Mac"][1] == "releases could not be read")
    print(f"  {'OK' if not failures else 'FAILED'}: platforms selftest")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("profile", nargs="?", help="README.md of the profile repo: check every project it lists")
    parser.add_argument("--repo", help="one project: OWNER/REPO, or OWNER/REPO/path/in/the/monorepo")
    parser.add_argument("--demo", default="", help="--repo: its live web app (default: the repo's homepage)")
    parser.add_argument("--tag", default="", help="--repo: a release tag of a monorepo project, when its tags do not start with the folder name")
    parser.add_argument("--only", default="", help="profile: only the project with this name")
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
    results = check_all(projects)
    if args.json:
        print(json.dumps([{"name": project["name"], "section": project["section"], **{platform: {"ok": result[platform][0], "how": result[platform][1]} for platform in PLATFORMS}, "readmeLacks": result["README"]} for project, result in zip(projects, results)], indent=1))
    elif len(projects) == 1:
        print(one_report(projects[0]["name"], results[0]))
    else:
        print(table(projects, results))
    return 1 if any(missing(result) or result["README"] for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
