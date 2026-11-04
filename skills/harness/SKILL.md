---
name: harness
description: Discover and run a project's build/test/lint commands and report pass/fail truthfully. Use when you need to actually RUN and verify a project (build, test, lint, CI) rather than only read code. Trigger on "build it", "run the tests", "does it pass", "verify the build", "lint", "CI", "make sure it works".
---

# Execution Harness

Run and verify - never guess.

## Workflow
1. **Discover** the real commands from the project, not from memory:
   - `package.json` -> `scripts`; `pyproject.toml` / `Makefile` / `justfile`;
     `.github/workflows/*.yml`; `README`; existing `scripts/`.
2. **Run** them from the project root with `bash`. Capture exit code + output.
3. **Report**: `command -> exit code -> key output -> PASS/FAIL`.
4. If a command is missing or fails to start, say so explicitly.

## Rules
- Paste REAL output. Never fabricate a pass.
- Do not "fix" the code unless asked - report the failure.
- Prefer the project's own commands over invented ones.
- For hermetic/CI parity, note the exact command so it can be re-run.
