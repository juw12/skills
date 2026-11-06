"""Collect real, verifiable repo facts for each landing page.

For every project source URL (github.com/<owner>/<repo>[/tree/<branch>/<path>]) this records:
  - commits touching the path (count, first/last date, recent non-merge subjects)
  - the file list under the path (from the git tree API)
  - dependency manifests (package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, *.csproj)

Usage: python repo_facts.py <data.json> <out.json>
"""
import base64
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MANIFESTS = ("package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod", "pubspec.yaml")


# projects whose code moved away from the source link listed on the gallery
SOURCE_OVERRIDE = {
    "scopeguard": "https://github.com/juw12/steward/tree/main/apps/playground",
}


def gh(endpoint, paginate=False):
    args = ["gh", "api", endpoint]
    if paginate:
        args.insert(2, "--paginate")
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if paginate:
        # --paginate concatenates JSON arrays: "][" boundaries
        text = "[" + re.sub(r"\]\s*\[", ",", text)[1:] if text.startswith("[") else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_source(url):
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)(?:/tree/([^/]+)/?(.*))?", url or "")
    if not m:
        return None
    owner, repo, branch, path = m.groups()
    return owner, repo.removesuffix(".git"), branch, (path or "").strip("/")


_tree_cache = {}


def repo_tree(owner, repo, branch):
    key = (owner, repo, branch)
    if key not in _tree_cache:
        if not branch:
            meta = gh(f"repos/{owner}/{repo}") or {}
            branch = meta.get("default_branch", "main")
        tree = gh(f"repos/{owner}/{repo}/git/trees/{branch}?recursive=1") or {}
        _tree_cache[key] = (branch, [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"])
    return _tree_cache[key]


def facts_for(slug, source):
    parsed = parse_source(source)
    if not parsed:
        return slug, None
    owner, repo, branch, path = parsed
    branch, all_files = repo_tree(owner, repo, branch)
    prefix = path + "/" if path else ""
    files = [f[len(prefix):] for f in all_files if f.startswith(prefix)]

    query = f"repos/{owner}/{repo}/commits?sha={branch}&per_page=100"
    if path:
        query += f"&path={path}"
    commits = gh(query, paginate=True) or []
    subjects = []
    for c in commits:
        msg = c["commit"]["message"].splitlines()[0].strip()
        if msg.lower().startswith("merge"):
            continue
        subjects.append({"date": c["commit"]["author"]["date"][:10], "msg": msg})

    manifests = {}
    for name in MANIFESTS:
        candidates = [f for f in files if f == name or (f.endswith("/" + name) and f.count("/") <= 2)]
        for rel in candidates[:3]:
            blob = gh(f"repos/{owner}/{repo}/contents/{prefix}{rel}?ref={branch}")
            if blob and blob.get("content"):
                manifests[rel] = base64.b64decode(blob["content"]).decode("utf-8", "replace")[:20000]

    return slug, {
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "path": path,
        "file_count": len(files),
        "files": files[:4000],
        "commit_count": len(commits),
        "first_commit": commits[-1]["commit"]["author"]["date"][:10] if commits else None,
        "last_commit": commits[0]["commit"]["author"]["date"][:10] if commits else None,
        "recent": subjects[:12],
        "manifests": manifests,
    }


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sources = {slug: d["links"].get("source") or d["links"].get("readme", "").split("#")[0] for slug, d in data.items()}
    sources.update({slug: url for slug, url in SOURCE_OVERRIDE.items() if slug in sources})
    # warm the tree cache serially per repo to avoid duplicate big downloads
    for src in set(sources.values()):
        parsed = parse_source(src)
        if parsed:
            repo_tree(parsed[0], parsed[1], parsed[2])
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = dict(pool.map(lambda kv: facts_for(*kv), sources.items()))
    Path(sys.argv[2]).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [s for s, r in results.items() if not r]
    print(f"facts for {len(results) - len(missing)} / {len(results)}; missing: {missing}")


if __name__ == "__main__":
    main()
