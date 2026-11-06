# Refine log — juw12.github.io/p/<slug>/ landing pages (50 pages)

Rubric: `refine/rubric.md` (frozen before work started).

**Judge note:** no independent judge was available. GitHub Copilot CLI is blocked by org policy
("Access denied by policy") and local Ollama has no models installed. All soft scores below are
**SELF-JUDGED** by the same agent that built the pages; treat them as indicative, not independent.
Hard gates (G1–G8) are objective and machine-checked with `tools/check.py` (Playwright + HTML parsing).

## Gates (objective) — final run `refine/check_final.json`
| Gate | Check | Result |
|---|---|---|
| G1 | 0 JS errors | 50/50 pass |
| G2 | no horizontal overflow at 390 px and 1280 px | 50/50 pass |
| G3 | every original CTA href still present | 50/50 pass |
| G4 | title/description/canonical/OG/JSON-LD preserved vs old page | 50/50 pass |
| G5 | no mojibake | 50/50 pass |
| G6 | no placeholders / empty sections | 50/50 pass |
| G7 | reduced-motion guard + img alt | 50/50 pass |
| G8 | ≥5 content sections | 50/50 pass |

## Rounds
1. Built generator + data extraction from 50 READMEs. Check r1: 17 pages failing (phone overflow from
   view-switch/highlight, 6 thin pages <5 sections, og:image on 4 pages that never had one → checker
   now compares to the old page). Fixed phone CSS, added README-faithful overrides for thin pages.
2. Check r2: 0 failing. Visual review found: related-project thumbnails blank in captures (lazy-load
   artefact only — verified loaded in a real browser), junk privacy/limits text extracted on 10 pages
   (e.g. Jeda "sw.js precache", airiz firmware version, handoff TODOs), `: ,` join artefacts, hero
   sticker overlapping subtitle. Fixed via `content/*.json` overrides + `tidy()` in the renderer +
   sticker repositioned.
3. Phone review found sections below the hero lost side padding (`section.block` padding shorthand
   overrode `.wrap`). Fixed. Final check: 0 failing.

## Soft scores (SELF-JUDGED, sample: glow, steward, jeda, signals, cozy-island, upwind)
| Criterion | Weight | Old template | New |
|---|---|---|---|
| S1 Specificity (README-true content, no generic filler) | .30 | 3 | 8.5 |
| S2 Visual richness | .25 | 5 | 9 |
| S3 Conversion clarity (CTAs, get-it paths) | .20 | 6 | 9 |
| S4 Distinctiveness between pages | .15 | 2 | 7.5 |
| S5 Craft (responsive, a11y, polish) | .10 | 7 | 8.5 |
| **Weighted** | | **4.35** | **8.58** |

Stop reason: all gates pass and self-judged score ≥ 8.5 target.

## Known residual weaknesses
- S4: pages share one skeleton (themed per kind: app/dev/game/sim + per-project accent); not
  bespoke like Buddy.
- Pages whose README is thin still get fewer sections (only README-backed content is shown; nothing invented).
- 4 projects have no shot.jpg on the original site; their hero uses the generated preview card.


## Round 2 — "fix the weak spots" (user request)
Weak spots from round 1 and what was done:
1. **Shared skeleton (S4)** → 6 visual themes (arcade, blueprint, tech, calm, clean, playful), each with
   its own font pair, background, card/button styling and hero layout (split hero for tech/clean/blueprint,
   terminal caret for tech, neon glow for arcade, alternating bands for clean).
2. **Thin pages** → "Under the hood" section on 48 pages built only from real repo data: detected stack
   (file types + package.json / requirements / pyproject / Cargo deps, tests, i18n), file count, last-updated
   date, and a "Recently shipped" timeline of real filtered commit subjects with a link to the GitHub history.
   atomize is excluded (monorepo, facts would mislead); scopeguard is excluded (code moved to Steward) and
   instead got README-true "Where ScopeGuard lives now" steps, a shipped checklist, and Steward as first
   related card. Every page now has ≥6 sections.
3. **4 pages without screenshots** → real visuals: Toolsmith web UI + real terminal demo (tools), renders of
   the repo's own assets (etsy-prompts), source/file-tree views labelled "source code" (outlook-archiver,
   plm-aml-approval).
Extra polish found during review: stale related-card placeholders (plm-aml-approval now has a shot),
single-image galleries capped at native width (no blurry upscale), compact 2-up stat grid on phones.

Check r4: 50/50 pages pass all gates (0 JS errors, no h-overflow 390/1280, CTAs kept, SEO/JSON-LD kept,
no mojibake, no placeholders, reduced-motion + alt, ≥5 sections).

## Soft scores round 2 (SELF-JUDGED — no independent judge available)
| Criterion | Weight | Round 1 | Round 2 |
|---|---|---|---|
| S1 Specificity | .30 | 8.5 | 9 |
| S2 Visual richness | .25 | 9 | 9.5 |
| S3 Conversion clarity | .20 | 9 | 9 |
| S4 Distinctiveness | .15 | 7.5 | 9 |
| S5 Craft | .10 | 8.5 | 9 |
| **Weighted** | | **8.58** | **9.13** |

## Remaining honest notes
- Themes are shared by family (6 looks across 50 pages), not hand-built per project like Buddy.
- Hood "Recently shipped" appears only where ≥2 meaningful commits exist (32 pages); the rest show the stack only.
- outlook-archiver / plm-aml-approval visuals are source-code views (these are internal tools with no public UI).

## Push
- Cairn (added to the site mid-round, old template) was brought into the generator too: README-faithful content, calm theme, real repo facts. 51/51 pages pass all gates (check_r6).
- Checker G6 narrowed: 'TODO' next to FIXME/HACK is product copy (Cairn), not a placeholder.
- Pushed to juw12/juw12.github.io as eaf142c; live pages verified (cairn, steward, scopeguard).



## Round 3 — "fix": per-page design + build details everywhere

**Per-page design DNA** (`tools/design.py`), applied by `tools/build_landing.py`:
- Every page gets its own Google display font (51 distinct, all css2 URLs verified 200).
- Unique combination of hero layout (center / split / split-r / poster / editorial), background texture
  (12 kinds), card style (6) and heading treatment (6); no two pages share the same combination.
- A hand-drawn inline SVG emblem per project (51 distinct).
- Project-specific section headlines (why / ideas / features / steps / checklist / quick / CTA band), README-faithful.

**"How it's built" on the two pages that lacked it**
- ScopeGuard: facts now come from its new home `juw12/steward/apps/playground` (`SOURCE_OVERRIDE` in
  `tools/repo_facts.py`): Python + JavaScript + HTML/CSS, PWA + service worker, automated tests, 38 files,
  with a note that it moved and a link to the folder.
- Atomize: stack as stated in its README (Next.js 14, Claude, Lemon Squeezy), clearly labelled as from the
  README, with a note that the app code isn't in the public repo yet. No repo facts invented.
- Result: 51/51 pages have the hood section.

**Checks**: gates `refine/check_r7.json` 51/51 pass. Visual: 1280px on 23 pages across all 5 layouts and
390px on poster/editorial/split-r pages; 0 JS errors, no horizontal scroll.

**Self-judged score**: S4 distinctiveness 6 → 8.5 (pages now differ in type, layout, texture, emblem
and copy, but still share one generator and section skeleton, unlike the hand-built Buddy page).
Overall ≈ 9/10, self-judged.
