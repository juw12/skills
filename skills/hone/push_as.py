"""Which GitHub account a push from this folder goes out as, what that account may do, and where it lands.

The account is the user's choice, made in Cairn (Vibe page, "Pushes from this computer", or
`cairn vibe github push-as NAME`). Cairn's switch is the GitHub CLI's own active account, so this file
reads it the way Cairn does: the sign-in git would send to github.com is compared with each account the
CLI is signed in to. It never switches the account, never acts with another account's sign-in and never
prints a token. When the picked account may not do what the work needs, the answer is a sentence for the
user ("press the other chip in Cairn"), not a way around it.

Where a push lands is a separate rule: a repo of DEFAULT_OWNER unless the request named another owner.

    python push_as.py                         # this folder: who pushes, where to, may it?  exit 1 = do not push
    python push_as.py check --dir PATH [--allow-owner NAME] [--needs workflow,settings] [--json]
    python push_as.py create NAME [--public]  # new repo under DEFAULT_OWNER; only when that account is the picked one
    python push_as.py --selftest              # offline checks of the rules above

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOST = "github.com"
DEFAULT_OWNER = os.environ.get("HONE_GITHUB_OWNER", "juw12")
LOGIN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
ORIGIN_RE = re.compile(r"github\.com[:/]+(?P<owner>[^/\s:]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$")
GH_PLACES = ("/usr/local/bin/gh", "/opt/homebrew/bin/gh", r"C:\Program Files\GitHub CLI\gh.exe")
CHIP = "Needs the user: press the {account} chip in Cairn (Vibe page, GitHub minutes, Pushes from this computer), then run this again."
# What a task may need beyond a plain push, and the sentence for when the picked account lacks it.
NEEDS = {
    "workflow": "{pusher}'s sign-in has no `workflow` scope, so it cannot push a change under .github/workflows/.",
    "settings": "{pusher} is not an admin of {origin}: no settings, secrets, collaborators, description or topics.",
}


class PushError(Exception):
    """A step that was not made, with a sentence a person can act on."""


def find_gh() -> str:
    """The GitHub CLI, also when an agent's shell has a shorter PATH than the user's terminal."""
    return shutil.which("gh") or next((place for place in GH_PLACES if Path(place).exists()), "gh")


def system_run(args: list[str], cwd: str | None = None, stdin: str | None = None) -> tuple[int, str, str]:
    """One git or gh command with every password prompt turned off. (127, "", "") when the program is missing.
    No sign-in is ever handed to it: gh and git use the account that is picked."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GH_PROMPT_DISABLED": "1"}
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    command = [find_gh(), *args[1:]] if args[0] == "gh" else args
    try:
        result = subprocess.run(command, input=stdin, capture_output=True, encoding="utf-8", errors="replace", timeout=30, env=env, cwd=cwd or str(Path.home()))
    except (OSError, subprocess.TimeoutExpired):
        return 127, "", ""
    return result.returncode, result.stdout, result.stderr


def signed_in(run) -> tuple[list[str], str, dict]:
    """(accounts the GitHub CLI is signed in to, the active one, {account: its sign-in's scopes})."""
    code, out, err = run(["gh", "auth", "status", "--hostname", HOST, "--json", "hosts"])
    names: list[str] = []
    active = ""
    scopes: dict = {}
    try:
        for entry in json.loads(out)["hosts"].get(HOST, []):
            names.append(str(entry.get("login", "")))
            scopes[names[-1]] = {scope.strip() for scope in str(entry.get("scopes", "")).split(",") if scope.strip()}
            if entry.get("active"):
                active = names[-1]
    except (ValueError, KeyError, TypeError, AttributeError):
        if code != 127:  # a GitHub CLI from before --json: read its sentences
            _, out, err = run(["gh", "auth", "status", "--hostname", HOST])
            names = re.findall(rf"Logged in to {re.escape(HOST)} (?:account|as) (\S+)", out + err)
    names = [name for name in dict.fromkeys(names) if LOGIN_RE.fullmatch(name)]
    if not active and names:
        _, out, _ = run(["gh", "config", "get", "user", "--host", HOST])
        active = next((name for name in names if name.lower() == out.strip().lower()), "")
    return names, active, scopes


def origin(run, cwd: str) -> dict:
    """Where this folder pushes: {"url", "owner", "repo", "ssh"}; empty values when it has no GitHub origin."""
    code, out, _ = run(["git", "remote", "get-url", "--push", "origin"], cwd=cwd)
    url = out.strip() if code == 0 else ""
    match = ORIGIN_RE.search(url)
    return {
        "url": url,
        "owner": match.group("owner") if match else "",
        "repo": match.group("repo") if match else "",
        "ssh": bool(url) and not url.lower().startswith("http"),
    }


