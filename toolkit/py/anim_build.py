"""Build an ANIMATED project (project.json "type": "anim"): script.py + tts/ -> everything the episode .tsx needs.
  python anim_build.py <project_dir>
Writes:  public/vo.wav (voice-over, -16 LUFS)  clean/master_raw.wav (for music.py ducking)  public/sfx/*.wav  public/fonts/
         public/timeline.json (for review.py)   toolkit/reel/src/projects/<id>.data.ts (frames of lines/words, caption pages)
         toolkit/reel/src/Root.tsx (registry of every src/projects/*.tsx)
Timing: real ElevenLabs character alignment (tts.py) when present, otherwise ESTIMATED (silent voice, data.estimated=true)
so the animation can be built and previewed before the voice exists.
Line clip = voice from first character (−0.06 s) to the real energy decay after the last character (+0.15 s): we never
cut on alignment times alone (same rule as whisper times in footage projects).
"""
import json, math, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, ROOT, REEL
from tts import load_script, spoken_text
import numpy as np, soundfile as sf

P = project()
S = load_script(P)
FPS = P.fps
SR = 48000
W, PUB = P.W, P.pub
os.makedirs(f"{PUB}/sfx", exist_ok=True)
os.makedirs(f"{W}/clean", exist_ok=True)
brand = json.load(open(ROOT / P.cfg["brand"], encoding="utf-8"))
START = 0.12                         # first voice onset (s)
END_SEC = getattr(S, "END_CARD_SEC", 3.4)
STYLE = {"*": "warm", "_": "cold", "!": "danger", "~": "ok"}
fr = lambda t: int(round(t * FPS))


def tokens(text):
    """display tokens [(display, style)] aligned 1:1 with spoken tokens; punctuation-only tokens ('—') join the previous."""
    disp, say = text.split(), spoken_text(text).split()
    assert len(disp) == len(say), (disp, say)
    out = []
    for d, s in zip(disp, say):
        st = next((v for k, v in STYLE.items() if k in d), "")
        show = re.sub(r"[*_!~]", "", re.sub(r"\{([^|}]*)\|[^}]*\}", r"\1", d))
        if not re.search(r"\w", show) and out:
            out[-1]["w"] += " " + show; out[-1]["say"] += " " + s
            continue
        out.append(dict(w=show, say=s, style=st))
    return out


def estimate(toks):
    """rough narration timing (≈2.7 words/s) for previews without a voice."""
    t, res = 0.0, []
    for k in toks:
        n = len(re.sub(r"\W", "", k["say"]))
        d = 0.064 * n + 0.08
        res.append((t, t + d))
        t += d + (0.22 if re.search(r"[,:—]$", k["say"]) else 0.04)
    return res, t


def align(toks, j):
    """word (start, end) from ElevenLabs character alignment."""
    chars = "".join(j["chars"])
    res, pos = [], 0
    for k in toks:
        word = re.sub(r"[^\w']", "", k["say"].split()[0]) or k["say"]
        i = chars.find(word[:3], pos)
        if i < 0:
            return None
        e = i + len(word) - 1
        res.append((j["starts"][i], j["ends"][min(e, len(j["ends"]) - 1)]))
        pos = e + 1
    return res


