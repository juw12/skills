"""/design — one command for a project's app UI + brand sync + landing page.

  python design_cmd.py status [slug]            what's new / pending, last audit per app
  python design_cmd.py report [--only a,b]       audit every live app, rank worst-first (out/report.md)
  python design_cmd.py start <slug>             prep workspace + baseline app audit + brand check + landing check
                                                -> prints the to-do list (failing gates) to work through
  python design_cmd.py audit <slug> [--label after] [--live | --url URL]   (default: local checkout)
  python design_cmd.py compare <slug>           baseline vs after: per-gate issue counts, regression = fail
  python design_cmd.py test <slug>              run the app's own tests
  python design_cmd.py finish <slug> [--push] [--merge]
        tests -> after-audit -> compare (abort on regression) -> brand sync --apply -> landing build + check
        -> app changes committed on a branch (+ PR with --push) -> landing commit (+ push with --push)
  python design_cmd.py sync <slug> [--apply] [--gallery]
  python design_cmd.py landing <landing.py args...>   pass-through to project-landing

App code is checked out under workspace/ (sparse checkout for monorepos). Nothing is pushed without --push,
and app changes go to a branch + pull request unless --merge is given.
"""
import argparse
import datetime
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SKILL = TOOLS.parent
STATE = SKILL / "state"
WORKSPACE = SKILL / "workspace"
OUT = SKILL / "out"
LANDING = next((p for p in (SKILL.parent / "project-landing",
                            Path.home() / ".vector" / "skills" / "project-landing") if p.exists()),
               SKILL.parent / "project-landing")
LANDING_CLI = LANDING / "tools" / "landing.py"
LANDING_STATE = LANDING / "state"
PY = r"C:\Users\juwen_lie\AppData\Local\Programs\Python\Python313\python.exe"
if not Path(PY).exists():
    PY = sys.executable

WEB_ROOT_CANDIDATES = ("web", "app", "public", "docs", "site", "www", "frontend", "client", ".")


def run(cmd, cwd=None, check=True, quiet=False, timeout=None):
    if not quiet:
        print("$", " ".join(str(c) for c in cmd))
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, text=True, encoding="utf-8", errors="replace",
                            capture_output=True, timeout=timeout)
    if not quiet:
        if result.stdout.strip():
            print(result.stdout.strip()[-5000:])
        if result.stderr.strip():
            print(result.stderr.strip()[-2000:])
    if check and result.returncode != 0:
        sys.exit(f"command failed ({result.returncode}): {' '.join(str(c) for c in cmd)[:160]}")
    return result


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")


def landing_entry(slug):
    data = load_json(LANDING_STATE / "data.json", {})
    if slug not in data:
        sys.exit(f"{slug} is not in the landing data yet: run `design_cmd.py landing ingest {slug}` first")
    return data[slug]


def resolve_source(slug):
    """Where the app's code lives: (owner/repo, branch, path inside repo)."""
    entry = landing_entry(slug)
    overrides = load_json(STATE / "apps.json", {}).get(slug, {})
    if overrides.get("repo"):
        return overrides["repo"], overrides.get("branch"), overrides.get("path", "")
    sys.path.insert(0, str(LANDING / "tools"))
    from repo_facts import SOURCE_OVERRIDE, parse_source  # noqa: E402
    src = SOURCE_OVERRIDE.get(slug) or entry["links"].get("source") or entry["links"].get("readme", "").split("#")[0]
    parsed = parse_source(src)
    if not parsed:
        sys.exit(f"cannot tell where {slug}'s code lives ({src!r}); set repo/path in state/apps.json")
    owner, repo, branch, path = parsed
    return f"{owner}/{repo}", branch, path


