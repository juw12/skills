"""Which GitHub account a push from this folder goes out as, and whether it lands where it should.

The account is the user's choice, made in Cairn (Vibe page, "Pushes from this computer", or
`cairn vibe github push-as NAME`). Cairn's switch is the GitHub CLI's own active account, so this file
reads it the way Cairn does: the sign-in git would send to github.com is compared with each account the
CLI is signed in to. It never switches the account and never prints a token.

Where a push lands is a separate rule: everything goes to a repo of DEFAULT_OWNER unless the request
named another owner. A new repo is therefore created under DEFAULT_OWNER with that account's own sign-in
(one call), and the account Cairn picked is invited to it so the push itself still goes out as picked.

    python push_as.py                     # this folder: who pushes, where to, may it?  exit 1 = do not push
    python push_as.py check --dir PATH [--allow-owner NAME] [--json]
    python push_as.py create NAME [--public] [--dir PATH]   # new repo under DEFAULT_OWNER, private by default
    python push_as.py invite OWNER/REPO   # let the picked account push to a repo of another of your accounts
    python push_as.py --selftest          # offline checks of the rules above

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


class PushError(Exception):
    """A step that was not made, with a sentence a person can act on."""


def find_gh() -> str:
    """The GitHub CLI, also when an agent's shell has a shorter PATH than the user's terminal."""
    return shutil.which("gh") or next((place for place in GH_PLACES if Path(place).exists()), "gh")


def system_run(args: list[str], cwd: str | None = None, stdin: str | None = None, token: str | None = None) -> tuple[int, str, str]:
    """One git or gh command with every password prompt turned off. (127, "", "") when the program is missing."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GH_PROMPT_DISABLED": "1"}
    if token:
        env["GH_TOKEN"] = token
    command = [find_gh(), *args[1:]] if args[0] == "gh" else args
    try:
        result = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=30, env=env, cwd=cwd or str(Path.home()))
    except (OSError, subprocess.TimeoutExpired):
        return 127, "", ""
    return result.returncode, result.stdout, result.stderr


def signed_in(run) -> tuple[list[str], str]:
    """(accounts the GitHub CLI is signed in to, the active one)."""
    code, out, err = run(["gh", "auth", "status", "--hostname", HOST, "--json", "hosts"])
    names: list[str] = []
    active = ""
    try:
        for entry in json.loads(out)["hosts"].get(HOST, []):
            names.append(str(entry.get("login", "")))
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
    return names, active


def token_of(run, name: str) -> str:
    """That account's sign-in, for one call. It stays inside this process."""
    code, out, _ = run(["gh", "auth", "token", "--hostname", HOST, "--user", name])
    return out.strip() if code == 0 else ""


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
    """(account git signs in to GitHub as from this folder, whether that was compared and not guessed)."""
    question = f"url={url}\n\n" if url.lower().startswith("http") else f"protocol=https\nhost={HOST}\n\n"
    _, out, _ = run(["git", "credential", "fill"], cwd=cwd, stdin=question)
    found = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    password = found.get("password", "")
    if password:
        for name in names:
            if token_of(run, name) == password:
                return name, True
    user = found.get("username", "")
    return (user, False) if LOGIN_RE.fullmatch(user) else ("", False)


def can_push(run, account: str, slug: str) -> bool | None:
    """Whether `account` may push to `slug` (None when GitHub could not be asked or the repo is not there)."""
    token = token_of(run, account)
    if not token:
        return None
    code, out, _ = run(["gh", "api", f"repos/{slug}", "--jq", ".permissions.push"], token=token)
    return out.strip() == "true" if code == 0 else None


