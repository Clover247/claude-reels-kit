"""EDL -> frame timeline (timeline.json) + mezzanine video + cleaned master voice + SFX.
Usage: python build.py <project_dir> [--plan] [--fresh]
  --plan  : only print durations (no encoding; may extract a48/ audio for the VAD)
  --fresh : re-make cached public/mezz/ and clean/ (they are otherwise reused if present)
"""
import json, os, sys, subprocess, math
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from common import project, FFBIN, h264_mezz_args
import rustle
import vad

P = project()
_edl = P.edl()
HOOK, BLOCKS, END, FIX = getattr(_edl, "HOOK", None), _edl.BLOCKS, _edl.END, getattr(_edl, "FIX", {})
vad.use(P)
W = P.W
PUB = P.pub
FF = str(FFBIN)   # bin dir (code below calls f"{FF}/ffmpeg")
FPS, SR = P.fps, 48000
SPF = SR // FPS  # samples per frame
# pause tightening: only pauses > GAP_MAX are shortened, keeping PAD_PRE before / PAD_POST after the voice
# (v1 used 0.32/0.08/0.10 -> words were clipped; client feedback: let phrases breathe)
GAP_MAX, PAD_PRE, PAD_POST = 0.50, 0.15, 0.32
TAIL_MAX = 1.0  # range ends may be extended up to this much to let the voice decay naturally
PLAN = "--plan" in sys.argv
FRESH = "--fresh" in sys.argv   # re-make cached mezz/ + clean/ (after changing GRADE, geometry or replacing a source file)


def words(clip):
    return P.words(clip)


def tighten(clip, a, b):
    """split [a,b] at real pauses longer than GAP_MAX (spectral VAD on the raw track), keep short breaths"""
    v = vad.voice(clip)
    i0, i1 = vad._i(v, a), vad._i(v, b)
    quiet = ~v["active"][i0:i1]
    pieces, cur, k = [], a, 0
    n = len(quiet)
    while k < n:
        if quiet[k]:
            j = k
            while j < n and quiet[j]:
                j += 1
            s_t, e_t = a + k / 100, a + j / 100
            if (e_t - s_t) > GAP_MAX and k > 0 and j < n:  # inner pause only
                pieces.append((cur, s_t + PAD_POST))
                cur = e_t - PAD_PRE
            k = j
        else:
            k += 1
    pieces.append((cur, b))
    return [(x, y) for x, y in pieces if y - x > 0.2]


TAIL, PRE_ROLL = 0.28, 0.12   # room left after the voice decays / before the first sound of a phrase


def natural_bounds(clip, a, b):
    """Range bounds from the RAW voice track instead of whisper's word times (which run early).
    End: where the voice actually decays (spectral VAD) + TAIL, never into the next real onset.
         If she talks straight on into the next word, cut in the first near-silent dip ("tight").
    Start: true onset - PRE_ROLL, never before the previous word has decayed (else: last dip before the word).
    Returns (start, end, tight_start, tight_end)."""
    ws = words(clip)
    inside = [w for w in ws if a - 0.05 <= w["s"] < b - 0.12] or [w for w in ws if a - 0.05 <= w["s"] < b]
    if not inside:
        return a, b, False, False
    # ── end ──
    we = inside[-1]["e"]
    after = [w for w in ws if w["s"] > inside[-1]["s"]]
    nw = after[0]["s"] if after else None
    off = vad.voice_off(clip, we - 0.05, limit=TAIL_MAX + 1.0)
    if off is not None and (nw is None or off < nw + 0.35):      # the decay belongs to OUR last word
        nxt_on = vad.next_active(clip, off)
        end = min(off + TAIL, nxt_on - 0.06)
        tight_end = end - off < 0.12
    else:                                                       # running speech: first near-silent dip
        end = vad.dip(clip, we - 0.15, (nw if nw is not None else we) + 0.2)
        tight_end = True
    # ── start ──
    ws0 = inside[0]["s"]
    before = [w for w in ws if w["s"] < inside[0]["s"]]
    if before:
        pe = before[-1]["e"]
        prev_off = vad.voice_off(clip, pe - 0.05, limit=1.5)
        if prev_off is not None and prev_off < ws0 + 0.35:
            on = vad.next_active(clip, prev_off)
            start, tight_start = max(on - PRE_ROLL, prev_off + 0.04), False
        else:
            start, tight_start = vad.dip(clip, pe - 0.15, ws0 + 0.05, last=True), True
    else:
        on = vad.next_active(clip, max(0.0, ws0 - 0.6))
        start, tight_start = max(0.0, on - PRE_ROLL), False
    start = max(start, a - 0.6)
    return start, end, tight_start, tight_end