def prep(slug):
    repo, branch, path = resolve_source(slug)
    clone = WORKSPACE / repo.replace("/", "__")
    if not (clone / ".git").exists():
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        if path:
            run(["git", "clone", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", clone])
            run(["git", "sparse-checkout", "init", "--cone"], cwd=clone)
            run(["git", "sparse-checkout", "set", path], cwd=clone)
            run(["git", "checkout"] + ([branch] if branch else []), cwd=clone)
        else:
            run(["git", "clone", f"https://github.com/{repo}.git", clone])
    else:
        if path:
            current = run(["git", "sparse-checkout", "list"], cwd=clone, quiet=True).stdout.split()
            if path not in current:
                run(["git", "sparse-checkout", "add", path], cwd=clone)
        status = run(["git", "status", "--porcelain"], cwd=clone, quiet=True).stdout.strip()
        if not status:
            default = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=clone, quiet=True, check=False).stdout.strip()
            target = branch or (default.split("/", 1)[1] if "/" in default else "main")
            run(["git", "checkout", "-q", target], cwd=clone, check=False)
            run(["git", "pull", "-q", "--ff-only"], cwd=clone, check=False)
        else:
            print(f"workspace has uncommitted changes, not pulling:\n{status[:800]}")
    app_dir = clone / path if path else clone
    info = {"repo": repo, "branch": branch, "path": path, "clone": str(clone), "app_dir": str(app_dir)}
    for cand in WEB_ROOT_CANDIDATES:
        if (app_dir / cand / "index.html").exists():
            info["web_root"] = str((app_dir / cand).resolve())
            break
    pkg = app_dir / "package.json"
    if pkg.exists():
        scripts = load_json(pkg, {}).get("scripts", {})
        info["node"] = {k: scripts[k] for k in ("dev", "build", "start", "test") if k in scripts}
    tests = []
    if any(app_dir.rglob("test_*.py")) or any(app_dir.rglob("*_test.py")) or (app_dir / "tests.py").exists() or any(app_dir.rglob("tests.py")):
        tests.append("python")
    if info.get("node", {}).get("test"):
        tests.append("npm")
    info["tests"] = tests
    info["live"] = landing_entry(slug)["links"].get("live")
    apps = load_json(STATE / "apps.json", {})
    apps.setdefault(slug, {}).update({k: v for k, v in info.items() if k not in ("repo", "branch", "path")})
    apps[slug].setdefault("repo_detected", repo)
    save_json(STATE / "apps.json", apps)
    print(json.dumps(info, indent=1))
    return info


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def audit(slug, label="baseline", live=False, url=None, routes=None):
    apps = load_json(STATE / "apps.json", {})
    info = apps.get(slug) or prep(slug)
    server = None
    if url:
        urls = [url]
    elif not live and (info.get("web_root") or not info.get("live")):
        if not info.get("web_root"):
            sys.exit("no static web root found and no live URL; start the app yourself and pass --url http://127.0.0.1:PORT/")
        port = free_port()
        server = subprocess.Popen([PY, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", info["web_root"]],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)
        query = ""
        if info.get("live") and "?" in info["live"]:
            query = "?" + info["live"].split("?", 1)[1]
        urls = [f"http://127.0.0.1:{port}/{query}"]
    else:
        urls = [info["live"]]
    urls += [urls[0].split("?")[0].rstrip("/") + "/" + r.lstrip("/") for r in (routes or info.get("routes") or [])]
    out_dir = OUT / slug / label
    if out_dir.exists():
        shutil.rmtree(out_dir)
    try:
        run([PY, TOOLS / "app_audit.py", out_dir, *urls, "--name", slug], timeout=300)
    finally:
        if server:
            server.terminate()
    apps = load_json(STATE / "apps.json", {})
    report = load_json(out_dir / "audit.json", {})
    apps.setdefault(slug, {}).setdefault("audits", {})[label] = {
        "when": datetime.datetime.now().isoformat(timespec="minutes"), "urls": urls,
        "pass": report.get("pass"), "failing": report.get("failing_gates"), "dir": str(out_dir)}
    save_json(STATE / "apps.json", apps)
    return report


def counts(report):
    c = {}
    for r in report.get("results", []):
        p = r["probe"]
        for gate, n in (("A1", len(r["errors"])), ("A2", int(p["overflow"] > 1)), ("A3", int(not p["viewport_meta"])),
                        ("A4", len(p["contrast"])), ("A5", len(p["tap"])), ("A6", len(p["small_text"])),
                        ("A7", len(p["img"])), ("A8", int(p["h1"] != 1 or not p["brand"]["title"]))):
            c[gate] = c.get(gate, 0) + n
    return c


def compare(slug, quiet=False):
    base = load_json(OUT / slug / "baseline" / "audit.json", None)
    after = load_json(OUT / slug / "after" / "audit.json", None)
    if not base or not after:
        sys.exit("need both a baseline and an after audit")
    cb, ca = counts(base), counts(after)
    regress = [g for g in cb if ca.get(g, 0) > cb[g]]
    print("gate  baseline  after")
    for g in sorted(cb):
        mark = "  REGRESSION" if g in regress else ("  better" if ca.get(g, 0) < cb[g] else "")
        print(f"{g}    {cb[g]:>6}  {ca.get(g, 0):>5}{mark}")
    total_b, total_a = sum(cb.values()), sum(ca.values())
    print(f"total {total_b:>6}  {total_a:>5}   gates passing: {8 - len(base['failing_gates'])} -> {8 - len(after['failing_gates'])}")
    return {"regress": regress, "improved": total_a < total_b or (total_a == 0 and total_b == 0), "after_pass": after["pass"]}


def tests(slug):
    info = load_json(STATE / "apps.json", {}).get(slug) or prep(slug)
    app_dir = Path(info["app_dir"])
    ok = True
    if "python" in info.get("tests", []):
        has_pytest = run([PY, "-c", "import pytest"], check=False, quiet=True).returncode == 0
        cmd = [PY, "-m", "pytest", "-q", "-x"] if has_pytest else [PY, "-m", "unittest", "discover", "-v"]
        ok &= run(cmd, cwd=app_dir, check=False, timeout=600).returncode == 0
    if "npm" in info.get("tests", []):
        if not (app_dir / "node_modules").exists():
            run(["npm", "ci" if (app_dir / "package-lock.json").exists() else "install"], cwd=app_dir, check=False, timeout=900)
        ok &= run(["npm", "test", "--silent"], cwd=app_dir, check=False, timeout=900).returncode == 0
    if not info.get("tests"):
        print("no tests detected for this app (audit gates are the only check)")
    print("tests:", "PASS" if ok else "FAIL")
    return ok


def sync(slug, apply=False, gallery=False):
    label = "after" if (OUT / slug / "after" / "audit.json").exists() else "baseline"
    audit_file = OUT / slug / label / "audit.json"
    if not audit_file.exists():
        audit(slug)
    cmd = [PY, TOOLS / "brand.py", slug, audit_file, "--landing-state", LANDING_STATE]
    if apply:
        cmd.append("--apply")
    if gallery:
        cmd.append("--gallery")
    run(cmd)


def landing(*args, check=True):
    return run([PY, LANDING_CLI, *args], check=check, timeout=900)


def ship_app(slug, push=False, merge=False):
    info = load_json(STATE / "apps.json", {}).get(slug)
    clone = Path(info["clone"])
    scope = info.get("path") or load_json(STATE / "apps.json", {}).get(slug, {}).get("path") or resolve_source(slug)[2] or "."
    changed = run(["git", "status", "--porcelain", "--", scope], cwd=clone, quiet=True).stdout.strip()
    if not changed:
        print("app: no code changes to ship")
        return None
    branch = f"design/{slug}-{datetime.date.today():%Y%m%d}"
    run(["git", "checkout", "-B", branch], cwd=clone)
    run(["git", "add", "--", scope], cwd=clone)
    run(["git", "commit", "-q", "-m", f"{landing_entry(slug)['name']}: design pass (contrast, tap targets, type scale)"], cwd=clone)
    if not push:
        print(f"app: committed on {branch} in {clone}; re-run finish with --push to open a PR")
        return branch
    run(["git", "push", "-u", "origin", branch], cwd=clone)
    body = (OUT / slug / "pr_body.md")
    body.write_text(pr_body(slug), encoding="utf-8")
    pr = run(["gh", "pr", "create", "--head", branch, "--title", f"{landing_entry(slug)['name']}: design pass",
              "--body-file", body], cwd=clone, check=False)
    if merge:
        run(["gh", "pr", "merge", branch, "--squash", "--delete-branch"], cwd=clone, check=False)
    return branch


def pr_body(slug):
    base = load_json(OUT / slug / "baseline" / "audit.json", {})
    after = load_json(OUT / slug / "after" / "audit.json", {})
    cb, ca = counts(base), counts(after)
    lines = ["Design pass made with the /design skill.", "", "| gate | before | after |", "|---|---|---|"]
    names = {"A1": "JS/console errors", "A2": "horizontal overflow", "A3": "viewport meta", "A4": "low-contrast text",
             "A5": "small tap targets (phone)", "A6": "text < 12px", "A7": "images without alt / broken", "A8": "h1 + title"}
    for g in sorted(cb):
        lines.append(f"| {g} {names[g]} | {cb[g]} | {ca.get(g, 0)} |")
    lines += ["", "App tests were run before opening this PR."]
    return "\n".join(lines)


def cmd_status(args):
    landing("status", check=False)
    apps = load_json(STATE / "apps.json", {})
    for slug, info in sorted(apps.items()):
        if args.slug and slug != args.slug:
            continue
        audits = info.get("audits", {})
        line = ", ".join(f"{k}: {'PASS' if v['pass'] else 'FAIL ' + ','.join(v['failing'] or [])} ({v['when']})" for k, v in audits.items())
        print(f"{slug:20} {line or 'no audits yet'}")


def cmd_start(args):
    info = prep(args.slug)
    report = audit(args.slug, "baseline", live=args.live, url=args.url)
    print("\n== brand")
    sync(args.slug)
    print("\n== landing")
    landing("build", "--only", args.slug)
    landing("check", "--only", args.slug, check=False)
    print("\n== TO-DO (app): fix these in", info["app_dir"])
    for gate, msgs in sorted(report.get("failures", {}).items()):
        for m in msgs[:4]:
            print(f"  {gate} {m[:200]}")
    print("Screenshots:", OUT / args.slug / "baseline")


def cmd_finish(args):
    slug = args.slug
    if not tests(slug):
        sys.exit("app tests fail: fix before finishing")
    audit(slug, "after", live=args.live, url=args.url)
    verdict = compare(slug)
    if verdict["regress"]:
        sys.exit(f"regression in {verdict['regress']}: not shipping")
    if not verdict["improved"]:
        print("warning: no measurable improvement; shipping only brand/landing changes")
    sync(slug, apply=True, gallery=args.gallery)
    landing("build", "--only", slug)
    landing("check", "--only", slug)
    ship_app(slug, push=args.push, merge=args.merge)
    publish = ["publish", "--only", slug, "-m", f"{landing_entry(slug)['name']}: landing page synced with the app"]
    if args.push:
        publish.append("--push")
    landing(*publish, check=False)


def cmd_report(args):
    """Audit every app with a live URL and rank by open issues (worst first)."""
    data = load_json(LANDING_STATE / "data.json", {})
    targets = [(s, d["links"]["live"]) for s, d in sorted(data.items()) if d["links"].get("live")]
    if args.only:
        wanted = set(args.only.split(","))
        targets = [t for t in targets if t[0] in wanted]
    rows = []
    for slug, url in targets:
        out_dir = OUT / slug / "live"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        run([PY, TOOLS / "app_audit.py", out_dir, url, "--name", slug], check=False, quiet=True, timeout=180)
        report = load_json(out_dir / "audit.json", None)
        if not report:
            rows.append((slug, None, "audit failed"))
            continue
        c = counts(report)
        rows.append((slug, sum(c.values()), ",".join(report["failing_gates"]) or "PASS"))
        apps = load_json(STATE / "apps.json", {})
        apps.setdefault(slug, {}).setdefault("audits", {})["live"] = {
            "when": datetime.datetime.now().isoformat(timespec="minutes"), "urls": [url],
            "pass": report["pass"], "failing": report["failing_gates"], "dir": str(out_dir)}
        save_json(STATE / "apps.json", apps)
        print(f"{slug:20} {rows[-1][1]!s:>5}  {rows[-1][2]}", flush=True)
    rows.sort(key=lambda r: -(r[1] or 0))
    lines = ["| app | open issues | failing gates |", "|---|---|---|"] + [f"| {s} | {n} | {g} |" for s, n, g in rows]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nworst first:")
    for s, n, g in rows[:10]:
        print(f"  {s:20} {n!s:>5}  {g}")
    print("table:", OUT / "report.md")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status")
    p.add_argument("slug", nargs="?")
    for name in ("start", "audit", "finish"):
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.add_argument("--live", action="store_true", help="audit the deployed site instead of the local checkout")
        p.add_argument("--url")
        if name == "audit":
            p.add_argument("--label", default="baseline")
            p.add_argument("--route", action="append")
        if name == "finish":
            p.add_argument("--push", action="store_true")
            p.add_argument("--merge", action="store_true")
            p.add_argument("--gallery", action="store_true")
    p = sub.add_parser("report")
    p.add_argument("--only", default="")
    for name in ("prep", "compare", "test"):
        sub.add_parser(name).add_argument("slug")
    p = sub.add_parser("sync")
    p.add_argument("slug")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--gallery", action="store_true")
    p = sub.add_parser("landing")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "start":
        cmd_start(args)
    elif args.cmd == "finish":
        cmd_finish(args)
    elif args.cmd == "report":
        cmd_report(args)
    elif args.cmd == "prep":
        prep(args.slug)
    elif args.cmd == "audit":
        audit(args.slug, args.label, live=args.live, url=args.url, routes=args.route)
    elif args.cmd == "compare":
        compare(args.slug)
    elif args.cmd == "test":
        tests(args.slug)
    elif args.cmd == "sync":
        sync(args.slug, apply=args.apply, gallery=args.gallery)
    elif args.cmd == "landing":
        landing(*args.rest, check=False)


if __name__ == "__main__":
    main()
