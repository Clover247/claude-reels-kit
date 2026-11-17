"""Ear-test the edit: re-transcribe the EDITED voice (clean/master_raw.wav) with whisper and diff it
against the words that should be audible. A word that vanishes right at a cut = the cut ate it.
Usage: python verify_words.py <project_dir>
"""
import json, os, sys, re, difflib, subprocess
from common import project, FF, whisper_model
import soundfile as sf

P = project()
W = P.W
FPS = P.fps
tl = json.load(open(f"{P.pub}/timeline.json", encoding="utf-8"))
norm = lambda s: re.sub(r"[^\w']", "", s.lower().replace("ʼ", "'"))

# words that should be heard, in timeline order (same inclusion rule as the captions)
exp, cache = [], {}
for m in tl["main"]:
    if m.get("hook"):
        continue
    c = m["clip"]
    if c not in cache:
        cache[c] = P.words(c)
    a, b = m["src"] / FPS, (m["src"] + m["dur"]) / FPS
    mi = tl["main"].index(m); prev = tl["main"][mi - 1]
    lo = (prev["src"] + prev["dur"]) / FPS if m.get("piece", 0) > 0 and prev["clip"] == c else a - 0.6
    ra, rb = m.get("rng", [a, b])
    for w in cache[c]:
        if lo <= w["s"] < b and w["e"] > a + 0.05 and w["s"] < rb - 0.12 and w["e"] > ra + 0.05:
            tt = (m["frm"] + max(0, w["s"] - a) * FPS) / FPS
            edge = min(abs(w["s"] - a), abs(b - w["e"]))
            exp.append(dict(w=norm(w["w"]), raw=w["w"], t=tt, edge=edge, clip=c))

tmp = f"{W}/clean/master16k.wav"
subprocess.run([FF, "-v", "error", "-y", "-i", f"{W}/clean/master_raw.wav", "-ac", "1", "-ar", "16000", tmp], check=True)
audio, _ = sf.read(tmp, dtype="float32")
import stt
if stt.engine(P.cfg, sys.argv) == "deepgram":
    got = [dict(w=norm(w["word"]), raw=w["word"], t=w["start"])
           for w in stt.transcribe(tmp, P.cfg.get("language", "uk"), P.cfg.get("keyterms", []))["words"]]
else:
    model = whisper_model()
    segs, _ = model.transcribe(audio, language=P.cfg.get("language", "uk"), word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, initial_prompt=P.cfg.get("whisper_prompt"))
    got = [dict(w=norm(w.word), raw=w.word.strip(), t=w.start) for s in segs for w in (s.words or [])]
print(f"heard via {'deepgram' if 'model' not in dir() else 'whisper'}")

sm = difflib.SequenceMatcher(a=[e["w"] for e in exp], b=[g["w"] for g in got], autojunk=False)
issues = 0
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal":
        continue
    miss = exp[i1:i2]
    near_cut = any(e["edge"] < 0.35 for e in miss)
    if op == "insert":
        continue  # extra words heard = whisper noise, or a neighbour's syllable leaking in (checked by ear below)
    tag = "AT CUT" if near_cut else "asr"
    issues += near_cut
    print(f"{tag:6} {miss[0]['t']:6.1f}s {miss[0]['clip']}  expected: {' '.join(e['raw'] for e in miss):40}  heard: {' '.join(g['raw'] for g in got[j1:j2])}")
print(f"\n{len(exp)} expected words, {len(got)} heard, similarity {sm.ratio():.3f}, {issues} differences at cuts")
