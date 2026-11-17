"""<project>/public/timeline.json  ->  toolkit/reel/src/projects/<id>.tsx  (flat, Studio-editable JSX) + src/Root.tsx
Also prepares per-clip voice files (cleaned, loudness-matched) in public/voice/, brand fonts in public/fonts/,
and the cover background public/cover_bg.jpg.
Usage: python gen_tsx.py <project_dir>      (run after build.py and music.py)
NOTE: once you edit the composition in Remotion Studio, the .tsx is the source of truth — re-running this overwrites it.
"""
import json, os, re, shutil, sys, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, ROOT, REEL

P = project()
FIX = getattr(P.edl(), "FIX", {})
W, PUB = P.W, P.pub
tl = json.load(open(f"{PUB}/timeline.json", encoding="utf-8"))
FPS = tl["fps"]
LABEL = P.cfg.get("labels", {})
BRAND_P = ROOT / P.cfg["brand"]
brand = json.load(open(BRAND_P, encoding="utf-8"))
NL = chr(10)
COMP = "".join(x.capitalize() for x in re.split(r"[^A-Za-z0-9]+", P.id) if x)   # clinic-tour-2026 -> ClinicTour2026


def js(s):
    return json.dumps(s, ensure_ascii=False)


def words(clip):
    return P.words(clip)


# ── brand fonts -> public/fonts (brands/<b>/fonts first, then toolkit/fonts) ──
os.makedirs(f"{PUB}/fonts", exist_ok=True)
for f in (brand["fonts"]["sans"]["file"], brand["fonts"]["script"]["file"]):
    if not os.path.exists(f"{PUB}/fonts/{f}"):
        src = next((p for p in (BRAND_P.parent / "fonts" / f, ROOT / "toolkit" / "fonts" / f) if p.exists()), None)
        if not src:
            sys.exit(f"font {f} not found in {BRAND_P.parent / 'fonts'} or toolkit/fonts")
        shutil.copy(src, f"{PUB}/fonts/{f}")

# ── cover background: graded mezz frame ──
# cover.clip must be a clip used in the edit (only those have mezz files); empty -> first spoken shot, 1 s in.
# Re-extracted whenever project.json "cover" clip/at changes (stamp file).
cov = dict(P.cfg.get("cover") or {})
used_mezz = {os.path.splitext(f)[0] for f in os.listdir(f"{PUB}/mezz")}
if cov.get("clip") not in used_mezz:
    first = next(m for m in tl["main"] if not m.get("hook"))
    if cov.get("clip"):
        print(f"!! cover clip {cov['clip']} is not used in the edit -> using {first['clip']}")
    cov["clip"], cov["at"] = first["clip"], round(first["src"] / FPS + 1.0, 2)
stamp = f"{cov['clip']}@{cov.get('at', 1.0)}"
st_p = f"{PUB}/cover_bg.stamp"
old = open(st_p).read() if os.path.exists(st_p) else None
if not os.path.exists(f"{PUB}/cover_bg.jpg") or (old is not None and old != stamp):
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(cov.get("at", 1.0)), "-i", f"{PUB}/mezz/{cov['clip']}.mp4", "-frames:v", "1",
                    "-q:v", "2", f"{PUB}/cover_bg.jpg"], check=True)
open(st_p, "w").write(stamp)

# ── voice files: cleaned + loudness-matched per clip ──
os.makedirs(f"{PUB}/voice", exist_ok=True)
speech = sorted({m["clip"] for m in tl["main"] if not m.get("hook")})
for c in speech:
    out = f"{PUB}/voice/{c}.wav"
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(f"{W}/clean/{c}.wav"):
        subprocess.run([FF, "-v", "error", "-y", "-i", f"{W}/clean/{c}.wav", "-af", "loudnorm=I=-16:TP=-2:LRA=7", "-ar", "48000", out], check=True)

kin = [(t["frm"], t["frm"] + t["dur"]) for t in tl["texts"] if t["kind"] == "kinetic"]
trans_at = {t["at"]: t["kind"] for t in tl["transitions"]}

DROPPED = []

