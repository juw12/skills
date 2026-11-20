"""Keep "Featured" on the GitHub profile to the best projects, best first, from facts and not from taste.

Reads the profile README (the clone of OWNER/OWNER), scores every project it lists and says what Featured
should be. A project is a whole repo or a folder of a monorepo (juw12/projects/apps/twin), so both compete.

    python featured.py README.md                  # the ranking and what would change (changes nothing)
    python featured.py README.md --write          # put the Featured cards in score order
    python featured.py README.md --check          # gate: exit 1 while Featured is out of order or outranked
    python featured.py README.md --brain VAULT    # also count Cairn's own ranking (notes/project-ranking.md)
    python featured.py --selftest                 # offline checks of the scoring and the rewrite

What the script decides: the order of the cards, and who should be swapped in (a project outside Featured
that beats the weakest card by MARGIN points). What it leaves to the editor: writing the new card and its
image, because copy is not a fact. Pins cannot be set by any GitHub API, so they are only listed.

Standard library only; GitHub is read through the GitHub CLI (`gh`), nothing is pushed from here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_OWNER = os.environ.get("HONE_GITHUB_OWNER", "juw12")
FEATURED = "Featured"
# Sections that keep their own cards: a project listed there is not moved into Featured.
NOT_IN_POOL = ("Engineering", "Archive")
MARGIN = 5  # points a project outside Featured must lead the weakest card by, so near ties do not flap
PINS = 6
GH_PLACES = ("/usr/local/bin/gh", "/opt/homebrew/bin/gh", r"C:\Program Files\GitHub CLI\gh.exe")

# (key, weight, what it measures). The profile promises this ranking in its own caption: test suites,
# shipped releases and downloads, a working live demo and commit history. A signal that could not be read
# is left out of that project's total instead of counting as zero.
SIGNALS = (
    ("tests", 20, "test files in the project"),
    ("releases", 16, "a shipped release, and its downloads"),
    ("demo", 14, "a live demo that answers right now"),
    ("history", 10, "commits in total"),
    ("momentum", 10, "commits in the last 30 days"),
    ("stars", 10, "stars of the repo"),
    ("ci", 6, "CI workflows in the repo"),
    ("cairn", 14, "Cairn's own ranking of the repo"),
)

TEST_FILE_RE = re.compile(r"(^|/)(tests?|__tests__|e2e|specs?)/|(^|/)test_[^/]+$|[._-](test|spec)\.[a-z]+$", re.I)
SECTION_RE = re.compile(r"^## (.+?)\s*$", re.M)
CARD_RE = re.compile(r'<td width="50%" valign="top">.*?</td>', re.S)
TABLE_RE = re.compile(r"<table>.*?</table>", re.S)
BULLET_RE = re.compile(r"^- \*\*\[(?P<name>[^\]]+)\]\((?P<url>[^)\s]+)\)\*\*.*$", re.M)
CARD_NAME_RE = re.compile(r'<b><a href="(?P<url>[^"]+)">(?P<name>[^<]+)</a></b>')
README_LINK_RE = re.compile(r"https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)(?:/tree/(?P<branch>[\w.-]+)/(?P<path>[^)\s\"#]+))?#readme")
BADGE_RE = re.compile(r"\[!\[Source\]\([^)]*\)\]\(https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)(?:/tree/(?P<branch>[\w.-]+)/(?P<path>[^)\s]+))?\)")
DEMO_RE = re.compile(r'(?:<a href="(?P<html>[^"]+)">Live (?:demo|site)</a>|\[Try the demo\]\((?P<md>[^)\s]+)\))')
TAG_RE = re.compile(r"/releases/tag/(?P<tag>[^)\s\"]+)")
RANK_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*\[[^\]]+\]\(https://github\.com/(?P<slug>[^)\s]+)\)[^|]*\|[^|]*\|\s*(?P<overall>\d+)\s*\|", re.M)


# ---------------------------------------------------------------- the README

def sections(text: str) -> list[tuple[str, int, int]]:
    """(title, start, end) of every `## ` section."""
    marks = list(SECTION_RE.finditer(text))
    return [(mark.group(1), mark.end(), marks[index + 1].start() if index + 1 < len(marks) else len(text)) for index, mark in enumerate(marks)]


def _entry(block: str, name: str, link: str, section: str, kind: str) -> dict | None:
    source = None
    for source in README_LINK_RE.finditer(block):
        pass  # the README link is the last one in a card and in a bullet
    source = source or BADGE_RE.search(block)
    if not source:
        return None
    demo = DEMO_RE.search(block)
    demo_url = (demo.group("html") or demo.group("md")) if demo else link
    tag = TAG_RE.search(block)
    return {
        "name": name.split(":")[0].strip(), "section": section, "kind": kind, "block": block,
        "owner": source.group("owner"), "repo": source.group("repo"),
        "branch": source.group("branch") or "", "path": (source.group("path") or "").strip("/"),
        "demo": "" if "//github.com/" in demo_url else demo_url, "tag": tag.group("tag") if tag else "",
    }


def key_of(entry: dict) -> str:
    return f"{entry['owner']}/{entry['repo']}/{entry['path']}".lower().rstrip("/")


def read_projects(text: str) -> list[dict]:
    """Every project the README lists, once, in reading order. Cards of Featured come first by definition."""
    found: dict[str, dict] = {}
    for title, start, end in sections(text):
        body = text[start:end]
        for card in CARD_RE.finditer(body):
            name = CARD_NAME_RE.search(card.group(0))
            entry = _entry(card.group(0), name.group("name"), name.group("url"), title, "card") if name else None
            if entry:
                found.setdefault(key_of(entry), entry)
        for bullet in BULLET_RE.finditer(body):
            entry = _entry(bullet.group(0), bullet.group("name"), bullet.group("url"), title, "bullet")
            if entry:
                found.setdefault(key_of(entry), entry)
    return list(found.values())


def rewrite_featured(text: str, ordered_blocks: list[str]) -> str:
    """The README with the Featured table rebuilt from `ordered_blocks`, two cards per row, cards untouched."""
    for title, start, end in sections(text):
        if title == FEATURED:
            table = TABLE_RE.search(text, start, end)
            if not table:
                break
            rows = []
            for index in range(0, len(ordered_blocks), 2):
                cells = "\n".join(f"    {block}" for block in ordered_blocks[index:index + 2])
                rows.append(f"  <tr>\n{cells}\n  </tr>")
            return text[:table.start()] + "<table>\n" + "\n".join(rows) + "\n</table>" + text[table.end():]
    raise SystemExit(f'No "## {FEATURED}" section with a table in this README.')


# ---------------------------------------------------------------- the score (pure)

def log_scale(value: float, full: float) -> float:
    """0 at zero, 1 at `full`, logarithmic between: the 10th test file matters more than the 90th."""
    return max(0.0, min(1.0, math.log10(1 + max(0.0, value)) / math.log10(1 + full)))


def signal_values(facts: dict) -> dict:
    """Each signal as 0..1, or None when the fact is not known."""
    known = lambda key: facts.get(key) is not None
    return {
        "tests": log_scale(facts["tests"], 100) if known("tests") else None,
        "releases": (0.4 * (facts["releases"] > 0) + 0.6 * log_scale(facts.get("downloads") or 0, 500)) if known("releases") else None,
        "demo": float(bool(facts["demo"])) if known("demo") else None,
        "history": log_scale(facts["commits"], 500) if known("commits") else None,
        "momentum": log_scale(facts["commits30"], 60) if known("commits30") else None,
        "stars": log_scale(facts["stars"], 50) if known("stars") else None,
        "ci": float(bool(facts["ci"])) if known("ci") else None,
        "cairn": facts["cairn"] / 100 if known("cairn") else None,
    }


def score(facts: dict) -> float:
    values = signal_values(facts)
    known = [(weight, values[key]) for key, weight, _ in SIGNALS if values[key] is not None]
    total = sum(weight for weight, _ in known)
    return round(100 * sum(weight * value for weight, value in known) / total, 1) if total else 0.0


def decide(projects: list[dict]) -> dict:
    """What Featured should be. Every project needs a `score`; the order of `projects` is the README's."""
    featured = [project for project in projects if project["section"] == FEATURED]
    # Scores a point apart are a tie, and a tie keeps the order the README already has.
    ordered = sorted(featured, key=lambda project: (-round(project["score"]), featured.index(project)))
    pool = sorted(
        (project for project in projects if project["section"] != FEATURED and project["section"] not in NOT_IN_POOL and not project.get("archived")),
        key=lambda project: -project["score"],
    )
    swaps = []
    for challenger, weakest in zip(pool, sorted(featured, key=lambda project: project["score"])):
        if challenger["score"] < weakest["score"] + MARGIN:
            break
        swaps.append((challenger, weakest))
    return {"featured": featured, "ordered": ordered, "reorder": [p["name"] for p in ordered] != [p["name"] for p in featured], "swaps": swaps, "pool": pool}


