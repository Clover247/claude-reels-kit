"""Voice-over for animated projects (project.json "type": "anim"): one TTS request per script line, cached.
  python tts.py <project_dir>               synthesise every line of script.py (cached by text+voice settings)
  python tts.py <project_dir> --voices      list the voices on the ElevenLabs account
  python tts.py <project_dir> --audition id1 id2 ...   the hook line in each voice -> tts/audition_<id>.mp3 (owner picks by ear)
Key: env ELEVENLABS_API_KEY or the file <repo>/.secrets/elevenlabs.key (never paste keys into chat / code).
Output per line: tts/<line_id>.mp3 + tts/<line_id>.json {spoken, chars, starts, ends} (ElevenLabs character alignment).
No key -> nothing is synthesised; anim_build.py falls back to estimated timing (silent voice) so the animation can be previewed.
"""
import base64, hashlib, json, os, re, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from common import project, ROOT

API = "https://api.elevenlabs.io/v1"


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    f = ROOT / ".secrets" / "elevenlabs.key"
    if not k and f.exists():
        k = f.read_text(encoding="utf-8").strip()
    return k


MARK = re.compile(r"[*_!~]")


def spoken_text(text):
    """caption markup -> what the voice says: {SHOW|say} -> say, markers stripped."""
    t = re.sub(r"\{([^|}]*)\|([^}]*)\}", r"\2", text)
    return MARK.sub("", t)


def load_script(P):
    import importlib.util
    spec = importlib.util.spec_from_file_location("script", P.dir / "script.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def req(path, key, body=None):
    r = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                               headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {e.code}: {e.read().decode(errors='replace')[:500]}")


def synth(key, voice, text, prev="", nxt=""):
    body = {"text": text, "model_id": voice.get("model_id", "eleven_multilingual_v2"),
            "voice_settings": {k: voice[k] for k in ("stability", "similarity_boost", "style", "speed") if k in voice}
            | {"use_speaker_boost": True}}
    if prev: body["previous_text"] = prev
    if nxt: body["next_text"] = nxt
    vid = voice["voice_id"]
    return req(f"/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128", key, body)


def main():
    P = project()
    key = api_key()
    voice = P.cfg.get("voice", {})
    out = P.dir / "tts"
    out.mkdir(exist_ok=True)
    if not key:
        print("no ElevenLabs key (env ELEVENLABS_API_KEY or .secrets/elevenlabs.key) -> skipped; anim_build.py will estimate timing")
        return
    if "--voices" in sys.argv:
        for v in req("/voices", key)["voices"]:
            lab = v.get("labels") or {}
            print(f"{v['voice_id']}  {v['name']:<28} {v.get('category',''):<10} {lab.get('gender','')} {lab.get('accent','')} {lab.get('age','')} {lab.get('description','')}")
        return
    S = load_script(P)
    lines = S.LINES
    if "--audition" in sys.argv:
        ids = sys.argv[sys.argv.index("--audition") + 1:]
        for vid in ids:
            r = synth(key, voice | {"voice_id": vid}, spoken_text(lines[0]["text"]) + " " + spoken_text(lines[1]["text"]))
            (out / f"audition_{vid}.mp3").write_bytes(base64.b64decode(r["audio_base64"]))
            print("->", out / f"audition_{vid}.mp3")
        return
    if not voice.get("voice_id"):
        sys.exit('set project.json "voice": {"voice_id": ...}  (python tts.py <p> --voices to list)')
    for i, ln in enumerate(lines):
        say = spoken_text(ln["text"])
        prev = spoken_text(lines[i - 1]["text"]) if i else ""
        nxt = spoken_text(lines[i + 1]["text"]) if i + 1 < len(lines) else ""
        h = hashlib.sha1(json.dumps([say, prev, nxt, voice], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
        jp, mp = out / f"{ln['id']}.json", out / f"{ln['id']}.mp3"
        if jp.exists() and mp.exists() and json.load(open(jp, encoding="utf-8")).get("hash") == h:
            continue
        r = synth(key, voice, say, prev, nxt)
        al = r.get("alignment") or r.get("normalized_alignment")
        mp.write_bytes(base64.b64decode(r["audio_base64"]))
        json.dump({"hash": h, "spoken": say, "chars": al["characters"], "starts": al["character_start_times_seconds"],
                   "ends": al["character_end_times_seconds"]}, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"{ln['id']:<8} {al['character_end_times_seconds'][-1]:5.2f}s  {say}")
    print("tts done")


if __name__ == "__main__":
    main()
