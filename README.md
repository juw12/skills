# skills

**Agent skills I wrote for Claude Code, OpenCode, Codex and SkillMouse.** Plain `SKILL.md` files that work with any model.

The common thread: agents that **verify instead of claiming**. They run the checks, report honestly and stop when they should.

## Workflow skills

| Skill | What it does |
|---|---|
| [`hone`](skills/hone/SKILL.md) | `/hone`: improve-until-done with full autonomy. The agent owns the task like a senior expert (no approval questions, no excuses, 3 genuinely different approaches before "blocked"), runs a frozen-rubric loop with a separate judge, keep-best and blind pairwise checks, works a run queue until it is empty, and starts every final message with `Stopped: <reason>`. Successor of `refine-loop`. |
| [`refine-loop`](skills/refine-loop/SKILL.md) | The original loop, kept for agents that should ask before acting. Improve-until-done without babysitting: frozen rubric, baseline score, separate judge, keep-best, blind A/B anti-inflation check and hard stop rules. Includes an objective self-checker. |
| [`ambitious-founder`](skills/ambitious-founder/SKILL.md) | `/be-ambitious` + `/founder` in one. Raises any task (goal beyond the goal, expert-grade depth, outside judge, copy-ready rewritten prompt) and pressure-tests a business or product idea: 4-lens board (incl. a Make lens for hardware), simulated buyer panel, Van Westendorp pricing and unit economics, ending in a verdict computed by a script. Combines RoboNuggets' be-ambitious and Jake Schincariol's founder-skill (both MIT). |
| [`harness`](skills/harness/SKILL.md) | Finds and actually **runs** a project's build/test/lint commands and reports pass/fail truthfully. |
| [`heartbeat`](skills/heartbeat/SKILL.md) | A short, honest status of running jobs and services (servers, watchdogs, long tasks) that flags stalls. |
| [`delegator`](skills/delegator/SKILL.md) | Breaks a goal into small tasks, routes each to the best agent or skill, then combines the results. |
| [`soul`](skills/soul/SKILL.md) | Reviews drafts, docs and UI copy against a project's voice and principles, with minimal fixes. |
| [`memory-management`](skills/memory-management/SKILL.md) | Durable project memory (decisions, lessons, context) in an Obsidian vault, so it survives across sessions. |
| [`widgettheme`](skills/widgettheme/SKILL.md) | Applies "The Morning Paper" editorial design system (cream paper, ink black, newspaper red, serif headlines). |

## Design skills

One `/design` command for an app and its landing page. The app is the source of truth; the landing page follows it.

| Skill | What it does |
|---|---|
| [`design`](skills/design/SKILL.md) | `/design <app>`: audits the app's own UI on desktop and phone against 8 objective gates (contrast, tap targets, text size, overflow, alt text, errors, viewport, headings), fixes it in its repo, runs the app's tests, refuses regressions and ships a PR with a before/after table. Then syncs the brand (app accent + live screenshot) into the landing page. Playwright + `gh`. |
| [`project-landing`](skills/project-landing/SKILL.md) | README-faithful landing pages for every project on `juw12.github.io/p/<slug>/`: each page gets its own font, layout, emblem and headlines (a gate blocks duplicates), a "How it's built" section from real repo facts, page gates, screenshots and a publish step that can't touch the gallery. |

## Push Lab QA skills

Companion skills for [Push Lab](https://github.com/juw12/projects/tree/main/apps/pushlab): self-hosted push notifications (Beacon) and real-phone testing (Tether). Each skill ships the same zero-dependency `scripts/pushlab_cli.py`, so you can install it on its own.

| Skill | What it does |
|---|---|
| [`beacon-push`](skills/beacon-push/SKILL.md) | Send and inspect push notifications through Beacon: Web Push, FCM, ntfy, Bark, Gotify, Apprise. |
| [`tether-android-qa`](skills/tether-android-qa/SKILL.md) | Drive a real Android phone or emulator through Tether: read the screen, tap, type, swipe, read logcat. |
| [`push-qa-e2e`](skills/push-qa-e2e/SKILL.md) | End-to-end check: subscribe the phone, send a push, assert it shows in the shade, tap it, verify the app opens. |

## Agents

[`agents/`](agents) has OpenCode subagent versions of `harness`, `heartbeat`, `delegator`, `soul` and `memory-management`, plus `web-researcher`.

## Install

```bash
git clone https://github.com/juw12/skills
```

Copy any folder from `skills/` into your tool's skills folder:

| Tool | Skills folder |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` (agents: `~/.config/opencode/agent/`) |
| Codex | `~/.codex/skills/` |
| [SkillMouse](https://github.com/juw12/skillmouse) | **Settings > Sources > Add folder** and pick `skills/`, to run them with any model from your mouse |

Check `refine-loop` against its own rubric: `python skills/refine-loop/check_skill.py skills/refine-loop/SKILL.md`
(and `hone`: `python skills/hone/check_skill.py skills/hone/SKILL.md`).

## License

MIT