def captions_for(m):
    """Words heard in this shot. Ownership by whisper START (unique per word):
    first piece of an EDL range owns words from a-0.6 s (whisper starts run early), later pieces from the previous
    piece's end. Intent filter = the EDL range itself: a word starting in its last 0.12 s is the next sentence."""
    a, b = m["src"] / FPS, (m["src"] + m["dur"]) / FPS
    mi = tl["main"].index(m)
    prev = tl["main"][mi - 1] if mi else None
    if m.get("piece", 0) > 0 and prev and prev["clip"] == m["clip"]:
        lo = (prev["src"] + prev["dur"]) / FPS
    else:
        lo = a - 0.6
    ra, rb = m.get("rng", [a, b])
    out = []
    for w in words(m["clip"]):
        if not (lo <= w["s"] < b and w["e"] > a + 0.05 and w["s"] < rb - 0.12 and w["e"] > ra + 0.05):
            continue
        tl_f = m["frm"] + round((max(w["s"], a) - a) * FPS)
        tl_e = m["frm"] + round((min(w["e"], b) - a) * FPS) + 15   # a page stays up to 0.5 s after the word
        if any(ks - 12 <= tl_f < ke for ks, ke in kin):           # starts under / right before a big title
            DROPPED.append(w["w"])
            continue
        clash = [ks for ks, ke in kin if tl_f < ks < tl_e]           # page would linger into a title: end it earlier
        w = dict(w)
        if clash:
            w["e"] = max(w["s"] + 0.05, a + (clash[0] - m["frm"]) / FPS - 0.55)
        t = FIX.get(w["w"], w["w"])
        if not t:
            continue
        if t.startswith("-") and out:
            out[-1]["text"] += t
            out[-1]["endMs"] = round(w["e"] * 1000)
            continue
        out.append(dict(text=(" " if out else "") + t, startMs=round(max(w["s"], a) * 1000), endMs=round(w["e"] * 1000),
                        timestampMs=round((w["s"] + w["e"]) / 2 * 1000), confidence=None))
    return out

def cap_literal(caps, ind):
    if not caps:
        return "[]"
    rows = [f'{ind}  {{text: {js(c["text"])}, startMs: {c["startMs"]}, endMs: {c["endMs"]}, timestampMs: {c["timestampMs"]}, confidence: null}},' for c in caps]
    return "[\n" + "\n".join(rows) + f"\n{ind}]"

L = []
ap = L.append
ap(f'// AUTO-GENERATED by toolkit/py/gen_tsx.py from projects/{P.id}/edl.py — after editing in Studio, this file IS the source of truth.')
ap(f'// Media comes from projects/{P.id}/public (render/studio with --public-dir, see toolkit/py/render.py).')
ap('import React from "react";')
ap('import { AbsoluteFill, Sequence, Track, staticFile } from "remotion";')
ap('import { Audio } from "@remotion/media";')
ap('import { Brand, BrandT, Captions, Card, CoverCard, EndCard, Flash, Kinetic, Shot, Tag, Voice } from "../elements";')
ap('')
ap(f'export const meta = {{ id: {js(P.id)}, durationInFrames: {tl["durationInFrames"]}, fps: {FPS} }};')
ap(f'export const brand: BrandT = {json.dumps({k: brand[k] for k in ("name", "colors", "fonts") if k in brand}, ensure_ascii=False)};')
ap('')
ap(f'export const {COMP}: React.FC = () => {{')
ap('  return (')
ap('    <Brand value={brand}>')
ap('    <AbsoluteFill style={{ backgroundColor: "#000" }}>')