def fr(t):
    return int(round(t * FPS))


# ───────────────────────── timeline ─────────────────────────
main, broll, texts, trans, sfx, caps_src = [], [], [], [], [], []
t = 0  # frames

# hook
# HOOK = None / shots=[] -> no silent montage: the reel opens straight on the first block (voice-first hook)
hook_from = t
if HOOK and HOOK.get("shots"):
    for clip, s in HOOK["shots"]:
        d = fr(HOOK["shot_dur"])
        main.append(dict(clip=clip, src=fr(s), frm=t, dur=d, zoom=1.08, bw=False, hook=True))
        sfx.append(dict(kind="tick", at=t))
        t += d
    if HOOK.get("title"):
        texts.append(dict(kind="kinetic", lines=[dict(text=l[0], style=l[1], delay=0) for l in HOOK["title"]["lines"]],
                          frm=hook_from + 3, dur=t - hook_from - 3))
    sfx.append(dict(kind="whoosh", at=0))

block_marks = []
for bi, b in enumerate(BLOCKS):
    clip = b["clip"]
    block_start = t
    trans.append(dict(at=t, kind=b.get("trans", "cut")))
    if b.get("trans", "cut") != "cut":
        sfx.append(dict(kind="whoosh", at=max(0, t - 5)))
    mapping = []  # (src_a, src_b, tl_frame_a)
    zoom_toggle = False
    rs = b["ranges"]
    for ri, (a, bb) in enumerate(rs):
        na, nb, t_in, t_out = natural_bounds(clip, a, bb)
        # ranges that (almost) touch are one continuous take split only for a visual change (B&W, punch-in):
        # join them exactly, no boundary processing, so the voice runs on uninterrupted
        if ri > 0 and a - rs[ri - 1][1] <= 0.06:
            na, t_in = rs[ri - 1][1], False
        elif ri > 0:
            na = max(na, rs[ri - 1][1])
        if ri + 1 < len(rs) and rs[ri + 1][0] - bb <= 0.06:
            nb, t_out = rs[ri + 1][0], False
        elif ri + 1 < len(rs):
            nb = min(nb, rs[ri + 1][0])
        pieces = tighten(clip, na, nb)
        for pi, (x, y) in enumerate(pieces):
            ti, to = t_in and pi == 0, t_out and pi == len(pieces) - 1
            # tight cuts sit in a dip between words: quantise to frames AWAY from the neighbouring word
            sf_ = math.ceil(x * FPS) if ti else fr(x)
            ef = math.floor(y * FPS) if to else fr(y)
            d = ef - sf_
            bw = any(x >= p - 0.05 and y <= q + 0.05 for p, q in b.get("bw", []))
            main.append(dict(clip=clip, src=sf_, frm=t, dur=d, zoom=1.12 if zoom_toggle else 1.0, bw=bw, hook=False,
                             tight_in=ti, tight_out=to, rng=[a, bb], piece=pi))
            mapping.append((sf_ / FPS, ef / FPS, t))
            caps_src.append((clip, sf_ / FPS, ef / FPS, t))
            zoom_toggle = not zoom_toggle  # punch-in on every jump cut
            t += d
    block_marks.append((block_start, t))

    def to_tl(src_t, mapping=mapping):
        for a, bb, f0 in mapping:
            if a - 0.05 <= src_t <= bb + 0.05:
                return f0 + fr(max(0.0, src_t - a))
        # nearest following piece
        nxt = [f0 for a, bb, f0 in mapping if a > src_t]
        return nxt[0] if nxt else mapping[-1][2]

    if b.get("section"):
        texts.append(dict(kind="section", text=b["section"], frm=block_start + 4, dur=fr(2.6)))
    block_end = t
    for (bc, s_in, dur, at) in b.get("broll", []):
        f0 = to_tl(at)
        d = min(fr(dur), block_end - 8 - f0)  # leave the block's own shot visible for the transition
        if d > 12:
            broll.append(dict(clip=bc, src=fr(s_in), frm=f0, dur=d))
    for tx in b.get("texts", []):
        tx = dict(tx)
        f0 = to_tl(tx.pop("at"))
        d = min(fr(tx.pop("dur")), block_end - 3 - f0)  # never spill into the next scene
        if tx["kind"] == "kinetic":
            tx["lines"] = [dict(text=l[0], style=l[1], delay=fr(l[2]) if len(l) > 2 else 0) for l in tx["lines"]]
            sfx.append(dict(kind="pop", at=f0))
        texts.append(dict(tx, frm=f0, dur=d))

