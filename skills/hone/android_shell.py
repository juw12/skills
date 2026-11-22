"""Stamp the Android shell (a full-screen window around a live web app) for another app.

    python android_shell.py SPEC.json                    # the shell comes from a fresh copy of juw12/cairn
    python android_shell.py SPEC.json --template PATH    # ... or from a checkout of it

For a project whose job is done by its web app and that has no Android version yet. The shell's files are
copied from Cairn (android/ and .github/workflows/android.yml) and every "Cairn" in them becomes the new app.
What comes out, inside the target repo:

    <folder>/android/           the program (one Java file), manifest, icon, build.py (no Gradle), smoke.py
    .github/workflows/<file>    builds and signs the .apk, opens it on an Android 14 emulator, publishes it
                                to one release tag (not marked latest)

The repository needs two secrets before the workflow can sign: ANDROID_KEYSTORE_B64 and
ANDROID_KEYSTORE_PASSWORD (the key's backup is a private repository; see `signing` below).

Spec keys:
    name          "Bilas"                       the file's name (<name>-android.apk); no spaces
    display       optional: the name under the icon and in the notes, when it differs from name
    id            "io.github.juw12.bilas"       the Android package id; never changes once published
    url           "https://juw12.github.io/bilas/"   the page the app opens
    scope         optional: "juw12.github.io/bilas"  links outside it open in the browser (default: from url)
    repo          "juw12/bilas"
    target        path of the target repo's checkout
    folder        "" or "apps/sync"             where android/ goes inside the repo
    icon          path of a square PNG, 192 px or more
    background    "#151d20"                     window, status bar and navigation bar colour
    accent        "#d9481f"                     the offline page's mark and button
    tag           "android", or "<folder name>-android" in a repo of many apps
    workflow      "android.yml" or "sync-android.yml"
    alias         the key's alias in the keystore ("shells")
    cert          SHA-256 of the signing certificate, lower case hex without colons
    signing       the private repository that keeps the key ("juw12/web-shells-signing")
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE_ID = "io.github.juw12.cairn"
TEMPLATE_URL = "https://juw12.github.io/cairn/"
TEMPLATE_SCOPE = "juw12.github.io/cairn"


SMOKE_RETRY = r'''def killed_with_play_services(folder):
    """True when Android ended the app because Google Play services restarted under it.

    A freshly started emulator updates Play services in its first minutes. The WebView holds Play
    services' font provider, so Android ends every app that does when Play services goes down. That
    says nothing about the app, and the next start stays up.
    """
    try:
        with open(os.path.join(folder, "android-logcat.txt"), encoding="utf-8") as handle:
            log = handle.read()
    except OSError:
        return False
    with open(os.path.join(HERE, "app.json"), encoding="utf-8") as handle:
        package = json.load(handle)["id"]
    return any("Killing" in line and package in line and "com.google.android.gms" in line for line in log.splitlines())


if __name__ == "__main__":
    for attempt in (1, 2, 3):
        try:
            main()
            break
        except SystemExit as stopped:
            folder = os.path.dirname(os.path.abspath(sys.argv[1]))
            if not stopped.code or attempt == 3 or not killed_with_play_services(folder):
                raise
            print("\nAndroid ended the app because Google Play services restarted on this new emulator. "
                  "Trying again (%d of 3).\n" % (attempt + 1), flush=True)
            time.sleep(20)
'''


def rename(text: str, spec: dict) -> str:
    display = spec.get("display") or spec["name"]
    text = text.replace(TEMPLATE_URL, spec["url"])
    text = text.replace('SCOPE = "%s"' % TEMPLATE_SCOPE, 'SCOPE = "%s"' % spec["scope"])
    text = text.replace(TEMPLATE_ID, spec["id"])
    text = text.replace('android:label="Cairn"', 'android:label=%s' % json.dumps(display, ensure_ascii=False).replace("&", "&amp;"))
    text = text.replace("#1b1a17", spec["background"]).replace("#d9481f", spec["accent"])
    text = text.replace('aria-hidden="true">C</div>', 'aria-hidden="true">%s</div>' % display[0])
    text = text.replace("<title>Cairn</title>", "<title>%s</title>" % display)
    text = text.replace("Cairn can't reach", "%s can't reach" % display).replace("Cairn needs a connection", "%s needs a connection" % display)
    return text.replace("Cairn", spec["name"]).replace("cairn", spec["name"].lower())


def is_light(colour: str) -> bool:
    red, green, blue = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * red + 0.587 * green + 0.114 * blue > 150


def readme(spec: dict, prefix: str) -> str:
    display = spec.get("display") or spec["name"]
    apk = "%s-android.apk" % spec["name"]
    link = "https://github.com/%s/releases/download/%s/%s" % (spec["repo"], spec["tag"], apk)
    return f"""# {display} for Android

