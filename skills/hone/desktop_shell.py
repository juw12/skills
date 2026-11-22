"""Stamp the Jeda desktop shell (a native window around a live site, for Windows and Mac) for another app.

    python desktop_shell.py SPEC.json                    # the shell comes from a fresh copy of juw12/jeda
    python desktop_shell.py SPEC.json --template PATH    # ... or from a checkout of it

For a project whose job is done by its web app and that has no Windows or Mac version yet. The shell's files
are copied from Jeda (desktop/ and .github/workflows/apps.yml) and every "Jeda" in them becomes the new app.
What comes out, inside the target repo:

    <folder>/desktop/           the program, its build recipe, installer script, smoke test, icon, README
    .github/workflows/<file>    builds on Windows + two Macs, opens each build and checks its window,
                                publishes what passed to one release tag (not marked latest)

Then: add the downloads to the project's README (all four versions named), open a pull request, and let the
workflow's three builds pass before merging. Before pushing, open the shell from source against a local copy
of the site to see that `started` is true:  <SLUG>_WINDOW_TEST=report.json <SLUG>_DESKTOP_URL=http://127.0.0.1:PORT/
python desktop/<slug>_app.py  (needs pywebview).

Spec keys:
    name          "Bilas"                       file names, Start menu, the .app; no spaces
    title         optional: the window's title, when it differs from name ("光耀同行 Guang Yao Together")
    display       optional: the name people know, for the release notes, when it differs from name
    slug          "bilas"                       lower case, for folders and identifiers
    tagline       "A quiet coin laundry"        one line, for the installer and the release notes
    url           "https://juw12.github.io/bilas/"
    repo          "juw12/bilas"
    target        path of the target repo's checkout
    folder        "" or "apps/sync"             where desktop/ goes inside the repo
    site          "" or "apps/sync/web"         the folder GitHub Pages serves (for the local-site smoke test)
    icon          path of a square PNG, 512 px or more
    title_has     "Bilas"                       text the page title must contain
    started       JS expression, true once the app's own script has drawn the app (not static HTML)
    started_says  what that expression looks for, in words
    keeps         "your laundry progress"       what the window keeps between starts, in words
    light, dark   window background colours before the page loads
    tag           "desktop", or "<folder name>-desktop" in a repo of many apps (the gate gives a folder the
                  tags that start with its name)
    workflow      "desktop.yml" or "sync-desktop.yml"
    android_note  the Download and How-to cells of the Android row in the release notes

A name another app already uses for its folders (Sync) gets a different `name` (SyncLive) and keeps its own
`title` and `display`. Say in the README what was not checked inside the window (sign-in windows, music
services, a microphone): the workflow checks that the page loads, the app starts and it can store data.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE = Path(".")  # set in main()
JEDA_TAGLINE_UPPER = "A quiet space for every faith in Indonesia"
JEDA_TAGLINE_LOWER = "a quiet space for every faith in Indonesia"
JEDA_KEEPS = "your space, notes and settings"
JEDA_STARTED = "!!(document.getElementById('topbar') && document.getElementById('topbar').children.length)"
JEDA_STARTED_SAYS = "the top bar the app draws when it starts"


READ_PAGE = '''def read_page(window, script):
    """The page's answer to `script`.

    A page that forbids eval (Content-Security-Policy: script-src 'self') refuses pywebview's own
    evaluate_js on a Mac, which wraps the script in eval. There the question is put to WebKit itself,
    which the page's policy does not bind.
    """
    try:
        return window.evaluate_js(script)
    except Exception:
        if sys.platform != "darwin":
            raise
    from PyObjCTools import AppHelper
    from webview.platforms.cocoa import BrowserView

    answer, done = {}, threading.Event()

    def ask():
        def finished(result, error):
            answer["value"] = result
            answer["error"] = None if error is None else str(error)
            done.set()

        BrowserView.instances[window.uid].webview.evaluateJavaScript_completionHandler_(script, finished)

    AppHelper.callAfter(ask)
    if not done.wait(20):
        raise RuntimeError("the page did not answer")
    if answer["error"]:
        raise RuntimeError(answer["error"])
    return answer["value"]


'''

def rename(text: str, spec: dict) -> str:
    """Every Jeda becomes the new app. The longer, exact strings go first."""
    lower_tagline = spec["tagline"][0].lower() + spec["tagline"][1:]
    swaps = [
        ("https://juw12.github.io/jeda/", spec["url"]),
        ("https://github.com/juw12/jeda", "https://github.com/" + spec["repo"]),
        ("github.com/juw12/jeda", "github.com/" + spec["repo"]),
        ("juw12/jeda", spec["repo"]),
        (JEDA_TAGLINE_UPPER, spec["tagline"]),
        (JEDA_TAGLINE_LOWER, lower_tagline),
        (JEDA_KEEPS, spec["keeps"]),
        (JEDA_STARTED, spec["started"]),
        (JEDA_STARTED_SAYS, spec["started_says"]),
        ('LIGHT_BACKGROUND = "#f6f2eb"', 'LIGHT_BACKGROUND = "%s"' % spec["light"]),
        ('DARK_BACKGROUND = "#14110f"', 'DARK_BACKGROUND = "%s"' % spec["dark"]),
        ("io.github.juw12.jeda.desktop", "io.github.juw12.%s.desktop" % spec["slug"].replace("-", "")),
        ('if "Jeda" not in str(result.get("title")', 'if %s not in str(result.get("title")' % json.dumps(spec["title_has"])),
    ]
    for old, new in swaps:
        text = text.replace(old, new)
    text = text.replace('aria-hidden="true">J</div>', 'aria-hidden="true">%s</div>' % spec["name"][0])  # offline.html's mark
    text = text.replace("JEDA", spec["slug"].upper().replace("-", "_"))
    text = text.replace("Jeda", spec["name"])
    text = text.replace("jeda", spec["slug"])
    return text


def stamp(spec: dict) -> list[str]:
    target = Path(spec["target"])
    folder = target / spec["folder"] if spec["folder"] else target
    desktop = folder / "desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    made = []
    for source in sorted((TEMPLATE / "desktop").iterdir()):
        if source.name in ("icon-512.png", "dist", "build", "__pycache__") or source.is_dir():
            continue
        name = source.name.replace("jeda", spec["slug"])
        text = rename(source.read_text(encoding="utf-8"), spec)
        if source.name == "jeda_app.py" and "def read_page(" not in text:
            # until Jeda's own shell has it: the self-test can read a page that forbids eval
            asked = "window.evaluate_js(PAGE_SCRIPT)"
            assert asked in text and "\ndef main(" in text
            text = text.replace(asked, "read_page(window, PAGE_SCRIPT)").replace("\ndef main(", "\n" + READ_PAGE + "def main(", 1)
        (desktop / name).write_text(text, encoding="utf-8", newline="\n")
        made.append(str((desktop / name).relative_to(target)))
    if spec.get("title"):
        # the window's title can be the app's real name where the file name could not (spaces, other scripts)
        program = desktop / (spec["slug"] + "_app.py")
        code = program.read_text(encoding="utf-8")
        old_title = 'TITLE = "%s"' % spec["name"]
        assert old_title in code
        program.write_text(code.replace(old_title, "TITLE = %s" % json.dumps(spec["title"], ensure_ascii=False)), encoding="utf-8", newline="\n")
    shutil.copyfile(spec["icon"], desktop / "icon-512.png")
    made.append(str((desktop / "icon-512.png").relative_to(target)))
    (desktop / "shell.json").write_text('{\n  "version": "1.0.0"\n}\n', encoding="utf-8")

    prefix = (spec["folder"] + "/") if spec["folder"] else ""
    site = spec.get("site", "")
    if prefix or site:
        # the site is not the repository's top folder: tell the smoke test where it is
        smoke = desktop / "smoke_test.py"
        text = smoke.read_text(encoding="utf-8")
        depth = len(Path(prefix + "desktop").parts)
        top = "DESKTOP" + "".join(", os.pardir" for _ in range(depth))
        old = "REPO = os.path.dirname(DESKTOP)\n"
        assert old in text
        new = "REPO = os.path.normpath(os.path.join(%s%s))  # the folder GitHub Pages serves\n" % (
            top, "".join(", %s" % json.dumps(part) for part in Path(site).parts))
        smoke.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    workflow = rename((TEMPLATE / ".github" / "workflows" / "apps.yml").read_text(encoding="utf-8"), spec)
    if prefix:
        workflow = workflow.replace("'desktop/**'", "'%sdesktop/**'" % prefix)
        workflow = re.sub(r"(?<![\w/.-])desktop/(build\.py|smoke_test\.py|dist|shell\.json)", prefix + r"desktop/\1", workflow)
        workflow = workflow.replace("APP=desktop/dist/", "APP=%sdesktop/dist/" % prefix)
    workflow = workflow.replace("workflows/apps.yml", "workflows/" + spec["workflow"])
    workflow = workflow.replace("group: apps-${{ github.ref }}", "group: %s-${{ github.ref }}" % spec["workflow"].removesuffix(".yml"))
    if spec["tag"] != "apps":
        workflow = workflow.replace("releases/download/apps/", "releases/download/%s/" % spec["tag"])
        workflow = workflow.replace('the "apps" release', 'the "%s" release' % spec["tag"])
        workflow = re.sub(r"gh release (view|upload|edit|create) apps ", r"gh release \1 %s " % spec["tag"], workflow)
        workflow = workflow.replace('--notes-file notes.md --repo "$REPO"\n          fi', '--notes-file notes.md --latest=false --repo "$REPO"\n          fi')
    # the Android row and the header comment said what was true of Jeda on the day the shell was written
    workflow = re.sub(r"\n# iPhone and Android use the site itself[^\n]*\n", "\n", workflow)
    workflow = re.sub(r"          \| \*\*Android\*\* \|[^\n]*\n", "          | **Android** | %s |\n" % spec["android_note"], workflow)
    if spec.get("display"):
        # where people read the app's name (not a file's name), say the name they know
        for old_text, new_text in (
            ("**%s**:" % spec["name"], "**%s**:" % spec["display"]),
            ("the same %s as" % spec["name"], "the same %s as" % spec["display"]),
            ('--title "%s for Windows and Mac"' % spec["name"], '--title "%s for Windows and Mac"' % spec["display"]),
        ):
            assert old_text in workflow, old_text
            workflow = workflow.replace(old_text, new_text)
    flow_file = target / ".github" / "workflows" / spec["workflow"]
    flow_file.parent.mkdir(parents=True, exist_ok=True)
    flow_file.write_text(workflow, encoding="utf-8", newline="\n")
    made.append(str(flow_file.relative_to(target)))

    leftovers = []
    for path in [*desktop.iterdir(), flow_file]:
        if path.suffix == ".png":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"jeda|faith|Indonesia", line, re.I) and "jeda" not in spec["slug"]:
                leftovers.append("%s:%d: %s" % (path.name, number, line.strip()[:120]))
    if leftovers:
        print("STILL NAMES JEDA:", *leftovers, sep="\n  ")
    return made


def main() -> int:
    global TEMPLATE
    parser = argparse.ArgumentParser(description="Stamp the Jeda desktop shell for another app")
    parser.add_argument("spec", help="SPEC.json (see the top of this file)")
    parser.add_argument("--template", default="", help="a checkout of juw12/jeda (default: a fresh copy)")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as folder:
        if args.template:
            TEMPLATE = Path(args.template)
        else:
            TEMPLATE = Path(folder) / "jeda"
            subprocess.run(["git", "clone", "--quiet", "--depth", "1", "https://github.com/juw12/jeda.git", str(TEMPLATE)], check=True)
        if not (TEMPLATE / "desktop" / "jeda_app.py").is_file():
            raise SystemExit("%s is not a checkout of juw12/jeda (no desktop/jeda_app.py)" % TEMPLATE)
        for path in stamp(spec):
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
