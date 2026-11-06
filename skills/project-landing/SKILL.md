---
name: project-landing
description: Juwen's project landing-page pipeline for juw12.github.io/p/<slug>/ - turns a project's gallery page + README + GitHub repo into a rich, README-faithful landing page with its own design (unique font, layout combo, emblem, headlines), a "How it's built" section from real repo facts, quality gates, screenshots and a safe publish. Use when the user adds a new project to the site, asks to make/redo/refresh a project landing page, says "landing page for <project>", "new project page", "update the /p/ pages", or wants the landing pages brought up to the same standard as the others. For app UI + brand + landing in one go, the /design skill (~/.vector/skills/design) drives this one.
---

# Project landing pages (juw12.github.io/p/)

Everything lives in this folder (`~/.vector/skills/project-landing/`):

| Path | What it is |
|---|---|
| `tools/landing.py` | **One entry point**: `status`, `ingest`, `facts`, `build`, `check`, `shoot`, `publish` |
| `tools/ingest.py` | original gallery page + README → `state/data.json` entry (facts only) |
| `tools/design.py` | per-page design DNA: `FONTS`, `STYLE`, `COPY`, `ART` (+ CSS) |
| `tools/enrich.py` | theme (`THEMES`), stack + shipped log from repo facts, `HOOD` special cases |
| `tools/repo_facts.py` | GitHub facts via `gh` (`SOURCE_OVERRIDE` for moved code) |
| `tools/build_landing.py` | renderer |
| `tools/check.py`, `tools/dna_check.py` | gates G1–G8 (pages) and D1–D6 (design DNA) |
| `tools/shoot.py` | Playwright screenshots (system Chrome) |
| `state/data.json` | every page's content (source of truth; 51 projects at creation) |
| `state/content/<slug>.json` | hand overrides; any key replaces the extracted value |
| `state/gallery/<slug>/g*.jpg`, `state/readmes/`, `state/repo_facts.json` | assets and cached facts |
| `state/config.json` | repo, live URL, site clone + out dir, protected files, browser python |
| `site/juw12.github.io/` | the skill's own clone of the site repo (auto-pulled) |
| `out/p/<slug>/` | build output; `out/shots/` screenshots; `out/check.json` gate report |
| `history/refine_log.md` | how the pages got to their current standard (rubric, rounds, scores) |

Run everything with the **system Python** (has Playwright):
`C:\Users\juwen_lie\AppData\Local\Programs\Python\Python313\python.exe ~/.vector/skills/project-landing/tools/landing.py <cmd>`
(`L` below means that command.) Needs `gh` logged in as juw12 and Google Chrome installed.

## Hard rules

1. **Never touch** `p/index.html` (gallery), `p/landing.json`, or Buddy. `publish` aborts if any of them,
   or anything outside `p/`, changed. The gallery generator owns those; this skill only rewrites `p/<slug>/`.
2. **Facts only.** Every sentence must trace to the README, the original page, or the repo. No invented
   features, numbers, testimonials or stack. If the code isn't public, say so on the page (see `HOOD`).
3. Every page gets **its own** design DNA — never reuse another page's font, STYLE combo or emblem.
   `dna_check` (D1–D6) enforces this; do not publish with failures.
4. Don't claim a page is "10/10" or "validated": scores are self-judged unless the user judged them.
5. Ask before pushing if the user hasn't asked for it in this request (earlier rounds: "fix" implied push).

## Workflow: a new project appeared on the site

1. `L status` → lists NEW slugs (on the site, not in state) and REGENERATED ones (gallery generator rewrote a
   page back to its original format). The page must be in the original format to ingest.
2. `L ingest <slug> [--category "Featured"|"Solid: usable today"|"Engineering"|"Games"|"Tools and agent skills"|"Archive"]`
   Reads hero copy, CTAs, colours and `<head>` from the original page, fetches the README with `gh`, extracts
   about/features/steps/quick start/limits/privacy/FAQ, downloads README screenshots (≥500 px) into
   `state/gallery/<slug>/`, picks 3 related projects. Category comes from the profile README section.
3. **Review the entry** in `state/data.json` against the README. Extraction is heuristic: fix anything wrong,
   thin or techy by writing `state/content/<slug>.json` (then re-run ingest; overrides merge last).
   Common keys: `about` (≤4 paras), `features` [{title, body}] (6–8), `ideas` (3), `steps` + `steps_title`,
   `checklist` (≤8 short), `quickstart` {heading, lang, code}, `privacy` + `privacy_title`, `limits`,
   `readme_faq` [{q, a}], `extra_stats` [[value, label]], `devices` [{device, how}], `band_title`.
   Keep copy plain and user-facing (README wording, no file paths in headlines).
