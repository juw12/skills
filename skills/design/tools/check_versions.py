"""Version-history gate A9 for /design (SKILL.md, Rules).

Checks that an app keeps one version list, shows it inside the app and has a changelog that matches.
Usage: python check_versions.py <app checkout> [--build <number or version now shipping>]
Exit 0 = every gate passes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv"}
CODE_SUFFIXES = {".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".py", ".cs", ".vue", ".svelte"}


def find_versions_file(root: Path):
    found = [
        path
        for path in root.rglob("versions.json")
        if not SKIP_DIRS.intersection(path.relative_to(root).parts)
    ]
    return sorted(found, key=lambda path: len(path.parts))[0] if found else None


def entry_id(entry: dict) -> str:
    return str(entry.get("build", entry.get("version", "")))


def sort_key(entry: dict):
    numbers = [int(part) for part in re.findall(r"\d+", entry_id(entry))]
    return (entry.get("date", ""), numbers)


def shown_in_app(root: Path, versions_file: Path) -> bool:
    for path in root.rglob("*"):
        if path.suffix.lower() not in CODE_SUFFIXES or not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if SKIP_DIRS.intersection(parts) or parts[0] in {"tests", "test", "scripts"}:
            continue
        if path.name.startswith("sw."):
            continue
        try:
            if "versions.json" in path.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False


def check(root: Path, build_now: str | None) -> list[tuple[bool, str]]:
    results = []
    versions_file = find_versions_file(root)
    results.append((versions_file is not None, "one versions.json exists"))
    if versions_file is None:
        return results

    try:
        data = json.loads(versions_file.read_text(encoding="utf-8"))
    except ValueError as error:
        results.append((False, f"versions.json is valid JSON ({error})"))
        return results
    entries = data
    if isinstance(data, dict):
        entries = data.get("releases") or data.get("versions")
    is_list = isinstance(entries, list) and len(entries) > 0
    results.append((is_list, "versions.json holds a list of entries"))
    if not is_list:
        return results

    complete = all(
        isinstance(entry, dict)
        and entry_id(entry)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("date", "")))
        and str(entry.get("title", "")).strip()
        and isinstance(entry.get("changes"), list)
        and entry["changes"]
        for entry in entries
    )
    results.append((complete, "every entry has build or version, date, title, changes"))
    if not complete:
        return results

    ids = [entry_id(entry) for entry in entries]
    results.append((len(ids) == len(set(ids)), "no build or version listed twice"))
    newest_first = entries == sorted(entries, key=sort_key, reverse=True)
    results.append((newest_first, "newest first"))

    changelog = root / "CHANGELOG.md"
    in_step = changelog.exists() and all(
        str(entry["title"]) in changelog.read_text(encoding="utf-8") for entry in entries
    )
    results.append((in_step, "CHANGELOG.md names every entry"))
    results.append((shown_in_app(root, versions_file), "the app's own code reads versions.json"))
    if build_now is not None:
        results.append((ids[0] == str(build_now), f"newest entry is the shipping build {build_now}"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("checkout")
    parser.add_argument("--build", help="build number or version that is shipping now")
    args = parser.parse_args()
    results = check(Path(args.checkout).expanduser().resolve(), args.build)
    for ok, label in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    passed = sum(ok for ok, _ in results)
    print(f"  Version history gates: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
