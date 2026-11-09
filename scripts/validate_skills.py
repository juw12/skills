"""Repository checks for the skills collection. Exit code 1 on any failure.

1. Every skills/<name>/SKILL.md starts with front matter that has name and description.
2. The refine-loop and hone skills pass their own objective checkers (check_skill.py).
3. Shared helper scripts copied into several skills (so each installs standalone)
   are byte-identical, so a fix in one copy cannot silently miss the others.
4. Every Python file compiles.

Usage: python scripts/validate_skills.py
"""
import hashlib
import py_compile
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
FRONT_MATTER = re.compile(r"^\ufeff?---\s*\r?\n(.*?)\r?\n---", re.S)


def check_front_matter(errors):
    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    if not skill_files:
        errors.append("no skills/*/SKILL.md found")
    for path in skill_files:
        match = FRONT_MATTER.match(path.read_text(encoding="utf-8"))
        if not match:
            errors.append(f"{path.relative_to(ROOT)}: missing --- front matter ---")
            continue
        keys = {line.split(":", 1)[0].strip().lower() for line in match.group(1).splitlines() if ":" in line}
        for required in ("name", "description"):
            if required not in keys:
                errors.append(f"{path.relative_to(ROOT)}: front matter has no '{required}'")
    return len(skill_files)


def check_refine_loop(errors):
    checker = SKILLS / "refine-loop" / "check_skill.py"
    skill = SKILLS / "refine-loop" / "SKILL.md"
    if not checker.exists():
        return
    result = subprocess.run([sys.executable, str(checker), str(skill)], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("refine-loop/SKILL.md fails its own check_skill.py:\n" + result.stdout[-1500:])



def check_hone(errors):
    checker = SKILLS / "hone" / "check_skill.py"
    skill = SKILLS / "hone" / "SKILL.md"
    if not checker.exists():
        return
    result = subprocess.run([sys.executable, str(checker), str(skill)], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("hone/SKILL.md fails its own check_skill.py:\n" + result.stdout[-1500:])
    mandate = (SKILLS / "hone" / "mandate.md").read_text(encoding="utf-8")
    for marker in ("Stopped: all done", "Stopped: session limit", "Stopped: blocked", "Stopped: needs you"):
        if marker not in mandate:
            errors.append(f"hone/mandate.md is missing the stop reason '{marker}'")


def check_shared_copies(errors):
    by_name = defaultdict(list)
    for path in SKILLS.glob("*/scripts/*.py"):
        by_name[path.name].append(path)
    for name, paths in sorted(by_name.items()):
        if len(paths) < 2:
            continue
        digests = {hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        if len(digests) > 1:
            listed = ", ".join(str(path.relative_to(ROOT)) for path in sorted(paths))
            errors.append(f"copies of {name} differ: {listed}")


def check_compiles(errors):
    for path in sorted(ROOT.rglob("*.py")):
        if ".git" in path.parts:
            continue
        try:
            py_compile.compile(str(path), doraise=True, cfile=None)
        except py_compile.PyCompileError as error:
            errors.append(f"{path.relative_to(ROOT)}: {error.msg}")


def main():
    errors = []
    count = check_front_matter(errors)
    check_refine_loop(errors)
    check_hone(errors)
    check_shared_copies(errors)
    check_compiles(errors)
    if errors:
        print("FAILED")
        for error in errors:
            print(" -", error)
        return 1
    print(f"OK: {count} skills, front matter valid, shared scripts identical, all Python compiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