def pusher(run, cwd: str, names: list[str], url: str) -> tuple[str, bool]:
    """(account git signs in to GitHub as from this folder, whether that was compared and not guessed).
    The comparison is Cairn's own: each account's sign-in is read to be compared here, and used for nothing."""
    question = f"url={url}\n\n" if url.lower().startswith("http") else f"protocol=https\nhost={HOST}\n\n"
    _, out, _ = run(["git", "credential", "fill"], cwd=cwd, stdin=question)
    found = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    password = found.get("password", "")
    if password:
        for name in names:
            code, token, _ = run(["gh", "auth", "token", "--hostname", HOST, "--user", name])
            if code == 0 and token.strip() == password:
                return name, True
    user = found.get("username", "")
    return (user, False) if LOGIN_RE.fullmatch(user) else ("", False)


def repo_rights(run, slug: str) -> dict | None:
    """What the picked account may do in `slug`: {"push", "admin", "private"}; None when GitHub cannot be asked."""
    code, out, _ = run(["gh", "api", f"repos/{slug}", "--jq", "[.permissions.push, .permissions.admin, .private] | @json"])
    try:
        push, admin, private = json.loads(out) if code == 0 else (None, None, None)
    except ValueError:
        return None
    return None if push is None else {"push": bool(push), "admin": bool(admin), "private": bool(private)}


def author_is_new(run, cwd: str) -> str:
    """The commit address set for this clone when no commit in its history carries it yet, else ""."""
    _, email, _ = run(["git", "config", "user.email"], cwd=cwd)
    code, history, _ = run(["git", "log", "--all", "--format=%ae"], cwd=cwd)
    seen = {line.strip().lower() for line in history.splitlines() if line.strip()}
    return email.strip() if code == 0 and seen and email.strip() and email.strip().lower() not in seen else ""


def check(run, cwd: str, allow_owner: str = "", needs: tuple = ()) -> dict:
    """Everything a push from `cwd` depends on. `ok` False means: do not push, act on `problems` first."""
    names, active, scopes = signed_in(run)
    where = origin(run, cwd)
    reading = {
        "accounts": names, "active": active, "pusher": "", "sure": False, "defaultOwner": DEFAULT_OWNER,
        "origin": f"{where['owner']}/{where['repo']}" if where["owner"] else "", "canPush": None, "cannot": [], "problems": [], "notes": [],
    }
    problems = reading["problems"]
    other = next((name for name in names if name.lower() == DEFAULT_OWNER.lower()), DEFAULT_OWNER)
    if not names:
        problems.append("The GitHub CLI is not signed in on this computer. Needs the user: gh auth login")
    if where["ssh"]:
        reading["notes"].append("origin is an SSH address: the SSH key decides who pushes there, not Cairn's switch.")
    elif names:
        reading["pusher"], reading["sure"] = pusher(run, cwd, names, where["url"])
        if not reading["pusher"]:
            problems.append("git has no sign-in for github.com here. The user picks one: cairn vibe github push-as NAME")
        elif not reading["sure"]:
            reading["notes"].append(f"git signs in as {reading['pusher']} with a sign-in it saved by itself, not the GitHub CLI's.")
        elif reading["pusher"].lower() != active.lower():
            reading["notes"].append(f"this folder pushes as {reading['pusher']} although Cairn's switch is on {active}: a setting inside this repo decides it.")
    picked = reading["sure"] and reading["pusher"].lower() == active.lower()
    rights = None
    if not where["url"]:
        problems.append(f"No origin yet. New repos go under {DEFAULT_OWNER}: python push_as.py create NAME")
    elif not where["owner"]:
        problems.append(f"origin is not a github.com repo: {where['url']}")
    else:
        owner = where["owner"]
        if owner.lower() != DEFAULT_OWNER.lower() and owner.lower() != allow_owner.lower():
            problems.append(
                f"origin is {reading['origin']}, not a {DEFAULT_OWNER} repo. Push there only when the request named that repo "
                f"(then pass --allow-owner {owner}); otherwise the work belongs in {DEFAULT_OWNER}/{where['repo']}."
            )
        if picked:
            rights = repo_rights(run, reading["origin"])
            reading["canPush"] = rights["push"] if rights else None
            if rights and not rights["push"]:
                problems.append(f"{reading['pusher']} may not push to {reading['origin']}. " + CHIP.format(account=owner))
    if picked:
        lacks = {"workflow": "workflow" not in scopes.get(reading["pusher"], set()), "settings": bool(rights) and not rights["admin"]}
        reading["cannot"] = [need for need, lacking in lacks.items() if lacking]
        for need in needs:
            if lacks.get(need):
                problems.append(NEEDS[need].format(pusher=reading["pusher"], origin=reading["origin"]) + " " + CHIP.format(account=other))
    new_address = author_is_new(run, cwd) if where["owner"] else ""
    if new_address and not (rights and rights["private"]):
        problems.append(
            f"Commits here would carry {new_address}, an address no commit in this repo has shown before, and a pushed address cannot be "
            f"taken back. Set the one this repo uses: git config user.email <address from `git log`>"
        )
    reading["ok"] = not problems
    who = reading["pusher"] or ("the SSH key's account" if where["ssh"] else "nobody")
    reading["line"] = f"Pushed as: {who} ({'Cairn push-as' if picked else 'not Cairn-switch'}) -> {reading['origin'] or 'no origin'}"
    return reading


