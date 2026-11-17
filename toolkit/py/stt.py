"""Speech-to-text via Deepgram (cloud, nova-3) — alternative to local whisper: ingest.py / verify_words.py use it with
`--stt deepgram` or project.json "stt": "deepgram" (auto when there is no NVIDIA GPU but a key exists); also for TTS checks.
  python stt.py <audio> [<audio> ...]          prints transcript, words/s, duration per file
  from stt import transcribe; words = transcribe(path)   -> [{word, start, end, confidence}] + text
Key: env DEEPGRAM_API_KEY or <repo>/.secrets/deepgram.key. Model nova-3 (falls back to nova-2 if a language is refused).
NOTE: word times from ANY ASR are not cut points (see lessons.md) — cuts still come from vad.py / energy decay.
"""
import json, mimetypes, os, sys, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT


def api_key():
    k = os.environ.get("DEEPGRAM_API_KEY", "").strip()
    f = ROOT / ".secrets" / "deepgram.key"
    if not k and f.exists():
        k = f.read_text(encoding="utf-8").strip()
    if not k:
        sys.exit("no Deepgram key: env DEEPGRAM_API_KEY or .secrets/deepgram.key")
    return k


def _call(path, model, language, keyterms=()):
    q = f"model={model}&language={language}&smart_format=true&punctuate=true"
    for t in keyterms:
        q += "&keyterm=" + urllib.parse.quote(t) if model == "nova-3" else ""
    data = open(path, "rb").read()
    ct = mimetypes.guess_type(path)[0] or "audio/wav"
    r = urllib.request.Request(f"https://api.deepgram.com/v1/listen?{q}", data=data,
                               headers={"Authorization": f"Token {api_key()}", "Content-Type": ct})
    with urllib.request.urlopen(r, timeout=300) as resp:
        return json.loads(resp.read())


def transcribe(path, language="uk", keyterms=()):
    import urllib.parse  # noqa: F401  (used in _call)
    last = None
    for model in ("nova-3", "nova-2"):
        try:
            j = _call(path, model, language, keyterms)
            alt = j["results"]["channels"][0]["alternatives"][0]
            return dict(model=model, text=alt.get("transcript", ""), words=[
                dict(word=w.get("punctuated_word", w["word"]), start=w["start"], end=w["end"], confidence=w.get("confidence", 0))
                for w in alt.get("words", [])], duration=j.get("metadata", {}).get("duration", 0))
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read().decode(errors='replace')[:300]}"
    sys.exit(f"Deepgram failed — {last}")


import urllib.parse  # noqa: E402


def segments(path, language="uk", keyterms=(), gap=0.8):
    """Deepgram words -> the transcript format ingest.py writes for whisper:
    [{start, end, text, words: [{w, s, e, p}]}]; a segment ends at . ! ? or a pause > gap s."""
    ws = transcribe(path, language, keyterms)["words"]
    segs, cur = [], []
    for i, w in enumerate(ws):
        cur.append(dict(w=w["word"], s=round(w["start"], 2), e=round(w["end"], 2), p=round(w["confidence"], 2)))
        nxt = ws[i + 1]["start"] if i + 1 < len(ws) else None
        if w["word"].endswith((".", "!", "?", "…")) or nxt is None or nxt - w["end"] > gap:
            segs.append(dict(start=cur[0]["s"], end=cur[-1]["e"], text=" ".join(x["w"] for x in cur), words=cur))
            cur = []
    return segs


def has_key():
    return bool(os.environ.get("DEEPGRAM_API_KEY", "").strip()) or (ROOT / ".secrets" / "deepgram.key").exists()


def engine(cfg, argv):
    """Which STT to use: --stt whisper|deepgram, else project.json "stt", else auto
    (whisper on an NVIDIA GPU; no GPU + a Deepgram key -> deepgram; else whisper on CPU)."""
    for i, a in enumerate(argv):
        if a == "--stt" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--stt="):
            return a.split("=", 1)[1]
    if cfg.get("stt") in ("whisper", "deepgram"):
        return cfg["stt"]
    from common import has_cuda
    return "whisper" if has_cuda() or not has_key() else "deepgram"

if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = transcribe(p)
        ws = r["words"]
        rate = len(ws) / max(0.01, ws[-1]["end"] - ws[0]["start"]) if ws else 0
        low = [w["word"] for w in ws if w["confidence"] < 0.6]
        print(f"{os.path.basename(p)}  [{r['model']}] {r['duration']:.2f}s  {rate:.2f} w/s  low-conf: {low}\n   {r['text']}")
