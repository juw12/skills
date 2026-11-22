# Ship: every place the project shows up

For an artifact that is one of the user's projects (it has, or gets, a repo). At intent time (`SKILL.md`
step 0) add the four-versions gate, the findable gate and the five surfaces below to the end of the run
queue; each is done only when its gate passes. A surface the run changed nothing on is ticked as `unchanged`, not skipped
silently. Facts only: every sentence and number written anywhere comes from the repo (`mandate.md` hard
limits).

## 0. Who pushes, and where to

Before the first push in every clone: `python push_as.py check --dir <clone>`. Add `--needs workflow` when
the change touches `.github/workflows/`, `--needs settings` for a description, topics, secrets or
collaborators. Exit 1 = do not push; do what it prints.

- **Who** is the user's choice, made in Cairn (Vibe page, *Pushes from this computer*, or
  `cairn vibe github push-as NAME`). Read it, never change it and never go around it: no `gh auth switch`,
  no `GH_TOKEN` or other account's sign-in, no `git config credential.*`, no token in a remote URL. Push
  with plain `git push` and `gh`; they follow the switch.
- **What the picked account may not do** (`push_as.py` prints it: workflow files, settings, a new repo)
  stays undone. It goes in the final message under `needs you`, with the chip to press and the exact
  command to run afterwards. Everything the account may do is finished first.
- **Where** is `juw12`, whoever pushes. A new repo: `python push_as.py create <name>` (private; `--public`
  only when the request says so), which works only while juw12 is the picked account. A repo of another
  account only when the request names it (`--allow-owner NAME`). Never create or move a repo to the pushing
  account because it happens to be the active one.
- **Whose name is on the commit** is the clone's own `user.email`; it does not follow the switch.
  `push_as.py` stops a push to a public repo that would show an address its history has never shown.
- The printed `Pushed as: <account> (Cairn push-as) -> <repo>` line goes into the final message.

## The surfaces

| Surface | Source of truth | Update | Gate |
|---|---|---|---|
| **GitHub** | the project's repo, `juw12/<repo>` or its folder in `juw12/projects` | branch, PR, merge after checks pass. README, changelog or version file, release, repo description, topics and homepage say what shipped. | clean `git status`; local HEAD is on `origin/<default>`; `gh pr checks` or `gh run list -L 1` green |
| **Profile** | `juw12/juw12`, `README.md` | the project's card or bullet: sentence, test count, version, links. Never edit between `<!--live-->` markers or the `BUILDING` caption (an Action owns them). A new landing page also goes in `.github/landing.json`. Then **Featured** below. | `python featured.py README.md --check`; the pushed README on GitHub holds the new sentence |
| **Portfolio** | `juw12/projects`, `scripts/apps.json` (the entry with the project's `id`) | `summary` (120 visible characters at most), `description`, `version`, links; card art with `python scripts/portfolio_card.py <id>`. Never hand-edit a card in `juw12/portfolio`: its hourly `sync-cards` rebuilds them. After the merge: `gh workflow run sync-cards.yml -R juw12/portfolio`. Leave `order` and `portfolio_order` alone unless asked. Landing page `juw12.github.io/p/<slug>/`: the `project-landing` skill. | the sync run is green and `index.html` on `juw12/portfolio` `main` holds the new summary |
| **Obsidian** | the vault, which is also Cairn's brain | Follow the vault's own rules on this computer. Where Cairn installed a memory skill (`cairn-memory`), save through it: it knows the one folder this computer may write in. Notes other computers wrote (`GitHub/<repo>.md`, `notes/project-ranking.md`) are read, never edited. One note per run: what changed for a user, the PR or commit links, what was checked and what was not. Never commit or push the vault: Cairn syncs it. Only where the vault has no such rules: a dated line at the top of `## Changes` in `GitHub/<repo>.md`. | the memory skill's own check passes (`remember.py check`: the file is there and the vault's remote is up to date) |
| **Cairn** | the brain, through the `cairn` CLI (`python -m cairn` in the Cairn clone when it is not on PATH) | `cairn vibe skill /hone "<project>: v0 <x> -> <y>, gates <n>/<m>"`. A session this run started: `cairn vibe end --result shipped|partial "<one line>"`; never `start` one while `cairn vibe watch` tracks the work. A task note the run finished: `status: done`. What only another computer can do or check (start the Windows build, try it on a phone) goes out with `cairn handoff send`. A change that lives in a repo travels through GitHub, never as a handoff. | `cairn vibe status` shows the run; `cairn handoff` lists what was sent |

## Four versions: Windows, Mac, iPhone, Android

A standing gate for every project, asked for or not: `python platforms.py --repo juw12/<repo> --brain <vault>`
(a folder of the monorepo: `python platforms.py <profile README> --only <name> --brain <vault>`). Exit 1 =
the gate fails, and every gap it names is a run-queue item of this run.

| Version | What counts | How it is usually made |
|---|---|---|
| **Windows** | a download: a file in a GitHub release, or a direct link in the README that answers (`.exe`, `.msi`, an install script, or a file named for windows) | the project's own packager on a `windows-latest` runner |
| **Mac** | the same (`.dmg`, `.pkg`, or a file named for mac) | the same on a `macos-latest` runner; a Mac build cannot be made on Windows |
| **Android** | an `.apk`, in a release or linked from the README | native, or the web app wrapped (Capacitor, Trusted Web Activity) and signed in CI |
| **iPhone** | the live web app on the home screen: it answers, has an `apple-touch-icon` and a manifest with `display: standalone` | manifest, icon and a service worker; no App Store, no `.ipa` |