def decode(mp3):
    tmp = f"{W}/clean/_tmp.wav"
    subprocess.run([FF, "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(SR), tmp], check=True)
    a, _ = sf.read(tmp, dtype="float32")
    return a


def decay_after(a, t):
    """first time >= t where the 20 ms RMS falls 40 dB under the clip peak (the voice really stopped)."""
    h = int(0.02 * SR)
    pk = np.abs(a).max() + 1e-9
    i = int(t * SR)
    while i + h < len(a) and i < int((t + 0.8) * SR):
        if 20 * np.log10(np.sqrt(np.mean(a[i:i + h] ** 2)) / pk + 1e-12) < -40:
            return i / SR
        i += h // 2
    return min(len(a) / SR, t + 0.8)


lines, chunks, t = [], [], START
real = 0
for ln in S.LINES:
    toks = tokens(ln["text"])
    jp, mp = P.dir / "tts" / f"{ln['id']}.json", P.dir / "tts" / f"{ln['id']}.mp3"
    times = None
    if jp.exists() and mp.exists():
        j = json.load(open(jp, encoding="utf-8"))
        if j["spoken"] == spoken_text(ln["text"]):
            times = align(toks, j)
            if times is None:
                print(f"!! {ln['id']}: alignment mismatch -> estimated")
    if times:
        real += 1
        a = decode(str(mp))
        lead = max(0.0, times[0][0] - 0.06)
        tail = max(times[-1][1] + 0.12, decay_after(a, times[-1][1]) + 0.15)
        clip = a[int(lead * SR): int(tail * SR)].copy()
        f = int(0.01 * SR); clip[:f] *= np.linspace(0, 1, f); clip[-f:] *= np.linspace(1, 0, f)
        times = [(s - lead, e - lead) for s, e in times]
        dur = len(clip) / SR
    else:
        times, dur = estimate(toks)
        dur += 0.15
        clip = np.zeros(int(dur * SR), np.float32)
    chunks.append((t, clip))
    words = [dict(w=k["w"], style=k["style"], f0=fr(t + s), f1=fr(t + e)) for k, (s, e) in zip(toks, times)]
    lines.append(dict(id=ln["id"], f0=fr(t), f1=fr(t + dur), words=words))
    t += dur + ln.get("gap", 0.35)

end_f0 = fr(t)
total = end_f0 + fr(END_SEC)
estimated = real < len(S.LINES)

# ── voice track ──
n = int(total / FPS * SR) + SR
vo = np.zeros(n, np.float32)
for t0, c in chunks:
    i = int(t0 * SR); vo[i:i + len(c)] += c[: n - i]
sf.write(f"{W}/clean/master_raw.wav", vo, SR)
if estimated:
    sf.write(f"{PUB}/vo.wav", vo, SR)
else:
    subprocess.run([FF, "-v", "error", "-y", "-i", f"{W}/clean/master_raw.wav", "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-ar", str(SR), f"{PUB}/vo.wav"], check=True)

# ── caption pages: ≤3 words / ≤18 chars, break after punctuation; lifetime = last word + 0.5 s ──
pages = []
for L in lines:
    cur = []
    for k, wd in enumerate(L["words"]):
        cur.append(wd)
        txt = " ".join(x["w"] for x in cur)
        last = k == len(L["words"]) - 1
        nxt = L["words"][k + 1]["w"] if not last else ""
        short = len(re.sub(r"\W", "", wd["w"])) <= 2          # never leave «в», «з», «по», «й» dangling at a page end
        if last or re.search(r"[,.:—?!]$", wd["w"]) or (not short and (len(cur) >= 3 or len(txt) + 1 + len(nxt) > 18)):
            pages.append(cur); cur = []
P_OUT = []
for i, pg in enumerate(pages):
    f0 = pg[0]["f0"] - 2
    f1 = pg[-1]["f1"] + fr(0.5)
    if i + 1 < len(pages):
        f1 = min(f1, pages[i + 1][0]["f0"] - 2)
    longest = max(len(x["w"]) for x in pg)
    fs = int(min(88, 900 / (0.70 * max(longest, 1))))
    P_OUT.append(dict(f0=f0, f1=max(f1, f0 + 6), fs=fs, words=[dict(w=x["w"], f=x["f0"] - f0, style=x["style"]) for x in pg]))

# ── SFX (synthesised, no licensing issues) ──
rng = np.random.default_rng(7)
from scipy.signal import butter, sosfilt


def save(name, y, peak=0.5):
    sf.write(f"{PUB}/sfx/{name}.wav", (y / (np.abs(y).max() + 1e-9) * peak).astype(np.float32), SR)


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


x = tt(0.42); noise = rng.standard_normal(len(x)); o = np.zeros(len(x)); st = 1024
for i in range(0, len(x), st):
    fc = 300 + 3200 * math.sin(math.pi * i / len(x)) ** 2
    o[i:i + st] = band(noise[i:i + st], max(80, fc * 0.6), min(20000, fc * 1.6))
save("whoosh", o * np.sin(np.pi * x / x[-1]) ** 2.2)
x = tt(0.09); save("pop", np.sin(2 * np.pi * (700 + 500 * np.exp(-x * 40)) * x) * np.exp(-x * 45))
x = tt(0.03); save("tick", rng.standard_normal(len(x)) * np.exp(-x * 250), 0.35)
x = tt(0.16); save("beep", np.sin(2 * np.pi * 2350 * x) * np.minimum(1, np.minimum(x / 0.005, (x[-1] - x) / 0.02)), 0.3)
x = tt(0.06); save("click", band(rng.standard_normal(len(x)), 1500, 6000) * np.exp(-x * 120) + 0.6 * np.sin(2 * np.pi * 180 * x) * np.exp(-x * 60), 0.5)
x = tt(0.5); save("tape", band(rng.standard_normal(len(x)), 900, 7000) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 38 * x))) * np.sin(np.pi * x / x[-1]) ** 0.6, 0.3)
x = tt(0.35)
save("ding", (np.sin(2 * np.pi * 1318 * x) + 0.5 * np.sin(2 * np.pi * 1976 * x)) * np.exp(-x * 9), 0.35)
# wind: 60 s bed of low band noise with slow gusts
x = tt(60.0); w = sosfilt(butter(2, [120, 900], btype="band", fs=SR, output="sos"), rng.standard_normal(len(x)))
g = 0.55 + 0.45 * np.sin(2 * np.pi * x / 5.3) * np.sin(2 * np.pi * x / 3.1 + 1)
f = int(0.5 * SR); w = w * g; w[:f] *= np.linspace(0, 1, f); w[-f:] *= np.linspace(1, 0, f)
save("wind", w, 0.5)
# riser: rising filtered noise for the reveal of step 4
x = tt(0.9); o = np.zeros(len(x)); noise = rng.standard_normal(len(x))
for i in range(0, len(x), st):
    fc = 400 + 5000 * (i / len(x)) ** 2
    o[i:i + st] = band(noise[i:i + st], fc * 0.7, min(20000, fc * 1.4))