def check(run, cwd: str, allow_owner: str = "") -> dict:
    """Everything a push from `cwd` depends on. `ok` False means: do not push, act on `problems` first."""
    names, active = signed_in(run)
    where = origin(run, cwd)
    reading = {
        "accounts": names, "active": active, "pusher": "", "sure": False, "defaultOwner": DEFAULT_OWNER,
        "origin": f"{where['owner']}/{where['repo']}" if where["owner"] else "", "canPush": None, "problems": [], "notes": [],
    }
    problems = reading["problems"]
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
        if reading["pusher"] and reading["sure"]:
            reading["canPush"] = can_push(run, reading["pusher"], reading["origin"])
            if reading["canPush"] is False:
                problems.append(f"{reading['pusher']} may not push to {reading['origin']}. Fix: python push_as.py invite {reading['origin']}")
    reading["ok"] = not problems
    who = reading["pusher"] or ("the SSH key's account" if where["ssh"] else "nobody")
    how = "Cairn push-as" if reading["sure"] and reading["pusher"].lower() == active.lower() else "not Cairn's switch"
    reading["line"] = f"Pushed as: {who} ({how}) -> {reading['origin'] or 'no origin'}"
    return reading


def invite(run, slug: str) -> str:
    """Let the account Cairn picked push to `slug`, a repo of another account signed in on this computer."""
    owner = slug.split("/", 1)[0]
    names, active = signed_in(run)
    account = next((name for name in names if name.lower() == owner.lower()), "")
    if not account:
        raise PushError(f"{owner} is not an account the GitHub CLI is signed in to here, so it is not ours to change.")
    if not active or active.lower() == account.lower():
        return f"{account} owns {slug} and is the account that pushes: nothing to invite."
    if can_push(run, active, slug):
        return f"{active} can already push to {slug}."
    code, out, err = run(["gh", "api", "-X", "PUT", f"repos/{slug}/collaborators/{active}", "-f", "permission=push"], token=token_of(run, account))
    if code != 0:
        raise PushError(f"Could not invite {active} to {slug}: {err.strip() or 'GitHub refused'}")
    try:
        invitation = json.loads(out).get("id") if out.strip() else None
    except ValueError:
        invitation = None
    if invitation:
        code, _, err = run(["gh", "api", "-X", "PATCH", f"user/repository_invitations/{invitation}"], token=token_of(run, active))
        if code != 0:
            raise PushError(f"{active} was invited to {slug} but could not accept: {err.strip() or 'GitHub refused'}")
    if not can_push(run, active, slug):
        raise PushError(f"{active} still may not push to {slug} after the invitation.")
    return f"{active} can now push to {slug} (invited by {account}, accepted)."