def create(run, name: str, cwd: str, public: bool = False) -> str:
    """A new repo under DEFAULT_OWNER. Only that account can make it, so only when it is the picked one."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name):
        raise PushError(f"'{name}' is not a repo name.")
    slug = f"{DEFAULT_OWNER}/{name}"
    names, active, _ = signed_in(run)
    if active.lower() != DEFAULT_OWNER.lower():
        raise PushError(f"{slug} can only be created by {DEFAULT_OWNER}, and pushes are set to {active or 'nobody'}. " + CHIP.format(account=DEFAULT_OWNER))
    made = "already there"
    if run(["gh", "api", f"repos/{slug}", "--jq", ".full_name"])[0] != 0:
        code, _, err = run(["gh", "api", "-X", "POST", "user/repos", "-f", f"name={name}", "-F", f"private={'false' if public else 'true'}"])
        if code != 0:
            raise PushError(f"Could not create {slug}: {err.strip() or 'GitHub refused'}")
        made = "created " + ("public" if public else "private")
    if run(["git", "rev-parse", "--git-dir"], cwd=cwd)[0] == 0 and not origin(run, cwd)["url"]:
        run(["git", "remote", "add", "origin", f"https://{HOST}/{slug}.git"], cwd=cwd)
    return f"{slug} {made}."


def selftest() -> int:
    """The rules, against a pretend computer: two accounts, repos under `juw12`, Cairn's switch on `work`."""
    tokens = {"juw12": "t-main", "work": "t-work"}
    world = {
        "active": "work", "origin": "https://github.com/juw12/app.git", "email": "me@users.noreply.github.com", "history": ["me@users.noreply.github.com"],
        "repos": {"juw12/app": {"work": "push", "private": False}}, "calls": [], "env_seen": [],
    }

    def fake(args, cwd=None, stdin=None):
        world["calls"].append(args)
        who = world["active"]
        if args[:3] == ["gh", "auth", "status"]:
            hosts = [{"login": "work", "active": who == "work", "scopes": "gist, repo"}, {"login": "juw12", "active": who == "juw12", "scopes": "gist, repo, workflow"}]
            return 0, json.dumps({"hosts": {HOST: hosts}}), ""
        if args[:3] == ["gh", "auth", "token"]:
            return 0, tokens[args[-1]] + "\n", ""
        if args[:3] == ["git", "remote", "get-url"]:
            return (0, world["origin"] + "\n", "") if world["origin"] else (2, "", "no such remote")
        if args[:3] == ["git", "remote", "add"]:
            world["origin"] = args[-1]
            return 0, "", ""
        if args[:2] == ["git", "rev-parse"]:
            return 0, ".git\n", ""
        if args[:2] == ["git", "credential"]:
            return 0, f"username=x\npassword={tokens[who]}\n", ""
        if args[:3] == ["git", "config", "user.email"]:
            return 0, world["email"] + "\n", ""
        if args[:2] == ["git", "log"]:
            return 0, "\n".join(world["history"]) + "\n", ""
        if args[:2] == ["gh", "api"] and "POST" in args:
            new_name = next(arg.split("=", 1)[1] for arg in args if arg.startswith("name="))
            world["repos"][f"{who}/{new_name}"] = {"private": "private=true" in args}
            return 0, "{}", ""
        if args[:2] == ["gh", "api"]:
            slug = args[2].replace("repos/", "")
            repo = world["repos"].get(slug)
            if repo is None:
                return 1, "", "Not Found"
            mine = who == slug.split("/")[0]
            return 0, json.dumps([mine or repo.get(who) == "push", mine, repo.get("private", False)]) if "@json" in args[-1] else slug, ""
        return 1, "", "unexpected"

    failures = []

    def expect(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        if not condition:
            failures.append(label)

    reading = check(fake, ".")
    expect("pusher is the account Cairn's switch is on, compared and not guessed", reading["pusher"] == "work" and reading["sure"])
    expect("a juw12 repo the pusher may write to is ok", reading["ok"] and reading["line"] == "Pushed as: work (Cairn push-as) -> juw12/app")
    expect("what the picked account cannot do is listed", reading["cannot"] == ["workflow", "settings"])
    blocked = check(fake, ".", needs=("workflow", "settings"))
    expect("needing a workflow change or a setting stops the push and asks for the other chip", not blocked["ok"] and len(blocked["problems"]) == 2 and all("press the juw12 chip" in problem for problem in blocked["problems"]))
    world["origin"] = "https://github.com/work/app.git"
    world["repos"]["work/app"] = {}
    expect("a repo under the pushing account is refused by default", not check(fake, ".")["ok"])
    expect("...and allowed when the request named that owner", check(fake, ".", allow_owner="work")["ok"])
    world["origin"] = "https://github.com/juw12/locked.git"
    world["repos"]["juw12/locked"] = {}
    expect("no push rights is a problem that names the chip to press", "press the juw12 chip" in " ".join(check(fake, ".")["problems"]))
    world["origin"] = ""
    expect("no origin points at create", "create NAME" in " ".join(check(fake, ".")["problems"]))
    try:
        create(fake, "fresh", ".")
        expect("a new juw12 repo is not created while another account is picked", False)
    except PushError as error:
        expect("a new juw12 repo is not created while another account is picked", "press the juw12 chip" in str(error) and "juw12/fresh" not in world["repos"])
    world["active"] = "juw12"
    message = create(fake, "fresh", ".")
    reading = check(fake, ".", needs=("workflow", "settings"))
    expect("with juw12 picked: created private, origin set, everything allowed", "juw12/fresh created private" in message and world["origin"].endswith("juw12/fresh.git") and reading["ok"] and reading["cannot"] == [])
    world["active"], world["origin"] = "work", "https://github.com/juw12/app.git"
    world["email"] = "private@example.com"
    expect("an address this public repo has never shown stops the push", "private@example.com" in " ".join(check(fake, ".")["problems"]))
    world["repos"]["juw12/app"]["private"] = True
    expect("...but not in a private repo", check(fake, ".")["ok"])
    world["origin"] = "git@github.com:juw12/app.git"
    reading = check(fake, ".")
    expect("an SSH origin is reported as not Cairn's switch", reading["pusher"] == "" and reading["notes"] and "SSH key" in reading["line"])
    expect("the account is never switched", not any(call[:3] == ["gh", "auth", "switch"] for call in world["calls"]))
    print(f"  {'OK' if not failures else 'FAILED'}: push_as selftest")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("action", nargs="?", default="check", choices=["check", "create"])
    parser.add_argument("name", nargs="?", help="create: repo name")
    parser.add_argument("--dir", default=".", help="the clone to read (default: this folder)")
    parser.add_argument("--allow-owner", default="", help="the request named a repo of this other account of the user's")
    parser.add_argument("--needs", default="", help="what the work needs beyond a push: workflow, settings (comma separated)")
    parser.add_argument("--public", action="store_true", help="create: make the new repo public")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    cwd = str(Path(args.dir).resolve())
    needs = tuple(need.strip() for need in args.needs.split(",") if need.strip())
    if any(need not in NEEDS for need in needs):
        parser.error(f"--needs takes: {', '.join(NEEDS)}")
    if args.action == "create":
        if not args.name:
            parser.error("create needs a repo name")
        try:
            print(create(system_run, args.name, cwd, args.public))
        except PushError as error:
            print(f"Not done: {error}", file=sys.stderr)
            return 1
    reading = check(system_run, cwd, args.allow_owner, needs)
    if args.json:
        print(json.dumps(reading, indent=1))
    else:
        print(reading["line"])
        print(f"Signed in: {', '.join(reading['accounts']) or 'nobody'}. New repos go under {DEFAULT_OWNER}.")
        if reading["cannot"]:
            words = {"workflow": "change files under .github/workflows/", "settings": "change settings, secrets, collaborators, description or topics"}
            print(f"{reading['pusher']} cannot: " + "; ".join(words[need] for need in reading["cannot"]) + ".")
        for note in reading["notes"]:
            print(f"Note: {note}")
        for problem in reading["problems"]:
            print(f"DO NOT PUSH: {problem}")
    return 0 if reading["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
