"""Can a search engine find this project? A gate, read from what is really online.

A page nobody links to and no sitemap names is found late or never: on 21 Nov 2026 Google knew 2 pages
of a site that had more than 150. For every public page of a project (the site its repo names, its
landing page) the gate asks what a search engine asks:

    answers       the page answers 200
    may be shown  it does not say noindex (a page that names another page as the real one is skipped)
    says what     a title of at least 10 characters and a description of at least 25
    is listed     a sitemap that the site's robots.txt names holds the page's address

Exit 1 = the gate fails; every GAP line is a run-queue item of this run. The fix for the first three is in
the project's own page. The fix for "is listed" is the site's sitemap: where ReachPilot runs, its daily
Search task writes it, tells Bing and Yandex through IndexNow and shows every project on its Search page
(`python findable.py` in the ReachPilot folder runs it now).

    python findable.py --repo juw12/cairn            # the repo's site and its landing page
    python findable.py --url https://example.org/    # any page, as often as needed
    python findable.py --repo juw12/tool --private   # a page meant to stay out of search may say noindex
    python findable.py --selftest                    # offline checks

Standard library only; GitHub is read through `gh` when it is there, else through the public API.
Whether and when a search engine shows a page stays its own decision. The gate only removes the reasons
it could not.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

AGENT = "hone-findable (https://github.com/juw12/skills)"
MIN_TITLE = 10
MIN_DESCRIPTION = 25
SITEMAPS_READ = 12  # sitemaps of one site that are opened, an index's children included


MAC_CERTS = "/etc/ssl/cert.pem"  # the roots macOS itself trusts


def _trust() -> ssl.SSLContext | None:
    """A python.org Python on a Mac ships without root certificates until a script is run; use the system's."""
    paths = ssl.get_default_verify_paths()
    if (paths.cafile and os.path.exists(paths.cafile)) or (paths.capath and os.path.isdir(paths.capath) and os.listdir(paths.capath)):
        return None
    return ssl.create_default_context(cafile=MAC_CERTS) if os.path.exists(MAC_CERTS) else None


def fetch(url: str) -> tuple[int, str]:
    """(status, text). Status 0 = no answer."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(request, timeout=25, context=_trust()) as answer:
            return answer.status, answer.read(1_500_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, ""


def homepage(repo: str) -> str:
    """The site a repo names on GitHub, or ""."""
    try:
        asked = subprocess.run(["gh", "api", f"repos/{repo}", "--jq", ".homepage // \"\""], capture_output=True, text=True, timeout=40)
        if asked.returncode == 0:
            return asked.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    status, text = fetch(f"https://api.github.com/repos/{repo}")
    try:
        return str(json.loads(text).get("homepage") or "") if status == 200 else ""
    except ValueError:
        return ""


def _meta(head: str, name: str) -> str:
    for tag in re.findall(r"<meta\b[^>]*>", head, re.I):
        if re.search(rf'\b(?:name|property)\s*=\s*["\']{re.escape(name)}["\']', tag, re.I):
            found = re.search(r'\bcontent\s*=\s*"([^"]*)"|\bcontent\s*=\s*\'([^\']*)\'', tag, re.I)
            if found:
                return html.unescape(found[1] if found[1] is not None else found[2]).strip()
    return ""


def same(first: str, second: str) -> bool:
    def plain(address: str) -> str:
        parts = urllib.parse.urlsplit(address)
        return parts.netloc.lower() + (re.sub(r"/index\.html?$", "/", parts.path) or "/")

    return plain(first) == plain(second)


def listed(url: str, get=fetch) -> bool:
    """True when a sitemap that the site's robots.txt names holds this address."""
    parts = urllib.parse.urlsplit(url)
    status, robots = get(f"{parts.scheme}://{parts.netloc}/robots.txt")
    waiting = re.findall(r"^\s*Sitemap:\s*(\S+)", robots, re.I | re.M) if status == 200 else []
    opened = 0
    # the sitemap nearest to the page first: a site can name many
    waiting.sort(key=lambda address: -len(urllib.parse.urlsplit(address).path.rsplit("/", 1)[0]) if url.startswith(address.rsplit("/", 1)[0]) else 1)
    while waiting and opened < SITEMAPS_READ:
        address = waiting.pop(0)
        opened += 1
        status, text = get(address)
        if status != 200:
            continue
        places = [html.unescape(place).strip() for place in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.S)]
        if "<sitemapindex" in text:
            waiting = places + waiting
        elif any(same(place, url) for place in places):
            return True
    return False


def gaps(url: str, private: bool = False, get=fetch) -> list[str]:
    """What keeps a search engine from finding this page. [] = nothing."""
    status, text = get(url)
    if status != 200:
        return [f"does not answer ({status or 'no connection'})"]
    end = text.lower().find("</head>")
    head = text[: end if end >= 0 else 20_000]
    link = next((tag for tag in re.findall(r"<link\b[^>]*>", head, re.I) if re.search(r'\brel\s*=\s*["\']canonical["\']', tag, re.I)), "")
    named = re.search(r'\bhref\s*=\s*["\']([^"\']+)["\']', link, re.I)
    canonical = urllib.parse.urljoin(url, html.unescape(named[1])) if named else ""
    if canonical and not same(canonical, url):
        return []  # it names another page as the real one: that page is the one to check
    if re.search(r'http-equiv\s*=\s*["\']refresh["\']', head, re.I):
        return []  # it only sends the reader on
    if "noindex" in _meta(head, "robots").lower():
        return [] if private else ["says noindex, so search engines must leave it out (--private if that is meant)"]
    found = []
    title = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    title_text = re.sub(r"\s+", " ", html.unescape(title[1])).strip() if title else ""
    if len(title_text) < MIN_TITLE:
        found.append(f"its title says too little (\"{title_text}\"): say what the project is, in the words people search with" if title_text else "has no title")
    described = _meta(head, "description")
    if len(described) < MIN_DESCRIPTION:
        found.append("has no description" if not described else f"its description is only {len(described)} characters")
    if not listed(url, get):
        found.append("is in no sitemap that robots.txt names")
    return found


