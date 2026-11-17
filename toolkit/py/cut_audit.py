"""Audit every speech cut in <project>/public/timeline.json against the raw voice track.
Prints a table and draws spectrograms around each cut (stills/cut_audit_*.png):
  red    = where the shot is cut now
  yellow = whisper's word end / start
  cyan   = where the voice actually decays / starts (spectral VAD)
  white curve = above-floor speech energy (dB), dashed = threshold
Usage: python cut_audit.py <project_dir> [tag]
"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import vad
from common import project
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = project()
vad.use(P)
W = P.W
FPS = P.fps
tag = sys.argv[2] if len(sys.argv) > 2 else "now"
tl = json.load(open(f"{P.pub}/timeline.json", encoding="utf-8"))
ms = [m for m in tl["main"] if not m.get("hook") and not m.get("end")]


def words(clip):
    return P.words(clip)


rows = []
for i, m in enumerate(ms):
    c, a, b = m["clip"], m["src"] / FPS, (m["src"] + m["dur"]) / FPS
    prv, nxt = (ms[i - 1] if i else None), (ms[i + 1] if i + 1 < len(ms) else None)
    cont_in = prv is not None and prv["clip"] == c and abs((prv["src"] + prv["dur"]) - m["src"]) <= 3
    cont_out = nxt is not None and nxt["clip"] == c and abs((m["src"] + m["dur"]) - nxt["src"]) <= 3
    ws = words(c)
    inside = [w for w in ws if a - 0.05 <= w["s"] < b]
    if not inside:
        continue
    if not cont_out:
        we = max(w["e"] for w in inside if w["s"] < b)
        off = vad.voice_off(c, min(we, b) - 0.05)
        nxt_w = [w["s"] for w in ws if w["s"] >= b - 0.02]
        rows.append(dict(kind="END", tl=m["frm"] + m["dur"], clip=c, cut=b, word=we, voice=off,
                         margin=None if off is None else b - off, live=vad.is_active(c, b),
                         next_word=nxt_w[0] if nxt_w else None, tight=m.get("tight_out", False), text=" ".join(w["w"] for w in inside[-3:])))
    if not cont_in:
        ws0 = min(w["s"] for w in inside)
        on = vad.voice_on(c, ws0)
        rows.append(dict(kind="START", tl=m["frm"], clip=c, cut=a, word=ws0, voice=on, margin=on - a,
                         live=vad.is_active(c, a + 0.03), tight=m.get("tight_in", False), text=" ".join(w["w"] for w in inside[:3])))

print(f"{'':5} {'tl':>6} clip  {'cut':>6} {'whisp':>6} {'voice':>6} {'margin':>6}  verdict   text")
bad = 0
for r in rows:
    mg = r["margin"]
    if r["kind"] == "END":
        verdict = "valley" if r["tight"] else "CLIPPED" if (mg is None or mg < 0.12 or r["live"]) else "tight" if mg < 0.25 else "ok"
    else:
        verdict = "valley" if r["tight"] else "CLIPPED" if mg < 0 else "tight" if mg < 0.08 else "ok"
    r["verdict"] = verdict
    bad += verdict == "CLIPPED"
    v = "  --  " if r["voice"] is None else f"{r['voice']:6.2f}"
    m_ = "  --  " if mg is None else f"{mg:+6.2f}"
    print(f"{r['kind']:5} {r['tl']/FPS:6.1f} {r['clip']} {r['cut']:6.2f} {r['word']:6.2f} {v} {m_}  {verdict:8}  {r['text']}")
print(f"\n{len(rows)} cut edges, {bad} clipped, {sum(r['verdict']=='tight' for r in rows)} tight")
json.dump(rows, open(f"{W}/stills/cut_audit_{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── spectrogram sheet (END cuts only — that's what the ear notices) ──
ends = [r for r in rows if r["kind"] == "END"]
cols = 4
nrow = (len(ends) + cols - 1) // cols
fig, axs = plt.subplots(nrow, cols, figsize=(cols * 4.2, nrow * 2.6), facecolor="#111")
for ax in np.ravel(axs):
    ax.axis("off")
for ax, r in zip(np.ravel(axs), ends):
    v = vad.voice(r["clip"])
    t0, t1 = r["cut"] - 1.6, r["cut"] + 1.2
    k0, k1 = np.searchsorted(v["t"], [t0, t1])
    fb = v["f"] <= 8000
    img = 10 * np.log10(v["S"][k0:k1, fb].T + 1e-12)
    ax.axis("on")
    ax.imshow(img, origin="lower", aspect="auto", cmap="magma", extent=[v["t"][k0], v["t"][k1 - 1], 0, 8],
              vmin=np.percentile(img, 30), vmax=np.percentile(img, 99.5))
    ax2 = ax.twinx()
    ax2.plot(v["t"][k0:k1], v["rel"][k0:k1], color="white", lw=0.9)
    ax2.axhline(v["thr"], color="white", ls="--", lw=0.6, alpha=0.6)
    ax2.set_ylim(-70, 5); ax2.set_yticks([])
    ax.axvspan(r["cut"], t1, color="black", alpha=0.45)        # what the viewer never hears
    ax.axvline(r["cut"], color="red", lw=2)
    ax.axvline(r["word"], color="yellow", lw=1.2, ls=":")
    if r["voice"] is not None:
        ax.axvline(r["voice"], color="cyan", lw=1.4)
    col = {"CLIPPED": "#ff5555", "tight": "#ffcc44", "ok": "#66dd88", "valley": "#88aaff"}[r["verdict"]]
    mg = "—" if r["margin"] is None else f"{r['margin']:+.2f}s"
    ax.set_title(f"{r['tl']/FPS:5.1f}s  {r['clip']}  {r['verdict']} {mg}\n…{r['text'][-34:]}", color=col, fontsize=8)
    ax.tick_params(colors="#aaa", labelsize=6)
    ax.set_ylabel("kHz", color="#aaa", fontsize=6)
plt.tight_layout()
out = f"{W}/stills/cut_audit_{tag}.png"
plt.savefig(out, dpi=80, facecolor="#111")
print("->", out)
