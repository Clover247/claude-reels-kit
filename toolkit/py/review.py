"""Self-review contact sheet: frames at every text / non-cut transition (+ extra frames) of a rendered reel, labelled.
Read the resulting jpg and check: text positions (captions/plates at the bottom, above IG UI), overlaps, black edges on
transitions, B-roll covering transitions, captions under big titles, end card.
Usage: python review.py <project_dir> <video> <out.jpg> [extra frame numbers...]
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, TOOLKIT, ui_font

P = project()
tl = json.load(open(f"{P.pub}/timeline.json", encoding="utf-8"))
fps = tl["fps"]
vid, out = sys.argv[2], sys.argv[3]
pts = []
for t in tl["texts"]:
    pts.append((t["frm"] + min(28, t["dur"] // 2), f"{t['kind']}"))
for tr in tl["transitions"]:
    if tr["kind"] != "cut":
        pts.append((tr["at"] - 3, f"{tr['kind']}-out"))
        pts.append((tr["at"] + 2, f"{tr['kind']}-in"))
pts += [(int(x), "extra") for x in sys.argv[4:]]
pts = sorted(set(pts))
tmp = P.path("stills", "rv", "x")[:-2]
ims = []
font = ImageFont.truetype(ui_font(), 20)
for f, lab in pts:
    p = f"{tmp}/{f}.jpg"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{f/fps+0.001:.3f}", "-i", vid, "-frames:v", "1", "-vf", "scale=216:384", p], check=True)
    im = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 216, 26], fill=(0, 0, 0)); d.text((4, 2), f"{f} {f/fps:.1f}s {lab}", fill=(255, 230, 0), font=font)
    ims.append(im)
cols = 8
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (216 * cols, 384 * rows))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 216, (i // cols) * 384))
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
sheet.save(out, quality=88)
print(len(ims), "frames ->", out)
