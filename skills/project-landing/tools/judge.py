"""Blind judge: scores landing pages against the frozen rubric using GitHub Copilot CLI
(separate model, fresh context, sees only artifact + rubric).

Usage:
  python judge.py score  OUT.json  name=html_path [name=html_path ...]
  python judge.py pair   OUT.json  name  html_A  html_B      (randomised A/B order)
"""
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = (ROOT / "refine" / "rubric.md").read_text(encoding="utf-8")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
COPILOT = shutil.which("copilot")


def render(html_path, out_dir, tag):
    """Full-page desktop shot split into <=3 tiles + a phone hero shot + visible text."""
    url = Path(html_path).resolve().as_uri()
    tiles = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(600)
        page.add_style_tag(content="*{animation:none!important;transition:none!important} .reveal{opacity:1!important;transform:none!important}")
        full = out_dir / f"{tag}_full.png"
        page.screenshot(path=str(full), full_page=True)
        text = page.inner_text("body")
        phone = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        phone.goto(url, wait_until="networkidle")
        phone.wait_for_timeout(400)
        phone_path = out_dir / f"{tag}_phone.png"
        phone.screenshot(path=str(phone_path))
        browser.close()
    img = Image.open(full).convert("RGB")
    img = img.resize((800, int(img.height * 800 / img.width)))
    tile_h = max(1, -(-img.height // 3))
    for i in range(3):
        crop = img.crop((0, i * tile_h, 800, min(img.height, (i + 1) * tile_h)))
        if crop.height < 50:
            continue
        p = out_dir / f"{tag}_d{i}.png"
        crop.save(p)
        tiles.append(p)
    tiles.append(phone_path)
    return tiles, text[:9000]


def ask(prompt, attachments, workdir):
    cmd = [COPILOT, "-p", prompt, "-s", "--allow-all-tools", "--stream", "off",
           "--disable-builtin-mcps", "-C", str(workdir)]
    for a in attachments:
        cmd += ["--attachment", str(a)]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=600)
    return out.stdout + out.stderr


def extract_json(reply):
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return {"raw": reply}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"raw": reply}


def score(out_file, targets):
    results = {}
    for name, html_path in targets:
        work = Path(tempfile.mkdtemp(prefix="judge_"))
        tiles, text = render(html_path, work, "page")
        prompt = (
            "You are a strict reviewer. You did not write this. Judge ONE product landing page.\n"
            "Attached: desktop full-page screenshot split top->bottom into tiles, then a phone screenshot.\n"
            "Score each soft criterion S1..S5 0-10 using the anchors (S4 judge from this page's composition "
            "fitting its product type). Quote specific evidence. Do not round up. List the 3 highest-impact fixes.\n"
            "Reply with ONLY JSON: {\"S1\":n,\"S2\":n,\"S3\":n,\"S4\":n,\"S5\":n,\"evidence\":{...},\"fixes\":[...]}\n\n"
            f"RUBRIC:\n{RUBRIC}\n\nVISIBLE PAGE TEXT:\n{text}"
        )
        reply = ask(prompt, tiles, work)
        res = extract_json(reply)
        if all(k in res for k in ("S1", "S2", "S3", "S4", "S5")):
            res["weighted"] = round(0.30 * res["S1"] + 0.25 * res["S2"] + 0.20 * res["S3"]
                                    + 0.15 * res["S4"] + 0.10 * res["S5"], 2)
        results[name] = res
        print(name, res.get("weighted"), flush=True)
        shutil.rmtree(work, ignore_errors=True)
    Path(out_file).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


def pair(out_file, name, html_a, html_b):
    work = Path(tempfile.mkdtemp(prefix="pair_"))
    order = [("X", html_a), ("Y", html_b)]
    swapped = random.random() < 0.5
    if swapped:
        order = [("X", html_b), ("Y", html_a)]
    attachments = []
    texts = {}
    for label, path in order:
        tiles, text = render(path, work, label)
        attachments += tiles
        texts[label] = text[:4000]
    prompt = (
        "You are a strict reviewer. Two versions (X then Y) of the same product landing page are attached "
        "(each: 3 desktop tiles top->bottom, then a phone shot; X's 4 images first, then Y's 4). "
        "Using the rubric, which version is better overall? Reply ONLY JSON: {\"winner\":\"X\"|\"Y\",\"why\":\"...\"}\n\n"
        f"RUBRIC:\n{RUBRIC}\n\nX TEXT:\n{texts['X']}\n\nY TEXT:\n{texts['Y']}"
    )
    res = extract_json(ask(prompt, attachments, work))
    winner = res.get("winner")
    if winner in ("X", "Y"):
        b_label = "X" if swapped else "Y"
        res["candidate_B_won"] = winner == b_label
    res["swapped"] = swapped
    Path(out_file).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(name, res.get("candidate_B_won"), res.get("why", "")[:200])
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "score":
        score(out, [a.split("=", 1) for a in sys.argv[3:]])
    else:
        pair(out, sys.argv[3], sys.argv[4], sys.argv[5])
