---
name: design
description: Juwen's single /design command for his projects - improves the APP's own UI (in its GitHub repo, against objective gates A1-A8 + screenshot review, tests must pass, shipped as a PR), syncs the brand (app accent + live screenshots) into the project's landing page, and builds/checks/publishes the landing page at juw12.github.io/p/<slug>/ via the project-landing skill. Use when the user types /design (with or without a project name), "design pass", "make <app> look great", "polish the app and its landing page", or asks to keep an app and its landing page on-brand.
---

# /design — app UI + brand sync + landing page

One command, three layers, always in this order: **app → brand → landing**. The app is the source of truth;
the landing page follows it.

CLI: `C:\Users\juwen_lie\AppData\Local\Programs\Python\Python313\python.exe ~/.vector/skills/design/tools/design_cmd.py <cmd>`
(`D` below). Landing engine: `~/.vector/skills/project-landing/` (read its SKILL.md for landing-only work).
Long steps (`report`, `test`, `finish`, full landing checks) can exceed 120 s: run them with `exec_command` and poll.

| Path | What |
|---|---|
| `tools/design_cmd.py` | the command: `status`, `report`, `start`, `audit`, `compare`, `test`, `sync`, `finish`, `landing …` |
| `tools/app_audit.py` | Playwright audit at 1280 + 390 px → gates A1–A8, screenshots, brand facts |
| `tools/brand.py` | app accent vs landing accent (ΔE), `--apply` writes landing overrides, `--gallery` adds live screenshots |
| `state/apps.json` | per app: checkout, web root, tests, live URL, audits; set `repo`/`path`/`routes` here to override |
| `workspace/<owner>__<repo>/` | app checkouts (sparse for `juw12/projects` and `juw12/portfolio` monorepos) |
| `out/<slug>/<label>/` | `audit.json` + screenshots (`baseline`, `after`, `live`); `out/report.md` ranking |

## What the user can type

| Input | Do |
|---|---|
| `/design` | `D status` (new landing pages, audit state) and, if no recent ranking, `D report` → suggest the worst 3 |
| `/design <app>` | full pass below |
| `/design <app> app` / `brand` / `landing` | only that layer |
| `/design new` | landing pipeline for new projects (`D landing status`, then project-landing workflow) |
| `/design all` | `D report` + landing refresh for all; then ask which apps get a full pass (each is a PR) |

## Full pass: `/design <app>`

**1. Start** — `D start <app>`: checks out the code, finds the web root and tests, runs the baseline audit
(local checkout served on 127.0.0.1; `--live` for the deployed site, `--url` if the app needs its own server),
dry-runs the brand check, builds + checks the landing page, prints the TO-DO list.
If the app needs a server (Python/Node), start it yourself per its README and use `--url`.

**2. Freeze the rubric** (write it in `out/<app>/rubric.md` before editing):
- Hard gates A1–A8 must not regress; every failing gate should improve, ideally to 0:
  A1 no JS/console errors · A2 no horizontal overflow (1280/390) · A3 viewport meta · A4 WCAG AA contrast
  (4.5:1, 3:1 large) · A5 phone tap targets ≥ 32 px (aim 44) · A6 no text < 12 px · A7 img alt + loads · A8 one h1 + title.
- Soft criteria (judge from the screenshots, before vs after): clear hierarchy, consistent spacing scale,
  one accent used with intent, readable line length, sensible empty/loading/error states, dark mode if the app has one.
- Constraints: keep the app's identity (its accent, font, layout, voice). Fix, don't redesign, unless asked.
  No behaviour changes, no copy changes that alter facts, no new dependencies, no build-system changes.

**3. Edit the app** in `workspace/…/<path>` (find the CSS/tokens first; prefer changing design tokens/variables
over one-off overrides). Typical fixes: raise muted text colour to ≥ 4.5:1, min-height 44 px on buttons/pills
on phone, 12 px floor for labels/counts, `theme-color` meta, missing alt text.
After each batch: `D audit <app> --label after`, `D compare <app>`, look at both screenshots side by side
(`image()`), keep changes that improve, revert those that don't. Stop when gates pass or no further gain.

**4. Finish** — `D finish <app>` (add `--gallery` to put a live-app screenshot on the landing page):
runs the app's tests (must pass) → after-audit → compare (aborts on any regression) → `brand --apply`
(landing accent follows the app when ΔE > 12) → landing build + gates → commits app changes on branch
`design/<app>-<date>` and the landing page locally. Show the user the before/after table and screenshots.

**5. Ship (only when the user says so)** — `D finish <app> --push`: pushes the branch and opens a PR in the
app's repo (table of gate counts in the body) and pushes the landing page. `--merge` squash-merges the PR;
use it only if the user explicitly asks. After merge, Pages redeploys the app; re-run `D audit <app> --live`
to confirm, and re-run `D sync <app> --apply --gallery` if you want the live screenshot refreshed.

## Rules

- Never push to an app's default branch directly; app changes go through a PR unless the user says merge.
- Never touch `p/index.html`, `p/landing.json` or Buddy (project-landing's publish enforces this).
- Facts only on the landing page; brand sync changes colours/screenshots, never claims.
- A pass with no measurable improvement is not shipped (finish warns; say so instead of claiming success).
- Scores and "looks better" are self-judged unless the user reviewed the screenshots — say so.
- Don't start a full pass on many apps at once without asking; each one is a PR to review.

## Gotchas

- The bundled Vector python lacks Playwright; always use the system Python path above.
- Local and live audits gave identical counts for Cairn, so baseline/after both on the local checkout is a fair comparison.
- `juw12/projects` is a monorepo: the checkout is sparse; `git sparse-checkout add <path>` happens automatically.
- Some apps' live URL carries `?demo=1`; the local audit reuses that query string.
- The contrast probe skips text over background images; check those by eye in the screenshots.
- First baseline findings (Nov 2026): Cairn 106 open issues (A4 muted nav labels 3.33:1, A5 28 px buttons, A6 10.5 px labels),
  Glow 18 (A4, A5 28 px pills); Cairn's app accent #d9481f vs landing teal #0f766e (ΔE 101) → brand sync candidate.
