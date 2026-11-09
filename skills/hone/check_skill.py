"""Objective checker for the refine-loop skill.

Hard gates are plain text checks, so no AI opinion is involved.
Usage: python check_skill.py <file.md> [more files...]
"""
import re
import sys
from pathlib import Path

GATES = {
    "frontmatter name + description": r"^---\s*\nname:.+\ndescription:.+\n---",
    "rubric frozen before generating": r"(?i)freeze the rubric|rubric is frozen",
    "baseline scored first": r"(?i)baseline",
    "separate judge / fresh context": r"(?i)fresh context",
    "objective checks override judge": r"(?i)override",
    "keeps best, rejects regressions": r"(?i)from best",
    "anti-inflation guard (pairwise)": r"(?i)pairwise",
    "numeric max rounds": r"MAX_ROUNDS[^\n]*\d",
    "plateau stop rule": r"(?i)plateau",
    "budget stop rule": r"(?i)budget",
    "blocked -> report, don't fake": r"(?i)blocked",
    "per-round log": r"(?i)refine_log",
    "safety boundary for autonomy": r"(?i)safety boundary",
    "honest final report (no 'perfect' claim)": r"(?i)never claim",
    "judge prompt template": r"(?i)judge prompt template",
}

MAX_WORDS = 1000


def check(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    passed = 0
    print(f"\n== {path.name} ==")
    for label, pattern in GATES.items():
        ok = re.search(pattern, text, re.MULTILINE) is not None
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    words = len(text.split())
    concise = words <= MAX_WORDS
    passed += concise
    print(f"  [{'PASS' if concise else 'FAIL'}] concise (<= {MAX_WORDS} words): {words}")
    # CRLF line endings stop the skill loader from reading the frontmatter (the skill then shows as "---").
    lf_only = b"\r\n" not in path.read_bytes()
    passed += lf_only
    print(f"  [{'PASS' if lf_only else 'FAIL'}] LF line endings (CRLF hides the skill)")
    total = len(GATES) + 2
    print(f"  Gates passed: {passed}/{total}  ->  {10 * passed / total:.1f}/10")
    return passed == total


if __name__ == "__main__":
    results = [check(Path(p)) for p in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