4. **Design DNA** in `tools/design.py` — add one entry to each dict for the slug:
   - `FONTS[slug] = ("Young+Serif", "Young Serif", 400)` → Google Fonts css2 family spec, CSS family, heading
     weight. Pick a display font that fits the project's personality and isn't used yet (D1/D6 check it).
   - `STYLE[slug] = (hero, background, card, heading)` from
     hero `center|split|split-r|poster|editorial`, background `dots|grid|fine|lines|diag|plus|waves|topo|rings|stars|checker|paper`,
     card `soft|outline|brutal|flat|ticket|pill`, heading `center|marker|left|upper|italic|outline`.
     The 4-tuple must be unique across all pages. Balance layouts (check counts with a quick Counter).
   - `COPY[slug] = {"why", "ideas", "features", "steps", "checklist", "quick", "band"}` → short section
     headlines in the project's own voice, faithful to the README (`why`, `features`, `band` required).
   - `ART[slug]` → hand-drawn inline SVG emblem body for a 200×200 viewBox using the classes from `ART_CSS`
     (`o` outline, `s` soft fill, `a` accent fill, `ao` accent stroke, `p` paper fill; see existing entries). One clear
     object that says what the project is (Cairn = stacked stones, CrewCup = coffee cup).
   - Theme: add the slug to a list in `enrich.THEMES` (arcade/blueprint/tech/calm/clean) or, for playful,
     to `PLAYFUL_OK` in `tools/dna_check.py`.
5. `L facts --only <slug>` → repo stack + shipped log. If the project's code moved, add the new URL to
   `SOURCE_OVERRIDE` in `tools/repo_facts.py`. If the listed repo is a monorepo that would mislead, add the
   slug to `SKIP_REPO_FACTS` and, if the README states a stack, add a `HOOD` entry in `tools/enrich.py`
   with `stack`, a `note` saying where it comes from, and a `link`.
6. `L build --only <slug>` then `L check --only <slug> --fonts` → must be D 1/1 and gates 1/1.
7. Visual check (required — gates don't judge looks):
   `L shoot <slug> --w 1280 --h 820` and `L shoot <slug> --w 390 --h 844`, then look at both images
   (`image()` in python). Check: hero readable, emblem sized well, no overlap, outline/marker headings legible,
   stats row in order, screenshots load, "How it's built" present. Fix in design/content and rebuild.
8. `L publish --only <slug> -m "Add <Name> landing page"` (commits locally), then with `--push` once the user
   wants it live. It pulls first, copies only `index.html` + `g*.jpg`, verifies protected files, pushes,
   and polls the live page with a cache-buster until it serves the new build.
9. Reply briefly: what's live (URL), checks passed, commit link, and any README gaps you labelled.

## Other jobs

- **Refresh all pages** (README or repo changed): `L facts`, `L build`, `L check` (51 pages ≈ 1 min — run it
  via `exec_command` and poll, or the 120 s tool timeout hits), shoot a sample of each hero layout, publish.
- **Improve the standard** ("make it 10/10"): use the `refine-loop` skill with the rubric in
  `history/refine_log.md`; keep gates green, log the round there.
- **Regression guard**: after editing `build_landing.py`/`design.py`, rebuild everything and diff against the
  site clone; only intended pages should change.

## Gotchas learned the hard way

- `check.py` output redirected by PowerShell (`>`) is UTF-16; `landing.py check` avoids that by capturing it.
- Exact-path checks only: `crewcup/index.html` ends with `index.html`, so suffix matching flags the gallery falsely.
- The bundled Vector python has no Playwright; `browser_python` in `state/config.json` points at the system one.
- GitHub Pages takes ~1 min to deploy; always verify live with `?cb=<timestamp>`.
- `.hero.split.rev .stats` needs `order: 3` or stats jump above the copy (fixed in `design.py`; keep it).
- Poster/editorial heroes hide stickers and show a large emblem; center/split show a small emblem above the pill.
- ScopeGuard now lives in `juw12/steward/apps/playground`; Atomize's app code isn't public (README-stated stack only).
- The `repo_facts` run for all pages takes a while; use `--only` for one project.
