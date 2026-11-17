"""Quick visual QA for anim projects: low-res render + labelled contact sheet of chosen frames.
  python anim_qa.py <project_dir> [frame frame ...]    (no frames = one per voice line + 2 inside each line + end card)
Writes <project>/stills/qa.mp4 (quarter res, silent) and stills/qa_sheet.jpg."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, REEL, ui_font
from PIL import Image, ImageDraw, ImageFont
P = project()
npx = "npx.cmd" if os.name == "nt" else "npx"
data = json.loads(open(REEL / "src" / "projects" / f"{P.id}.data.ts", encoding="utf-8").read().split("export const DATA = ", 1)[1].rsplit(" as const", 1)[0])
os.makedirs(f"{P.W}/stills", exist_ok=True)
mp4 = f"{P.W}/stills/qa.mp4"
subprocess.run([npx, "remotion", "render", "src/index.ts", P.id, mp4, f"--public-dir={P.pub}", "--scale=0.4", "--muted", "--concurrency=8", "--log=error"], cwd=REEL, check=True)
frames = [int(x) for x in sys.argv[2:]]
if not frames:
    for L in data["lines"]:
        a, b = L["f0"], L["f1"]
        frames += [a + 6, (a + b) // 2, b - 4]
    frames += [data["endF0"] + 40]
frames = sorted(set(frames))
font = ImageFont.truetype(ui_font(), 22)
tiles = []
for fr in frames:
    out = f"{P.W}/stills/_qa_{fr}.png"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{fr / data['fps'] + 0.001:.3f}", "-i", mp4, "-frames:v", "1", out], check=True)
    im = Image.open(out).convert("RGB"); os.remove(out)
    lid = max((L for L in data["lines"] if L["f0"] <= fr), key=lambda L: L["f0"], default={"id": "-"})["id"]
    d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width, 28], fill=(0, 0, 0)); d.text((6, 2), f"{fr} {fr / 30:.1f}s {lid}", fill=(255, 220, 0), font=font)
    tiles.append(im)
cols = 9
w, h = tiles[0].size
sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), "black")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * w, (i // cols) * h))
sheet.save(f"{P.W}/stills/qa_sheet.jpg", quality=85)
print(f"{len(tiles)} frames -> {P.W}/stills/qa_sheet.jpg ({sheet.size[0]}x{sheet.size[1]})")