def create(run, name: str, cwd: str, public: bool = False) -> str:
    """A new repo under DEFAULT_OWNER, made with that account's own sign-in, ready for the picked account to push."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name):
        raise PushError(f"'{name}' is not a repo name.")
    slug = f"{DEFAULT_OWNER}/{name}"
    token = token_of(run, DEFAULT_OWNER)
    if not token:
        raise PushError(f"The GitHub CLI is not signed in as {DEFAULT_OWNER} on this computer. Needs the user: gh auth login")
    made = "already there"
    if run(["gh", "api", f"repos/{slug}", "--jq", ".full_name"], token=token)[0] != 0:
        code, _, err = run(["gh", "api", "-X", "POST", "user/repos", "-f", f"name={name}", "-F", f"private={'false' if public else 'true'}"], token=token)
        if code != 0:
            raise PushError(f"Could not create {slug}: {err.strip() or 'GitHub refused'}")
        made = "created " + ("public" if public else "private")
    if run(["git", "rev-parse", "--git-dir"], cwd=cwd)[0] == 0 and not origin(run, cwd)["url"]:
        run(["git", "remote", "add", "origin", f"https://{HOST}/{slug}.git"], cwd=cwd)
    return f"{slug} {made}. {invite(run, slug)}"


def selftest() -> int:
    """The rules, against a pretend computer: two accounts, Cairn's switch on `work`, repos under `juw12`."""
    tokens = {"juw12": "t-main", "work": "t-work"}
    world = {"origin": "https://github.com/juw12/app.git", "push": {("work", "juw12/app"): True}, "repos": {"juw12/app"}, "calls": []}

    def fake(args, cwd=None, stdin=None, token=None):
        world["calls"].append(args)
        who = next((name for name, value in tokens.items() if value == token), "work")
        if args[:3] == ["gh", "auth", "status"]:
            hosts = [{"login": "work", "active": True}, {"login": "juw12", "active": False}]
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
            return 0, "username=x\npassword=t-work\n", ""
        if args[:2] == ["gh", "api"] and "POST" in args:
            new_name = next(arg.split("=", 1)[1] for arg in args if arg.startswith("name="))
            world["repos"].add(f"{who}/{new_name}")
            return 0, "{}", ""
        if args[:2] == ["gh", "api"] and "PUT" in args:
            world["invited"] = (who, args[4])
            return 0, '{"id": 7}', ""
        if args[:2] == ["gh", "api"] and "PATCH" in args:
            slug = world["invited"][1].split("/collaborators/")[0].replace("repos/", "")
            world["push"][(who, slug)] = True
            return 0, "", ""
        if args[:2] == ["gh", "api"]:
            slug = args[2].replace("repos/", "")
            if slug not in world["repos"]:
                return 1, "", "Not Found"
            allowed = who == slug.split("/")[0] or world["push"].get((who, slug), False)
            return 0, ("true" if allowed else "false") if ".permissions.push" in args else slug, ""
        return 1, "", "unexpected"

    failures = []

    def expect(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        if not condition:
            failures.append(label)

    reading = check(fake, ".")
    expect("pusher is the account Cairn's switch is on, compared and not guessed", reading["pusher"] == "work" and reading["sure"])
    expect("a juw12 repo the pusher may write to is ok", reading["ok"] and reading["line"] == "Pushed as: work (Cairn push-as) -> juw12/app")
    world["origin"] = "https://github.com/work/app.git"
    world["repos"].add("work/app")
    expect("a repo under the pushing account is refused by default", not check(fake, ".")["ok"])
    expect("...and allowed when the request named that owner", check(fake, ".", allow_owner="work")["ok"])
    world["origin"] = "https://github.com/juw12/locked.git"
    world["repos"].add("juw12/locked")
    expect("no push rights is a problem with its fix", "invite juw12/locked" in " ".join(check(fake, ".")["problems"]))
    expect("invite: owner invites, pusher accepts, rights verified", "can now push" in invite(fake, "juw12/locked") and check(fake, ".")["ok"])
    world["origin"] = ""
    expect("no origin points at create", "create NAME" in " ".join(check(fake, ".")["problems"]))
    message = create(fake, "fresh", ".")
    expect("create: repo lands under juw12, private, origin set, pusher can push", "juw12/fresh created private" in message and world["origin"].endswith("juw12/fresh.git") and check(fake, ".")["ok"])
    expect("the account is never switched", not any(call[:3] == ["gh", "auth", "switch"] for call in world["calls"]))
    world["origin"] = "git@github.com:juw12/app.git"
    reading = check(fake, ".")
    expect("an SSH origin is reported as not Cairn's switch", reading["pusher"] == "" and reading["notes"] and "SSH key" in reading["line"])
    try:
        invite(fake, "stranger/repo")
        expect("a repo of an account that is not ours is never touched", False)
    except PushError:
        expect("a repo of an account that is not ours is never touched", True)
    print(f"  {'OK' if not failures else 'FAILED'}: push_as selftest")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("action", nargs="?", default="check", choices=["check", "create", "invite"])
    parser.add_argument("name", nargs="?", help="create: repo name; invite: OWNER/REPO")
    parser.add_argument("--dir", default=".", help="the clone to read (default: this folder)")
    parser.add_argument("--allow-owner", default="", help="the request named a repo of this other account of the user's")
    parser.add_argument("--public", action="store_true", help="create: make the new repo public")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    cwd = str(Path(args.dir).resolve())
    try:
        if args.action == "create":
            if not args.name:
                parser.error("create needs a repo name")
            print(create(system_run, args.name, cwd, args.public))
        elif args.action == "invite":
            if not args.name or "/" not in args.name:
                parser.error("invite needs OWNER/REPO")
            print(invite(system_run, args.name))
    except PushError as error:
        print(f"Not done: {error}", file=sys.stderr)
        return 1
    reading = check(system_run, cwd, args.allow_owner)
    if args.json:
        print(json.dumps(reading, indent=1))
    else:
        print(reading["line"])
        print(f"Signed in: {', '.join(reading['accounts']) or 'nobody'}. New repos go under {DEFAULT_OWNER}.")
        for note in reading["notes"]:
            print(f"Note: {note}")
        for problem in reading["problems"]:
            print(f"DO NOT PUSH: {problem}")
    return 0 if reading["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