def pages_of(repo: str, site=homepage, get=fetch) -> list[str]:
    """The repo's site and, where it exists, its landing page on the owner's Pages site."""
    owner, _, name = repo.partition("/")
    pages = []
    named = site(repo)
    if named.startswith("http"):
        pages.append(named)
    landing = f"https://{owner.lower()}.github.io/p/{name.split('/')[-1].lower()}/"
    if not any(same(landing, page) for page in pages) and get(landing)[0] == 200:
        pages.append(landing)
    return pages


def report(pages: list[str], private: bool = False, get=fetch) -> int:
    if not pages:
        print("GAP  no public page: the repo names no site and has no landing page")
        return 1
    failed = 0
    for page in pages:
        found = gaps(page, private, get)
        print(f"{'GAP ' if found else 'ok  '} {page}" + "".join(f"\n       - {gap}" for gap in found))
        failed += bool(found)
    print(f"Findable: {len(pages) - failed} of {len(pages)} page(s) can be found" + ("" if not failed else "; each GAP is a run-queue item"))
    return 1 if failed else 0


def selftest() -> int:
    good = ('<html><head><title>Alpha: finds the page you lost</title><meta name="description" content="Finds the page you lost, in every '
            'browser you use."></head><body>text</body></html>')
    web = {
        "https://me.github.io/robots.txt": (200, "User-agent: *\nSitemap: https://me.github.io/index-of-maps.xml\nSitemap: https://me.github.io/show/sitemap.xml\n"),
        "https://me.github.io/index-of-maps.xml": (200, "<sitemapindex><sitemap><loc>https://me.github.io/sitemap.xml</loc></sitemap></sitemapindex>"),
        "https://me.github.io/sitemap.xml": (200, "<urlset><url><loc>https://me.github.io/alpha/</loc></url><url><loc>https://me.github.io/p/alpha/</loc></url></urlset>"),
        "https://me.github.io/show/sitemap.xml": (200, "<urlset><url><loc>https://me.github.io/show/</loc></url></urlset>"),
        "https://me.github.io/alpha/": (200, good),
        "https://me.github.io/p/alpha/": (200, good),
        "https://me.github.io/beta/": (200, good),
        "https://me.github.io/bare/": (200, "<html><head><title>Bare</title></head></html>"),
        "https://me.github.io/hidden/": (200, good.replace("<title>", '<meta name="robots" content="noindex"><title>')),
        "https://me.github.io/old/": (200, good.replace("<title>", '<link rel="canonical" href="https://me.github.io/alpha/"><title>')),
    }
    get = lambda url: web.get(url, (404, ""))  # noqa: E731
    checks = [
        (gaps("https://me.github.io/alpha/", get=get) == [], "a page with a title, a description and a place in a sitemap passes"),
        (gaps("https://me.github.io/alpha/index.html", get=lambda url: web.get(url.replace("index.html", ""), (404, ""))) == [], "index.html and the folder are the same page"),
        (gaps("https://me.github.io/beta/", get=get) == ["is in no sitemap that robots.txt names"], "a page no sitemap names is a gap"),
        (gaps("https://me.github.io/bare/", get=get) == ['its title says too little ("Bare"): say what the project is, in the words people search with',
                                                           "has no description", "is in no sitemap that robots.txt names"], "a bare name as title and no description are gaps"),
        (gaps("https://me.github.io/gone/", get=get) == ["does not answer (404)"], "a page that does not answer is a gap"),
        (len(gaps("https://me.github.io/hidden/", get=get)) == 1 and gaps("https://me.github.io/hidden/", private=True, get=get) == [], "noindex is a gap unless the page is meant to stay out"),
        (gaps("https://me.github.io/old/", get=get) == [], "a page that names another as the real one is skipped"),
        (listed("https://me.github.io/show/", get) and not listed("https://nowhere.example/", get), "a sitemap index is followed, and a site without robots.txt lists nothing"),
        (pages_of("Me/alpha", site=lambda repo: "https://me.github.io/alpha/", get=get) == ["https://me.github.io/alpha/", "https://me.github.io/p/alpha/"], "a repo's pages are its site and its landing page"),
        (pages_of("Me/alpha", site=lambda repo: "https://me.github.io/p/alpha/", get=get) == ["https://me.github.io/p/alpha/"], "a landing page that is the site is counted once"),
        (report([], get=get) == 1 and report(["https://me.github.io/alpha/"], get=get) == 0 and report(["https://me.github.io/alpha/", "https://me.github.io/beta/"], get=get) == 1,
         "the gate fails when a page has a gap, and when there is no page at all"),
    ]
    failed = [label for passed, label in checks if not passed]
    for passed, label in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
    print(f"findable.py selftest: {len(checks) - len(failed)}/{len(checks)}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", help="owner/name: check the site the repo names and its landing page")
    parser.add_argument("--url", action="append", default=[], help="a page to check; may be given more than once")
    parser.add_argument("--private", action="store_true", help="the page is meant to stay out of search: noindex is not a gap")
    parser.add_argument("--selftest", action="store_true", help="offline checks")
    arguments = parser.parse_args()
    if arguments.selftest:
        return selftest()
    pages = list(arguments.url) + (pages_of(arguments.repo) if arguments.repo else [])
    if not arguments.repo and not pages:
        parser.print_help()
        return 2
    return report(pages, arguments.private)


if __name__ == "__main__":
    sys.exit(main())
