# Ship: every place the project shows up

For an artifact that is one of the user's projects (it has, or gets, a repo). At intent time (`SKILL.md`
step 0) add the four-versions gate and the five surfaces below to the end of the run queue; each is done
only when its gate passes.
A surface the run changed nothing on is ticked as `unchanged`, not skipped silently. Facts only: every
sentence and number written anywhere comes from the repo (`mandate.md` hard limits).

## 0. Who pushes, and where to

Before the first push in every clone: `python push_as.py check --dir <clone>`. Exit 1 = do not push; do
what it prints.

- **Who** is the user's choice, made in Cairn (Vibe page, *Pushes from this computer*, or
  `cairn vibe github push-as NAME`). Read it, never change it: no `gh auth switch`, no `git config
  credential.*`, no token in a remote URL. Push with plain `git push` and `gh`; they follow the switch.
- **Where** is `juw12`, whoever pushes. A new repo: `python push_as.py create <name>` (private; `--public`
  only when the request says so). It is created under juw12 with juw12's own sign-in for that one call, and
  the pushing account is invited so the push still goes out as picked. A repo of another account only when
  the request names it (`--allow-owner NAME`). Never create or move a repo to the pushing account because
  it happens to be the active one.
- Something only the owner may do (description, topics, Pages, secrets) and the pushing account may not:
  do not borrow the owner's sign-in; put the exact command in the final message under `needs you`.
- The printed `Pushed as: <account> (Cairn push-as) -> <repo>` line goes into the final message.

## The surfaces

| Surface | Source of truth | Update | Gate |
|---|---|---|---|
| **GitHub** | the project's repo, `juw12/<repo>` or its folder in `juw12/projects` | branch, PR, merge after checks pass. README, changelog or version file, release, repo description, topics and homepage say what shipped. | clean `git status`; local HEAD is on `origin/<default>`; `gh pr checks` or `gh run list -L 1` green |
| **Profile** | `juw12/juw12`, `README.md` | the project's card or bullet: sentence, test count, version, links. Never edit between `<!--live-->` markers or the `BUILDING` caption (an Action owns them). A new landing page also goes in `.github/landing.json`. Then **Featured** below. | `python featured.py README.md --check`; the pushed README on GitHub holds the new sentence |
| **Portfolio** | `juw12/projects`, `scripts/apps.json` (the entry with the project's `id`) | `summary` (120 visible characters at most), `description`, `version`, links; card art with `python scripts/portfolio_card.py <id>`. Never hand-edit a card in `juw12/portfolio`: its hourly `sync-cards` rebuilds them. After the merge: `gh workflow run sync-cards.yml -R juw12/portfolio`. Leave `order` and `portfolio_order` alone unless asked. Landing page `juw12.github.io/p/<slug>/`: the `project-landing` skill. | the sync run is green and `index.html` on `juw12/portfolio` `main` holds the new summary |
| **Obsidian** | the vault, `juw12/obsidian` (use the clone Cairn watches; none on this computer: clone it) | `GitHub/<repo>.md`: a dated line at the top of `## Changes` (what changed for a user, with the PR or commit link) and `updated:`. A run that shipped more than one change also gets `Update Log/<YYYY-MM-DD HHMM> <project> <what>.md` with Done / Result / Verification / Commit, like its neighbours. `notes/project-ranking.md` is Cairn's: read it, never write it. | the note's commit is on `origin/main` (Cairn's watcher may have committed it already: check `git status` first) |
| **Cairn** | the brain (same vault), through the `cairn` CLI (`python -m cairn` in the Cairn clone when it is not on PATH) | `cairn vibe skill /hone "<project>: v0 <x> -> <y>, gates <n>/<m>"`. A session this run started: `cairn vibe end --result shipped|partial "<one line>"`; never `start` one while `cairn vibe watch` tracks the work. A task note the run finished: `status: done`. | `cairn vibe status` shows the run; the session or task file has the entry |

## Four versions: Windows, Mac, iPhone, Android

A standing gate for every project, asked for or not: `python platforms.py --repo juw12/<repo>` (a folder
of the monorepo: `python platforms.py <profile README> --only <name>`). Exit 1 = a version is missing,
and each missing one is a run-queue item of this run.

| Version | What counts | How it is usually made |
|---|---|---|
| **Windows** | a download in a GitHub release (`.exe`, `.msi`, or a file named for windows) | the project's own packager on a `windows-latest` runner |
| **Mac** | a download in a GitHub release (`.dmg`, `.pkg`, or a file named for mac) | the same on a `macos-latest` runner; a Mac build cannot be made on Windows |
| **Android** | an `.apk` in a GitHub release | native, or the web app wrapped (Capacitor, Trusted Web Activity) and signed in CI |
| **iPhone** | the live web app on the home screen: it answers, has an `apple-touch-icon` and a manifest with `display: standalone` | manifest, icon and a service worker; no App Store, no `.ipa` |

- The README names all four and says how to get each (iPhone: Safari, Share, *Add to Home Screen*). The
  profile card and the portfolio entry link the downloads.
- Each version does the project's real job. Where the job needs the desktop itself, the phone version is
  the part that travels (view, capture, remote), and the README says what it does not do. A wrapper around
  the landing page does not count, and neither does a feature the project does not have.
- Name release files like the others (`<Name>-Windows-Setup.exe`, `<Name>-macOS.dmg`, `<Name>-android.apk`,
  `SHA256SUMS.txt`) so the gate and people recognise them. An unsigned build says so, with how to open it.
- Published is not run. Say for each version where it was started: this computer, an emulator
  (`tether-android-qa`), an iPhone-sized WebKit, or `built, not run on a device`.
- Private repos pay for runners: check `cairn vibe github` before adding Mac jobs (GitHub counts a Mac
  minute as ten).
- No app at all (a study, a model library, a skills collection): nothing to version. Write `Assumed: no
  app, because <what the repo holds>` and move on; a repo with a UI or a program a person starts is an app.

## Featured (GitHub profile)

`python featured.py <profile clone>/README.md --brain <vault> --write` (about a minute; it reads GitHub
and pushes nothing). Projects are scored from facts: test files, releases and downloads, a live demo that
answers, commits in total and in the last 30 days, stars, CI and Cairn's own ranking note. A folder of
`juw12/projects` competes like a whole repo.

1. **Order** is written by the script. Commit it as its own change (`profile: Featured by score`).
2. **`SWAP IN: A for B`** (A leads the weakest card by 5 points): build A's card from its own bullet (same
   sentence and links, plus `media/<slug>.jpg`, a real screenshot in the size of the other cards), move B
   back to the top of its group as a bullet, delete A's old bullet. Rerun `--check` until it passes.
3. **Pins** follow Featured, but GitHub has no API for them. With a signed-in browser the run can drive,
   set them at *Customize your pins*; otherwise the printed `Pins:` line is the run's `needs you`.
4. The weights (`SIGNALS` in `featured.py`) are frozen like a rubric: disagreeing with the result is a
   proposal for the final message, not an edit mid-run.

## Self-check

`python push_as.py --selftest`, `python featured.py --selftest` and `python platforms.py --selftest` (offline).