# end card
end_from = t
trans.append(dict(at=t, kind="flash"))
sfx.append(dict(kind="whoosh", at=t - 5))
d = fr(END["dur"])
main.append(dict(clip=END["clip"], src=fr(END["src"]), frm=t, dur=d, zoom=1.0, bw=False, hook=True, end=True))
texts.append(dict(kind="endcard", frm=t, dur=d, title=END["title"], sub=END["sub"], lines=END["lines"], handle=END["handle"]))
t += d
total = t

# ───────────────────────── captions ─────────────────────────
KINETIC = [(x["frm"], x["frm"] + x["dur"]) for x in texts if x["kind"] == "kinetic"]
caps = []
for clip, a, b, f0 in caps_src:
    for w in words(clip):
        if (a - 0.05 <= w["s"] < b - 0.05) or (a + 0.05 < w["e"] <= b + 0.05 and w["s"] >= a - 0.5):
            txt = w["w"]
            txt = FIX.get(txt, txt)
            if not txt:
                continue
            if caps and caps[-1]["src"] == (clip, w["s"]):
                continue  # same word seen from two adjacent pieces
            s = f0 + fr(max(0.0, w["s"] - a))
            e = f0 + fr(min(b, w["e"]) - a)
            if txt.startswith("-") and caps:  # whisper splits hyphenated words
                caps[-1]["t"] += txt
                caps[-1]["e"] = e
                continue
            caps.append(dict(t=txt, s=s, e=max(e, s + 3), src=(clip, w["s"])))
# chunk into short lines: <=3 words / 22 chars, break after punctuation
chunks, cur = [], []
for w in caps:
    if cur and (len(cur) >= 3 or len(" ".join(c["t"] for c in cur + [w])) > 22 or w["s"] - cur[-1]["e"] > 9
                or cur[-1]["t"][-1] in ".,?!"):
        chunks.append(cur); cur = []
    cur.append(w)
if cur:
    chunks.append(cur)
captions = []
for i, c in enumerate(chunks):
    s, e = c[0]["s"], c[-1]["e"] + 4
    if i + 1 < len(chunks):
        e = min(max(e, s + 8), chunks[i + 1][0]["s"])
    if any(ks <= s < ke or ks < e <= ke for ks, ke in KINETIC):
        continue
    captions.append(dict(frm=s, dur=max(6, e - s), words=[dict(t=w["t"], s=w["s"] - s) for w in c]))

tl = dict(fps=FPS, width=1080, height=1920, durationInFrames=total, main=main, broll=broll,
          texts=texts, transitions=trans, sfx=sfx, captions=captions)
print(f"TOTAL {total/FPS:.1f}s  ({total} frames)  hook {(block_marks[0][0])/FPS:.1f}s")
for (s, e), b in zip(block_marks, BLOCKS):
    print(f"  {b['clip']} {s/FPS:6.1f}-{e/FPS:6.1f}  ({(e-s)/FPS:.1f}s)  {b.get('section','')}")
if PLAN:
    sys.exit()