# main shots
mains = [m for m in tl["main"] if not m.get("end")]
ap('      <Track name="Кадри">')
count = {}
for m in tl["main"]:
    if m.get("end"):
        continue
    c = m["clip"]
    lab = "Хук" if m.get("hook") else LABEL.get(c, c)
    count[lab] = count.get(lab, 0) + 1
    tin = trans_at.get(m["frm"], "cut"); tout = trans_at.get(m["frm"] + m["dur"], "cut")
    tin = "cut" if tin == "flash" else tin; tout = "cut" if tout == "flash" else tout
    caps = [] if m.get("hook") else captions_for(m)
    preview = " ".join(x["text"].strip() for x in caps[:4])
    name = f"{lab} {count[lab]:02d}" + (f" · {preview}" if preview else "") + (" · Ч/Б" if m["bw"] else "")
    ap(f'        <Sequence name={js(name)} from={{{m["frm"]}}} durationInFrames={{{m["dur"]}}} trimBefore={{{m["src"]}}}>')
    ap(f'          <Shot name="Відео" src="mezz/{c}.mp4" zoom={{{m["zoom"]}}} bw={{{"true" if m["bw"] else "false"}}} transIn="{tin}" transOut="{tout}" />')
    if not m.get("hook"):
        mi = mains.index(m)
        prv = mains[mi - 1] if mi > 0 else None
        nxt = mains[mi + 1] if mi + 1 < len(mains) else None
        cont_in = prv is not None and prv["clip"] == c and abs(prv["src"] + prv["dur"] - m["src"]) <= 3
        cont_out = nxt is not None and nxt["clip"] == c and abs(m["src"] + m["dur"] - nxt["src"]) <= 3
        # fades: none on seamless joins; 1 frame on cuts placed in a dip between words (don't eat the syllable);
        # 2 in / 4 out where the voice has already decayed (cut sits in room tone)
        fi = 0 if cont_in else 1 if m.get("tight_in") else 2
        fo = 0 if cont_out else 1 if m.get("tight_out") else 4
        ap(f'          <Voice name="Голос" src="voice/{c}.wav" fadeIn={{{fi}}} fadeOut={{{fo}}} gain={{1}} />')
        ap(f'          <Captions name="Субтитри" captions={{{cap_literal(caps, "          ")}}} />')
    ap('        </Sequence>')
end = [m for m in tl["main"] if m.get("end")][0]
ap(f'        <Sequence name="Фінал · фон" from={{{end["frm"]}}} durationInFrames={{{end["dur"]}}} trimBefore={{{end["src"]}}}>')
ap(f'          <Shot name="Відео" src="mezz/{end["clip"]}.mp4" zoom={{1}} bw={{false}} transIn="cut" transOut="cut" />')
ap('        </Sequence>')
ap('      </Track>')

# b-roll
ap('      <Track name="B-roll">')
for b in tl["broll"]:
    ap(f'        <Sequence name={js("B-roll · " + b["clip"])} from={{{b["frm"]}}} durationInFrames={{{b["dur"]}}} trimBefore={{{b["src"]}}}>')
    ap(f'          <Shot name="Відео" src="mezz/{b["clip"]}.mp4" zoom={{1.04}} bw={{false}} transIn="pop" transOut="pop" />')
    ap('        </Sequence>')
ap('      </Track>')

def tracks(items):
    """greedy split into non-overlapping rows"""
    rows = []
    for it in sorted(items, key=lambda x: x["frm"]):
        for r in rows:
            if r[-1]["frm"] + r[-1]["dur"] <= it["frm"]:
                r.append(it); break
        else:
            rows.append([it])
    return rows

hook_end = max((m["frm"] + m["dur"] for m in tl["main"] if m.get("hook") and not m.get("end")), default=0)
for i, row in enumerate(tracks([t for t in tl["texts"] if t["kind"] == "kinetic"])):
    ap(f'      <Track name="Великі титри{"" if i == 0 else f" {i+1}"}">')
    for t in row:
        bold = next((l["text"] for l in t["lines"] if l["style"] == "bold"), "")
        sc = next((l for l in t["lines"] if l["style"] == "script"), None)
        ap(f'        <Kinetic name={js("Титр · " + (bold or sc["text"]))} from={{{t["frm"]}}} durationInFrames={{{t["dur"]}}} bold={js(bold)} script={js(sc["text"] if sc else "")} scriptDelay={{{sc["delay"] if sc else 0}}} centered={{{"true" if t["frm"] < hook_end else "false"}}} />')
    ap('      </Track>')