save("riser", o * (x / x[-1]) ** 2, 0.4)
# drip: short rising "plip"; knock: dull tap on plastic; stamp: low thud + click
x = tt(0.12); save("drip", np.sin(2 * np.pi * (500 + 2600 * x / x[-1]) * x) * np.exp(-x * 38), 0.35)
x = tt(0.08); save("knock", band(rng.standard_normal(len(x)), 200, 1800) * np.exp(-x * 70) + 0.8 * np.sin(2 * np.pi * 140 * x) * np.exp(-x * 50), 0.5)
x = tt(0.25); save("stamp", np.sin(2 * np.pi * 70 * x) * np.exp(-x * 18) + 0.3 * band(rng.standard_normal(len(x)), 800, 5000) * np.exp(-x * 60), 0.55)

# ── fonts ──
os.makedirs(f"{PUB}/fonts", exist_ok=True)
bdir = (ROOT / P.cfg["brand"]).parent
for f in (bdir / "fonts").glob("*.ttf"):
    shutil.copy(f, f"{PUB}/fonts/{f.name}")

# ── timeline.json (review.py: one frame per line + end card) ──
texts = [dict(kind=L["id"], frm=L["f0"], dur=L["f1"] - L["f0"]) for L in lines] + [dict(kind="end", frm=end_f0, dur=fr(END_SEC))]
json.dump(dict(fps=FPS, durationInFrames=total, texts=texts, transitions=[]), open(f"{PUB}/timeline.json", "w", encoding="utf-8"), indent=1)

# ── data module for the episode .tsx ──
data = dict(fps=FPS, durationInFrames=total, estimated=estimated, endF0=end_f0, lines=lines, pages=P_OUT,
            brand=dict(name=brand.get("name", ""), instagram=brand.get("instagram", ""), colors=brand["colors"],
                       anim=brand.get("anim", {}), fonts=brand["fonts"]))
src = REEL / "src" / "projects"
(src / f"{P.id}.data.ts").write_text("// AUTO-GENERATED by toolkit/py/anim_build.py — do not edit (re-run the script)\nexport const DATA = "
                                     + json.dumps(data, ensure_ascii=False) + " as const;\n", encoding="utf-8")

# ── Root.tsx registry (same format as gen_tsx.py) ──
NL = chr(10)
imports, comps = [], []
for i, f in enumerate(sorted(src.glob("*.tsx"))):
    pid = f.stem
    cname = "".join(x.capitalize() for x in re.split(r"[^A-Za-z0-9]+", pid) if x)
    imports.append(f'import * as p{i} from "./projects/{pid}";')
    comps.append(f'    <Composition id={json.dumps(pid)} component={{p{i}.{cname}}} durationInFrames={{p{i}.meta.durationInFrames}} fps={{p{i}.meta.fps}} width={{1080}} height={{1920}} />')
    comps.append(f'    <Still id={json.dumps(pid + "-cover")} component={{p{i}.Cover}} width={{1080}} height={{1920}} />')
root = NL.join(["// AUTO-GENERATED by toolkit/py/gen_tsx.py / anim_build.py — one composition + cover per src/projects/<id>.tsx",
                'import React from "react";', 'import { Composition, Still } from "remotion";'] + imports
               + ["", "export const Root: React.FC = () => (", "  <>"] + comps + ["  </>", ");"]) + NL
(REEL / "src" / "Root.tsx").write_text(root, encoding="utf-8")

print(f"{'ESTIMATED timing (no TTS yet)' if estimated else 'real TTS timing'}: {len(lines)} lines, {len(P_OUT)} caption pages, "
      f"voice ends {end_f0 / FPS:.1f}s, total {total / FPS:.1f}s")
for L in lines:
    print(f"  {L['id']:<8} {L['f0'] / FPS:5.2f}-{L['f1'] / FPS:5.2f}  " + " ".join(w["w"] for w in L["words"]))