os.makedirs(PUB, exist_ok=True)
json.dump(tl, open(f"{PUB}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ───────────────────────── mezzanine video ─────────────────────────
os.makedirs(f"{PUB}/mezz", exist_ok=True)
used = sorted({m["clip"] for m in main} | {b_["clip"] for b_ in broll})
GRADE = "eq=contrast=1.05:saturation=1.07:gamma=0.98,unsharp=5:5:0.35"
# iPhone HDR (HLG / Dolby Vision = arib-std-b67, HDR10 = smpte2084) looks flat & washed out if just scaled -> tonemap to SDR bt709
TONEMAP = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"


def mezz_filter(c):
    """fps + HDR tonemap + geometry to 1080x1920 + grade.
    Portrait (9:16-ish) -> scale. Landscape/square -> project.json "fit": {clip: "crop"|"blur"} (default blur:
    the whole frame fitted over a blurred fill — keeps screens/monitors readable; "crop" = centre crop, fills the frame)."""
    import json as _j
    pr = _j.loads(subprocess.run([f"{FF}/ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height,color_transfer:stream_side_data=rotation", "-of", "json", P.raw(c)],
                                 capture_output=True, text=True).stdout)["streams"][0]
    w, h = pr["width"], pr["height"]
    rot = next((abs(int(sd.get("rotation", 0))) for sd in pr.get("side_data_list", []) if "rotation" in sd), 0)
    if rot in (90, 270):
        w, h = h, w                      # ffmpeg autorotates on decode; geometry is the displayed one
    hdr = pr.get("color_transfer") in ("arib-std-b67", "smpte2084")
    pre = f"fps={FPS}," + (TONEMAP if hdr else "")
    if w / h <= 0.6:
        return f"{pre}scale=1080:1920:flags=lanczos,{GRADE},format=yuv420p"
    if P.cfg.get("fit", {}).get(c, "blur") == "crop":
        return f"{pre}scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,{GRADE},format=yuv420p"
    return (f"{pre}split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:4,eq=brightness=-0.06[bg];"
            f"[b]scale=1080:-2:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,{GRADE},format=yuv420p")
for c in used:
    out = f"{PUB}/mezz/{c}.mp4"
    if os.path.exists(out) and not FRESH:
        continue
    enc = h264_mezz_args()
    cmd = [f"{FF}/ffmpeg", "-v", "error", "-y"] + (["-hwaccel", "cuda"] if "h264_nvenc" in enc else []) + ["-i", P.raw(c),
           "-vf", mezz_filter(c)] + enc + ["-an", out]
    subprocess.run(cmd, check=True)
    print("mezz", c)

# ───────────────────────── master voice ─────────────────────────
os.makedirs(f"{W}/clean", exist_ok=True)
speech_clips = sorted({m["clip"] for m in main if not m.get("hook")})
for c in speech_clips:
    out = f"{W}/clean/{c}.wav"
    if os.path.exists(out) and not FRESH:
        continue
    src = f"{W}/a48/{c}.wav"
    if not os.path.exists(src):
        subprocess.run([f"{FF}/ffmpeg", "-v", "error", "-y", "-i", P.raw(c), "-vn", "-ac", "1", "-ar", str(SR), src], check=True)
    x, _ = sf.read(src, dtype="float32")
    y, ev = rustle.repair(x, SR)
    tmp = f"{W}/clean/{c}_rep.wav"
    sf.write(tmp, y, SR)
    subprocess.run([f"{FF}/ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "highpass=f=85,afftdn=nr=8:nf=-44:tn=1,deesser=i=0.25,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2",
                    out], check=True)
    os.remove(tmp)
    print(f"clean {c}: {len(ev)} clicks repaired")

master = np.zeros(total * SPF, np.float32)
fade = int(0.012 * SR)
ramp = np.linspace(0, 1, fade, dtype=np.float32)
cache = {}
for m in main:
    if m.get("hook"):
        continue
    c = m["clip"]
    if c not in cache:
        cache[c], _ = sf.read(f"{W}/clean/{c}.wav", dtype="float32")
    a = m["src"] * SPF
    seg = cache[c][a:a + m["dur"] * SPF].copy()
    seg[:fade] *= ramp
    seg[-fade:] *= ramp[::-1]
    o = m["frm"] * SPF
    master[o:o + len(seg)] += seg
sf.write(f"{W}/clean/master_raw.wav", master, SR)
# loudness normalise to -15 LUFS (leaves room for SFX; final pass after render)
subprocess.run([f"{FF}/ffmpeg", "-v", "error", "-y", "-i", f"{W}/clean/master_raw.wav", "-af",
                "loudnorm=I=-15:TP=-1.5:LRA=9", "-ar", str(SR), f"{PUB}/voice.wav"], check=True)

# ───────────────────────── SFX (synthesised, no licensing issues) ─────────────────────────
os.makedirs(f"{PUB}/sfx", exist_ok=True)
rng = np.random.default_rng(7)
def save(name, y):
    sf.write(f"{PUB}/sfx/{name}.wav", (y / (np.abs(y).max() + 1e-9) * 0.5).astype(np.float32), SR)
# whoosh: noise through a sweeping band-pass, bell envelope
n = int(0.42 * SR); tt = np.arange(n) / SR
noise = rng.standard_normal(n).astype(np.float32)
from scipy.signal import butter, sosfilt
out = np.zeros(n, np.float32); step = 1024
for i in range(0, n, step):
    fc = 300 + 3200 * math.sin(math.pi * i / n) ** 2
    sos = butter(2, [max(80, fc * 0.6), min(20000, fc * 1.6)], btype="band", fs=SR, output="sos")
    out[i:i + step] = sosfilt(sos, noise[i:i + step])
env = np.sin(np.pi * tt / tt[-1]) ** 2.2
save("whoosh", out * env)
# pop: short pitched blip
n = int(0.09 * SR); tt = np.arange(n) / SR
save("pop", np.sin(2 * np.pi * (700 + 500 * np.exp(-tt * 40)) * tt) * np.exp(-tt * 45))
# tick: tiny click for hook cuts
n = int(0.03 * SR); tt = np.arange(n) / SR
save("tick", rng.standard_normal(n) * np.exp(-tt * 250))
print("done")