def wanted_pins(decision: dict, pinned: list[str] | tuple = ()) -> list[str]:
    """Repos to pin: those behind the Featured cards, best first, then the best whole repos outside it.
    For those free slots a repo that is pinned already stays unless a newcomer leads it by MARGIN."""
    slug = lambda project: f"{project['owner']}/{project['repo']}"
    swapped_out = [weakest for _, weakest in decision["swaps"]]
    lineup = [challenger for challenger, _ in decision["swaps"]] + [project for project in decision["ordered"] if project not in swapped_out]
    pins: list[str] = []
    for project in sorted(lineup, key=lambda project: -project["score"]):
        if slug(project) not in pins and not project.get("archived"):
            pins.append(slug(project))
    free = sorted(
        (project for project in decision["pool"] + swapped_out if not project["path"] and not project.get("archived") and slug(project) not in pins),
        key=lambda project: -project["score"],
    )
    already = {name.lower() for name in pinned}
    while len(pins) < PINS and free:
        staying = next((project for project in free if slug(project).lower() in already and project["score"] + MARGIN > free[0]["score"]), None)
        choice = staying or free[0]
        free.remove(choice)
        pins.append(slug(choice))
    return pins[:PINS]


# ---------------------------------------------------------------- the facts (GitHub, read only)