One full-screen window (Android's own WebView) around the web app ({spec["url"]}): the same {display} a phone
opens in its browser, with its own icon and no address bar. `MainActivity.java` adds what a plain WebView lacks:
Share, saving a file to Downloads, picking a file, and links to other sites opening in the browser. Because it
loads the live web app, every change to the site reaches the installed app on its next start; only a change to
this folder needs a new .apk.

Get it: [`{apk}`]({link}). Open the file on the phone and allow "install unknown apps" for your browser once.

| File | What it is |
| --- | --- |
| `app.json` | name, package id, version (raise `versionCode` and `versionName` when this folder changes), and the SHA-256 of the signing certificate |
| `AndroidManifest.xml`, `res/`, `assets/offline.html` | the app's manifest, icon and colours, the page shown when the first start has no connection |
| `src/.../MainActivity.java` | the whole program (the shell Jeda, Teduh, EarlyStar and Cairn use) |
| `build.py` | builds and signs the .apk without Gradle: aapt2, javac, d8, zipalign, apksigner |
| `smoke.py` | installs the .apk on an emulator, opens it and checks it stays up |

```
JAVA_HOME=<JDK 17> ANDROID_BUILD_TOOLS=<build-tools 34> ANDROID_JAR=<platform 34>/android.jar \\
  python {prefix}android/build.py --keystore release.p12 --password-file release-password.txt --alias {spec["alias"]}
```

`.github/workflows/{spec["workflow"]}` does this on GitHub: it signs with the key in the repository's secrets,
checks the certificate is the one named in `app.json`, opens the app on an Android 14 emulator, and puts
`{apk}` on the `{spec["tag"]}` release. The file there is replaced only when `versionName` in `app.json` is a
new one.

The signing key is not in this repository (its backup is the private `{spec["signing"]}`). Without `--keystore`
the build signs with a throwaway key, which is enough to try the app on your own phone.

Not checked: a real phone, and anything in the page that needs the camera, the microphone or a sign-in window
of another site. The emulator check cannot read the page inside a release build; it checks that the app
installs, opens its own window, stays up and does not crash, and keeps a screenshot.
"""


def stamp(spec: dict, template: Path) -> list[str]:
    spec.setdefault("scope", re.sub(r"^https?://", "", spec["url"]).split("?")[0].rsplit("/", 1)[0].rstrip("/"))
    display = spec.get("display") or spec["name"]
    target = Path(spec["target"])
    prefix = (spec["folder"].rstrip("/") + "/") if spec.get("folder") else ""
    android = target / prefix / "android" if prefix else target / "android"
    if android.exists():
        raise SystemExit("%s is already there" % android)
    source = template / "android"
    made = []
    for path in sorted(source.rglob("*")):
        if path.is_dir() or path.name in ("README.md", "ic_launcher.png", "app.json") or {"build", "dist", "__pycache__"} & set(path.parts):
            continue
        relative = Path(str(path.relative_to(source)).replace("io/github/juw12/cairn", spec["id"].replace(".", "/")))
        out = android / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        content = rename(path.read_text(encoding="utf-8"), spec)
        if path.name == "smoke.py" and "killed_with_play_services" not in content:
            # until Cairn's own smoke.py has it: try again when the emulator's Play services ended the app
            tail = 'if __name__ == "__main__":\n    main()\n'
            assert content.endswith(tail)
            content = content[:-len(tail)] + SMOKE_RETRY
        out.write_text(content, encoding="utf-8", newline="\n")
        made.append(str(out.relative_to(target)))
    if is_light(spec["background"]):
        # dark clock and icons on a light status bar, or they cannot be seen
        styles = android / "res" / "values" / "styles.xml"
        marked = styles.read_text(encoding="utf-8").replace(
            "    </style>",
            '        <item name="android:windowLightStatusBar">true</item>\n'
            '        <item name="android:windowLightNavigationBar">true</item>\n    </style>',
        )
        styles.write_text(marked, encoding="utf-8", newline="\n")
    icon = android / "res" / "mipmap-xxxhdpi" / "ic_launcher.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(spec["icon"], icon)
    try:  # Pillow where it is installed (any system), macOS's own sips otherwise
        from PIL import Image

        Image.open(icon).convert("RGBA").resize((192, 192), Image.LANCZOS).save(icon)
    except ImportError:
        subprocess.run(["sips", "-z", "192", "192", str(icon)], check=True, capture_output=True)
    (android / "app.json").write_text(json.dumps({
        "name": spec["name"], "id": spec["id"], "url": spec["url"], "versionName": "1.0.0", "versionCode": 1,
        "minSdk": 24, "targetSdk": 34, "certSha256": spec["cert"],
    }, indent=2) + "\n", encoding="utf-8")
    (android / "README.md").write_text(readme(spec, prefix), encoding="utf-8", newline="\n")
    made += [str(p.relative_to(target)) for p in (icon, android / "app.json", android / "README.md")]

    flow = (template / ".github" / "workflows" / "android.yml").read_text(encoding="utf-8")
    start = flow.index('            printf \'%s\\n\' "Downloads of Cairn')
    end = flow.index("            gh release create apps ")
    apk = "%s-android.apk" % spec["name"]
    notes = (
        "            printf '%%s\\n' \"%s for Android: a full-screen window around the web app (%s).\" \"\" \\\n"
        "              \"Download [%s](https://github.com/$GITHUB_REPOSITORY/releases/download/%s/%s), open the file on the phone and allow \\\"install unknown apps\\\" for your browser once.\" \\\n"
        "              \"It is not from a store: Android asks before it installs.\" > notes.md\n"
    ) % (display, spec["url"], apk, spec["tag"], apk)
    flow = flow[:start] + notes + flow[end:]
    flow = flow.replace("name: Android app", "name: %s Android app" % spec["name"], 1)
    flow = flow.replace('--title "Cairn apps"', '--title "%s for Android"' % display)
    flow = flow.replace("--alias cairn", "--alias %s" % spec["alias"])
    flow = flow.replace("cairn-android", "%s-android" % spec["slug"])
    flow = flow.replace("Cairn", spec["name"])
    flow = re.sub(r"gh release (view|create|download|upload) apps ", r"gh release \1 %s " % spec["tag"], flow)
    flow = flow.replace("the apps release", "the %s release" % spec["tag"]).replace("The apps release", "The %s release" % spec["tag"])
    flow = flow.replace("Made the apps release", "Made the %s release" % spec["tag"])
    flow = flow.replace("workflows/android.yml", "workflows/" + spec["workflow"])
    if prefix:
        flow = re.sub(r"(?<![\w/.-])android/", prefix + "android/", flow)
    flow_file = target / ".github" / "workflows" / spec["workflow"]
    if flow_file.exists():
        raise SystemExit("%s is already there" % flow_file)
    flow_file.parent.mkdir(parents=True, exist_ok=True)
    flow_file.write_text(flow, encoding="utf-8", newline="\n")
    made.append(str(flow_file.relative_to(target)))

    leftovers = []
    for path in [*android.rglob("*"), flow_file]:
        if path.is_file() and path.suffix != ".png":
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"cairn|\bapps release\b", line, re.I) and "cairn" not in spec["name"].lower() and "Cairn use" not in line:
                    leftovers.append("%s:%d: %s" % (path.name, number, line.strip()[:120]))
    if leftovers:
        print("STILL NAMES CAIRN:", *leftovers, sep="\n  ")
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp the Android shell for another app")
    parser.add_argument("spec", help="SPEC.json (see the top of this file)")
    parser.add_argument("--template", default="", help="a checkout of juw12/cairn (default: a fresh copy)")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as folder:
        template = Path(args.template) if args.template else Path(folder) / "cairn"
        if not args.template:
            subprocess.run(["git", "clone", "--quiet", "--depth", "1", "https://github.com/juw12/cairn.git", str(template)], check=True)
        if not (template / "android" / "build.py").is_file():
            raise SystemExit("%s is not a checkout of juw12/cairn (no android/build.py)" % template)
        for path in stamp(spec, template):
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