The gate also fails when the README does not name all four, when a download the README links is not there,
and when a version was left behind (`OLD`: its newest build sits in an older release than the others).

**The gate is that the four are there.** Starting them is not part of it. When the user asks whether a
version really starts, `--run --ledger <vault>/devices/<this computer>/notes/platform-runs.md` starts what
this computer can and writes one line per upload; `--need-run mac,iphone` then makes it part of the gate.

**Cairn shows the same four.** The repo's page in Cairn (`#/projects/<owner>/<repo>`, Look tab, *Versions*;
an app of the monorepo: `.../look/apps/<name>`) reads the releases, the README and the web manifest by the
same rules. After shipping, open it and see that it says what the gate says; a difference is a bug in one of
the two, not a matter of opinion.

**Building them:**

- CI builds every version when the release is made, from the release tag, and marks the release latest only
  when every file the README links is attached. No second step for a person or an agent to remember.
  Workflow changes need `push_as.py check --needs workflow` first.
- The README names all four and says how to get each (iPhone: Safari, Share, *Add to Home Screen*). The
  profile card and the portfolio entry link the downloads.
- Each version does the project's real job. Where the job needs the desktop itself, the phone version is
  the part that travels (view, capture, remote), and the README says what it does not do. A wrapper around
  the landing page does not count, and neither does a feature the project does not have.
- Name release files like the others (`<Name>-Windows-Setup.exe`, `<Name>-macOS.dmg`, `<Name>-android.apk`,
  `SHA256SUMS.txt`) so the gate and people recognise them. An unsigned build says so, with how to open it.
- A project whose job is done by its web app, with no Windows or Mac version: `desktop_shell.py SPEC.json`
  stamps the Jeda desktop shell for it (a native window around the live site, built and opened on Windows
  and two Macs before anything is published). The top of the file lists what the spec names. Say in the
  README what was not checked inside the window.
- The same project without an Android version: `android_shell.py SPEC.json` stamps the Cairn Android shell (a
  full-screen window around the live site, built without Gradle, opened on an emulator before it is
  published). The repository needs the two signing secrets first; the web-app shells share one key, kept in
  the private `juw12/web-shells-signing` with the list of apps signed with it.
- A window around a web page is a version only where the page does the project's job. Not where the page is
  a demo of a program that runs on a PC, and not where the job needs something the window lacks (folder
  access, the microphone on Android): say so and leave that version missing.
- A Mac app made of a script that hands over to Python (or any other program) gets no menu-bar icon on
  macOS 26. The program inside the `.app` has to be the one that runs: Cairn's `mac/launcher.c` loads
  Python into its own process. Check a Mac app on a macOS 26 runner as well as on this Mac.
- Private repos pay for runners: check `cairn vibe github` before adding Mac jobs (GitHub counts a Mac
  minute as ten).
- **No app at all** (a study, a model library, a skills collection): `no_app.txt` is the list, one project
  and its reason per line. It is the user's list. Propose an addition in the final message; never add a
  line to get a project past the gate.

## Findable: a search engine can find it

A standing gate for every project with a public page, asked for or not: `python findable.py --repo juw12/<repo>`
(any other page: `--url <address>`, as often as needed). Exit 1 = the gate fails, and every `GAP` line is a
run-queue item of this run. Run it last, after the pages this run changed are online.

| The gate asks | What counts | Where the fix is |
|---|---|---|
| **Answers** | the site the repo names (its homepage on GitHub) and its landing page answer 200 | the project's Pages setup; a repo with a site but no homepage on GitHub gets one (`push_as.py check --needs settings`) |
| **May be shown** | the page does not say `noindex` | the page's own `<head>`. A page meant to stay out of search (a private tool, a pairing page) is checked with `--private`, and in ReachPilot it is listed under `"not_for_search"` |
| **Says what it is** | a `<title>` of at least 10 characters and a description of at least 25 | the page's own `<head>`: the name plus what the project does, in the words someone would search with who has never heard of it ("Cairn: an open-source second brain in your Git repo", never just "Cairn"). Facts from the repo only |
| **Is listed** | a sitemap that the site's `robots.txt` names holds the page's address | the site's sitemap, never a hand-written list: ReachPilot's daily **Search** task writes `sitemap.xml` for the whole Pages site from every project's pages. `python findable.py` in the ReachPilot folder runs it now |

- **ReachPilot is where it shows and where it keeps running.** Its Search page (Projects > Search) lists every
  project page with what is in the way, whether the sitemap names it, when Bing and Yandex were told
  (IndexNow, no account) and, once the Search Console bridge is connected, whether Google has it. After
  shipping, a new page appears there with the next daily pass; nothing has to be registered.
- **Told, not waited for.** A new or changed page is sent through IndexNow by that task. Google has no door
  without the owner's sign-in: asking it to index a page (Search Console, *URL inspection*, *Request
  indexing*) is done with a signed-in browser the run can drive, else it is the run's `needs you` with the
  page's address.
- **Never promise a place.** The gate removes the reasons a search engine could not find the page. Whether
  and when it shows the page is its decision; the final message says what was checked, not "it ranks".
- Links from other sites count for more than anything on the page. The listings and list pull requests a
  project already has are ReachPilot's Promote page; this gate opens none.

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

`python push_as.py --selftest`, `python featured.py --selftest`, `python platforms.py --selftest` and
`python findable.py --selftest` (offline).