def gh(*args: str) -> tuple[int, str]:
    program = shutil.which("gh") or next((place for place in GH_PLACES if Path(place).exists()), "gh")
    try:
        result = subprocess.run([program, "api", *args], capture_output=True, text=True, timeout=60, env={**os.environ, "GH_PROMPT_DISABLED": "1"})
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return result.returncode, result.stdout


def commit_count(slug: str, path: str, since: str = "") -> int | None:
    """Commits touching `path` (the whole repo when empty), read from the last page number of a 1-per-page list."""
    query = "per_page=1" + (f"&path={path}" if path else "") + (f"&since={since}" if since else "")
    code, out = gh("-i", f"repos/{slug}/commits?{query}")
    if code != 0:
        return None
    last = re.search(r'[?&]page=(\d+)>; rel="last"', out)
    if last:
        return int(last.group(1))
    body = out.split("\n\n", 1)[-1].replace("\r", "").strip()
    try:
        return len(json.loads(body[body.index("["):]))
    except ValueError:
        return None


def repo_facts(slug: str) -> dict:
    """Facts shared by every project in one repo: stars, CI and its releases as (tag, downloads)."""
    code, out = gh(f"repos/{slug}", "--jq", "[.stargazers_count, .archived, (.homepage // \"\")] | @json")
    stars, archived, homepage = json.loads(out) if code == 0 else (None, False, "")
    code, out = gh(f"repos/{slug}/contents/.github/workflows", "--jq", "length")
    code_releases, releases = gh("--paginate", f"repos/{slug}/releases?per_page=100", "--jq", ".[] | [.tag_name, ([.assets[].download_count] | add // 0)] | @json")
    return {
        "stars": stars, "archived": archived, "homepage": homepage,
        "ci": (out.strip() not in ("", "0")) if code == 0 else False,
        "releases": [json.loads(line) for line in releases.splitlines() if line.strip()] if code_releases == 0 else None,
    }