pl = [t for t in tl["texts"] if t["kind"] in ("lower3", "pin", "tag", "section")]
for i, row in enumerate(tracks(pl)):
    ap(f'      <Track name="Плашки{"" if i == 0 else f" {i+1}"}">')
    for t in row:
        if t["kind"] in ("lower3", "pin"):
            ap(f'        <Card name={js(("Адреса · " if t["kind"] == "pin" else "Ім\'я · ") + t["title"])} from={{{t["frm"]}}} durationInFrames={{{t["dur"]}}} title={js(t["title"])} sub={js(t["sub"])} pin={{{"true" if t["kind"] == "pin" else "false"}}} />')
        else:
            var = "section" if t["kind"] == "section" else t.get("pos", "left")
            ap(f'        <Tag name={js("// " + t["text"])} from={{{t["frm"]}}} durationInFrames={{{t["dur"]}}} text={js(t["text"])} variant="{var}" />')
    ap('      </Track>')

e = [t for t in tl["texts"] if t["kind"] == "endcard"][0]
lines = e["lines"] + ["", "", ""]
ap('      <Track name="Фінальна картка">')
ap(f'        <EndCard name="Фінальна картка" from={{{e["frm"]}}} durationInFrames={{{e["dur"]}}} title={js(e["title"])} sub={js(e["sub"])} line1={js(lines[0])} line2={js(lines[1])} line3={js(lines[2])} handle={js(e["handle"])} />')
ap('      </Track>')

ap('      <Track name="Спалахи">')
for t in tl["transitions"]:
    if t["kind"] == "flash":
        ap(f'        <Flash name="Спалах" from={{{max(0, t["at"] - 3)}}} durationInFrames={{10}} />')
ap('      </Track>')

ap('      <Track name="Музика">')
ap(f'        <Audio name={js("Музика · " + os.path.splitext(os.path.basename(P.cfg.get("music", "music")))[0] + " — вже приглушена під голос")} src={{staticFile("music_bed.wav")}} volume={{1}} />')
ap('      </Track>')

VOL = {"whoosh": 0.32, "pop": 0.22, "tick": 0.15}
sfx = [dict(s, frm=max(0, s["at"]), dur=14 if s["kind"] == "whoosh" else 4 if s["kind"] == "tick" else 3) for s in tl["sfx"]]
for i, row in enumerate(tracks(sfx)):
    ap(f'      <Track name="SFX{"" if i == 0 else f" {i+1}"}">')
    for s in row:
        ap(f'        <Audio name="{s["kind"]}" src={{staticFile("sfx/{s["kind"]}.wav")}} from={{{s["frm"]}}} volume={{{VOL[s["kind"]]}}} />')
    ap('      </Track>')

ap('    </AbsoluteFill>')
ap('    </Brand>')
ap('  );')
ap('};')
ap('')
ap('export const Cover: React.FC = () => (')
ap('  <Brand value={brand}>')
ap(f'    <CoverCard name="Обкладинка" bg="cover_bg.jpg" title={js(cov.get("title", ""))} script={js(cov.get("script", ""))} line={js(cov.get("line", ""))} />')
ap('  </Brand>')
ap(');')
os.makedirs(REEL / "src" / "projects", exist_ok=True)
open(REEL / "src" / "projects" / f"{P.id}.tsx", "w", encoding="utf-8").write(NL.join(L) + NL)

# ── Root.tsx: register every project in src/projects ──
imports, comps = [], []
for i, f in enumerate(sorted((REEL / "src" / "projects").glob("*.tsx"))):
    pid = f.stem
    cname = "".join(x.capitalize() for x in re.split(r"[^A-Za-z0-9]+", pid) if x)
    imports.append(f'import * as p{i} from "./projects/{pid}";')
    comps.append(f'    <Composition id={js(pid)} component={{p{i}.{cname}}} durationInFrames={{p{i}.meta.durationInFrames}} fps={{p{i}.meta.fps}} width={{1080}} height={{1920}} />')
    comps.append(f'    <Still id={js(pid + "-cover")} component={{p{i}.Cover}} width={{1080}} height={{1920}} />')
root = (NL.join(["// AUTO-GENERATED by toolkit/py/gen_tsx.py — one composition + cover per projects/<id>",
                  'import React from "react";', 'import { Composition, Still } from "remotion";'] + imports
                 + ["", "export const Root: React.FC = () => (", "  <>"] + comps + ["  </>", ");"]) + NL)
open(REEL / "src" / "Root.tsx", "w", encoding="utf-8").write(root)
print(f"written src/projects/{P.id}.tsx ({len(L)} lines), component {COMP}; caption words hidden under titles:", " ".join(DROPPED))