def release_facts(releases: list | None, project: dict) -> tuple[int | None, int | None]:
    """(releases, downloads) that belong to the project: all of a repo's, or a folder's own tags in a monorepo."""
    if releases is None:
        return None, None
    if project["path"]:
        stem = re.sub(r"-v?\d[\d.]*$", "", project["tag"]) or project["path"].rsplit("/", 1)[-1]
        releases = [release for release in releases if release[0] == stem or release[0].startswith(stem + "-")]
    return len(releases), sum(release[1] for release in releases)


def answers(url: str) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "hone-featured"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def project_facts(project: dict, shared: dict, cairn_rank: dict, now: dt.datetime) -> dict:
    slug = f"{project['owner']}/{project['repo']}"
    tree = f"{project['branch'] or 'HEAD'}:{project['path']}" if project["path"] else "HEAD"
    code, out = gh(f"repos/{slug}/git/trees/{tree}?recursive=1", "--jq", '.tree[] | select(.type=="blob") | .path')
    releases, downloads = release_facts(shared["releases"], project)
    demo = project["demo"] or ("" if project["path"] else shared["homepage"])
    return {
        "tests": sum(1 for path in out.splitlines() if TEST_FILE_RE.search(path)) if code == 0 else None,
        "releases": releases, "downloads": downloads,
        "demo": answers(demo) if demo else False,
        "commits": commit_count(slug, project["path"]),
        "commits30": commit_count(slug, project["path"], (now - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")),
        # A folder of a monorepo has no stars of its own, and Cairn ranks whole repos only.
        "stars": 0 if project["path"] else shared["stars"],
        "ci": shared["ci"],
        "cairn": None if project["path"] else cairn_rank.get(slug.lower()),
    }


def cairn_ranking(brain: str) -> dict:
    """{owner/repo: overall 0-100} from the note Cairn keeps, or {} when there is none."""
    note = Path(brain) / "notes" / "project-ranking.md" if brain else None
    if not note or not note.exists():
        return {}
    return {row.group("slug").lower().rstrip("/"): int(row.group("overall")) for row in RANK_ROW_RE.finditer(note.read_text(encoding="utf-8"))}


def current_pins(owner: str) -> list[dict] | None:
    query = f'{{ user(login: "{owner}") {{ pinnedItems(first: {PINS}, types: REPOSITORY) {{ nodes {{ ... on Repository {{ nameWithOwner isArchived }} }} }} }} }}'
    code, out = gh("graphql", "-f", f"query={query}", "--jq", ".data.user.pinnedItems.nodes")
    try:
        return json.loads(out) if code == 0 else None
    except ValueError:
        return None


def gather(projects: list[dict], brain: str) -> None:
    """Adds `facts`, `score` and `archived` to every project that can be in or enter Featured."""
    now = dt.datetime.now(dt.timezone.utc)
    cairn_rank = cairn_ranking(brain)
    scored = [project for project in projects if project["section"] not in NOT_IN_POOL]
    slugs = sorted({f"{project['owner']}/{project['repo']}" for project in scored})
    with ThreadPoolExecutor(max_workers=8) as pool:
        shared = dict(zip(slugs, pool.map(repo_facts, slugs)))
        all_facts = list(pool.map(lambda project: project_facts(project, shared[f"{project['owner']}/{project['repo']}"], cairn_rank, now), scored))
    for project, facts in zip(scored, all_facts):
        project.update(facts=facts, score=score(facts), archived=shared[f"{project['owner']}/{project['repo']}"]["archived"])


# ---------------------------------------------------------------- report

def report(projects: list[dict], decision: dict, pins: list[dict] | None, owner: str, top: int) -> str:
    lines = [f"{'':2}{'score':>5}  {'project':<24}{'tests':>6}{'rel':>5}{'dl':>6}{'demo':>6}{'commits':>9}{'30d':>5}{'stars':>6}{'cairn':>6}  section"]
    scored = sorted((project for project in projects if "score" in project), key=lambda project: -project["score"])
    show = lambda value: "?" if value is None else ("yes" if value is True else "no" if value is False else str(value))
    for project in scored[:top]:
        facts = project["facts"]
        mark = "F" if project["section"] == FEATURED else " "
        lines.append(
            f"{mark:2}{project['score']:>5}  {project['name'][:23]:<24}{show(facts['tests']):>6}{show(facts['releases']):>5}{show(facts['downloads']):>6}"
            f"{show(facts['demo']):>6}{show(facts['commits']):>9}{show(facts['commits30']):>5}{show(facts['stars']):>6}{show(facts['cairn']):>6}  {project['section']}"
        )
    lines.append("")
    lines.append("Featured now:      " + ", ".join(project["name"] for project in decision["featured"]))
    lines.append("Featured by score: " + ", ".join(f"{project['name']} {project['score']}" for project in decision["ordered"]) + ("" if decision["reorder"] else "  (already in order)"))
    for challenger, weakest in decision["swaps"]:
        lines.append(f"SWAP IN: {challenger['name']} ({challenger['score']}, now in {challenger['section']}) for {weakest['name']} ({weakest['score']}): leads by {MARGIN}+ points. Needs its card written.")
    if not decision["swaps"]:
        lines.append(f"No project outside Featured leads its weakest card by {MARGIN} points.")
    wanted = wanted_pins(decision, [pin["nameWithOwner"] for pin in pins or []])
    lines.append("")
    if pins is None:
        lines.append("Pins: could not be read. Wanted: " + ", ".join(wanted))
    else:
        have = [pin["nameWithOwner"] for pin in pins]
        add = [slug for slug in wanted if slug.lower() not in (pin.lower() for pin in have)]
        drop = [pin["nameWithOwner"] + (" (archived)" if pin.get("isArchived") else "") for pin in pins if pin["nameWithOwner"].lower() not in (slug.lower() for slug in wanted)]
        if add or drop:
            lines.append(f"Pins: unpin {', '.join(drop) or 'nothing'}; pin {', '.join(add) or 'nothing'}. Order: {', '.join(wanted)}.")
            lines.append(f"      GitHub has no API for pins: https://github.com/{owner} > Customize your pins (a signed-in browser).")
        else:
            lines.append("Pins: match Featured.")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    card = lambda name, repo, path="": (
        f'<td width="50%" valign="top">\n      <a href="https://x.dev/{name}/"><img src="media/{name}.jpg"></a><br>\n'
        f'      <b><a href="https://x.dev/{name}/">{name}</a></b>: does things.<br>\n'
        f'      <sub><a href="https://github.com/me/{repo}{"/tree/main/" + path if path else ""}#readme">README</a></sub>\n    </td>'
    )
    table = lambda cards: "<table>\n" + "\n".join(f"  <tr>\n    {cards[i]}\n    {cards[i + 1]}\n  </tr>" for i in range(0, len(cards), 2)) + "\n</table>"
    cards = [card("Alpha", "alpha"), card("Beta", "mono", "apps/beta"), card("Gamma", "gamma"), card("Delta", "delta")]
    readme = (
        "intro\n\n## Featured\n\n<sub>caption</sub>\n\n" + table(cards) + "\n\n## Engineering\n\n" + table([card("Rig", "rig"), card("Bench", "bench")])
        + "\n\n## Building\n\n- **[Echo](https://x.dev/echo/)** [![Source](https://img.shields.io/badge/s)](https://github.com/me/echo): new.<br><sub>[README](https://github.com/me/echo#readme)</sub>\n"
        "- **[Foxtrot](https://github.com/me/mono/tree/main/apps/foxtrot)** [![Source](https://img.shields.io/badge/s)](https://github.com/me/mono/tree/main/apps/foxtrot): wip.\n"
    )
    failures = []

    def expect(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        if not condition:
            failures.append(label)

    projects = read_projects(readme)
    names = [project["name"] for project in projects]
    expect("reads cards and bullets, in order", names == ["Alpha", "Beta", "Gamma", "Delta", "Rig", "Bench", "Echo", "Foxtrot"])
    expect("a monorepo folder is its own project", projects[1]["path"] == "apps/beta" and projects[7]["path"] == "apps/foxtrot")
    expect("a link to GitHub is not a live demo", projects[7]["demo"] == "" and projects[0]["demo"] == "https://x.dev/Alpha/")
    expect("rewriting in the same order changes nothing", rewrite_featured(readme, cards) == readme)
    full = {"tests": 100, "releases": 3, "downloads": 500, "demo": True, "commits": 500, "commits30": 60, "stars": 50, "ci": True, "cairn": 100}
    expect("every signal at full scale is 100", score(full) == 100.0)
    expect("nothing at all is 0", score({"tests": 0, "releases": 0, "downloads": 0, "demo": False, "commits": 0, "commits30": 0, "stars": 0, "ci": False, "cairn": 0}) == 0.0)
    expect("an unread signal is left out, not counted as zero", score({**full, "cairn": None, "tests": None}) == 100.0)
    expect("weights add up to 100", sum(weight for _, weight, _ in SIGNALS) == 100)
    for project, value in zip(projects, [60, 80, 60.4, 30, 99, 99, 34, 34]):
        project["score"] = value
    decision = decide(projects)
    expect("best first; a tie within a point keeps its place", [p["name"] for p in decision["ordered"]] == ["Beta", "Alpha", "Gamma", "Delta"])
    expect("a lead under the margin is not a swap; Engineering stays put", decision["swaps"] == [])
    projects[7]["score"] = 35
    expect("a lead of the margin is a swap for the weakest card", [(c["name"], w["name"]) for c, w in decide(projects)["swaps"]] == [("Foxtrot", "Delta")])
    rewritten = rewrite_featured(readme, [project["block"] for project in decision["ordered"]])
    expect("the rewrite moves whole cards and nothing else", [p["name"] for p in read_projects(rewritten)][:4] == ["Beta", "Alpha", "Gamma", "Delta"] and sorted(rewritten) == sorted(readme))
    expect("pins follow Featured, one per repo, then whole repos", wanted_pins(decide(projects)) == ["me/mono", "me/gamma", "me/alpha", "me/echo", "me/delta"])
    expect("a repo already pinned keeps a free slot against a near tie", wanted_pins(decide(projects), ["me/Delta"])[3:] == ["me/delta", "me/echo"])
    expect("test files are told from other files", [bool(TEST_FILE_RE.search(p)) for p in ("tests/a.py", "src/test_x.py", "app.test.js", "src/contest.py", "latest.md")] == [True, True, True, False, False])
    print(f"  {'OK' if not failures else 'FAILED'}: featured selftest")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("readme", nargs="?", help="README.md in the clone of the profile repo")
    parser.add_argument("--write", action="store_true", help="reorder the Featured cards in the file")
    parser.add_argument("--check", action="store_true", help="exit 1 while Featured is out of order or outranked")
    parser.add_argument("--brain", default=os.environ.get("CAIRN_BRAIN", ""), help="the Obsidian vault Cairn writes its ranking note to")
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="whose pins to compare")
    parser.add_argument("--top", type=int, default=25, help="rows of the ranking to print")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.readme:
        parser.error("give the profile README.md")
    path = Path(args.readme)
    text = path.read_text(encoding="utf-8")
    projects = read_projects(text)
    gather(projects, args.brain)
    decision = decide(projects)
    if not decision["featured"]:
        raise SystemExit(f'No cards under "## {FEATURED}" in {path}.')
    pins = current_pins(args.owner)
    if args.json:
        print(json.dumps({
            "ranking": [{"name": p["name"], "score": p["score"], "section": p["section"], "source": key_of(p), "facts": p["facts"]} for p in sorted((p for p in projects if "score" in p), key=lambda p: -p["score"])],
            "featured": [p["name"] for p in decision["ordered"]], "reorder": decision["reorder"],
            "swaps": [{"in": c["name"], "out": w["name"]} for c, w in decision["swaps"]],
            "pins": wanted_pins(decision, [pin["nameWithOwner"] for pin in pins or []]), "pinsNow": [pin["nameWithOwner"] for pin in pins or []],
        }, indent=1))
    else:
        print(report(projects, decision, pins, args.owner, args.top))
    if args.write and decision["reorder"]:
        # newline="" keeps the file's own line endings: the profile's Action and git see only the moved cards.
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(rewrite_featured(text, [project["block"] for project in decision["ordered"]]))
        print(f"\nWrote the new order to {path}. Commit it as its own change.")
    if args.check and (decision["swaps"] or (decision["reorder"] and not args.write)):
        print("\nGATE FAIL: Featured is not the best projects in order.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
