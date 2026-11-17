"""STEP 1 of every reel: look at ALL raw footage before deciding anything.
For each clip in project.json "samples":
  clips.json            duration / resolution / fps / rotation / audio yes-no
  proxy/<stem>.mp4      540x960 h264 (fast to scrub, small for contact sheets)
  audio/<stem>.wav      16 kHz mono (whisper input)
  sheets/<stem>.jpg     contact sheet, <=24 frames with burned-in timecode  -> LOOK at these (Read tool)
  transcripts/<stem>.json  word timestamps: faster-whisper large-v3 (local, GPU/CPU) or Deepgram nova-3 (cloud) — see stt.engine
Then prints an overview table (clip, length, words, first words) to plan blocks from.
Idempotent: existing outputs are skipped. Usage: python ingest.py <project_dir> [--no-whisper] [--cpu] [--stt whisper|deepgram]
"""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, FFPROBE, TOOLKIT, ui_font, whisper_model

P = project()
clips = P.clips()
if not clips:
    sys.exit(f"no video files in {P.samples}")
font = ui_font()   # static bold: variable Montserrat renders hairline-thin in ffmpeg
meta = {}
for c, f in clips.items():
    stem = P.prefix + c
    pr = json.loads(subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                                    "format=duration:stream=codec_type,width,height,r_frame_rate,color_transfer:stream_side_data=rotation",
                                    "-of", "json", str(f)], capture_output=True, text=True).stdout)
    v = next((s for s in pr["streams"] if s["codec_type"] == "video"), {})
    rot = next((sd.get("rotation") for s in pr["streams"] for sd in s.get("side_data_list", []) if "rotation" in sd), 0)
    w, h = v.get("width"), v.get("height")
    if abs(int(rot or 0)) in (90, 270):
        w, h = h, w
    meta[c] = dict(file=f.name, dur=round(float(pr["format"]["duration"]), 2), w=w, h=h, fps=v.get("r_frame_rate"), rotation=rot,
                   hdr=v.get("color_transfer") in ("arib-std-b67", "smpte2084"), landscape=bool(w and h and w / h > 0.6),
                   audio=any(s["codec_type"] == "audio" for s in pr["streams"]))
    px = P.path("proxy", f"{stem}.mp4")
    if not os.path.exists(px):
        subprocess.run([FF, "-v", "error", "-y", "-i", str(f), "-vf", "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:-1:-1,fps=30",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "128k", px], check=True)
    au = P.path("audio", f"{stem}.wav")
    if meta[c]["audio"] and not os.path.exists(au):
        subprocess.run([FF, "-v", "error", "-y", "-i", str(f), "-vn", "-ac", "1", "-ar", "16000", au], check=True)
    sh = P.path("sheets", f"{stem}.jpg")
    if not os.path.exists(sh):
        iv = max(1.0, meta[c]["dur"] / 24)
        # fontfile path: ffmpeg filter syntax needs ':' escaped on Windows
        ff = font.replace("\\", "/").replace(":", "\\:")
        subprocess.run([FF, "-v", "error", "-y", "-i", px, "-vf",
                        f"fps=1/{iv},scale=200:-2,drawtext=fontfile='{ff}':text='%{{pts\\:hms}}':x=4:y=4:fontsize=18:"
                        f"fontcolor=yellow:box=1:boxcolor=black@0.6,tile=8x3:padding=2", "-frames:v", "1", sh], check=True)
    print(f"ok {stem}")
json.dump(meta, open(P.path("clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

import stt
ENGINE = stt.engine(P.cfg, sys.argv)
if "--no-whisper" not in sys.argv and ENGINE == "deepgram":
    for c in clips:
        stem = P.prefix + c
        out, au = P.transcript(c), P.path("audio", f"{stem}.wav")
        if os.path.exists(out) or not os.path.exists(au):
            continue
        t0 = time.time()
        data = stt.segments(au, P.cfg.get("language", "uk"), P.cfg.get("keyterms", []))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"file": stem, "duration": meta[c]["dur"], "engine": "deepgram", "segments": data},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"deepgram {stem}: {len(data)} segments in {time.time() - t0:.0f}s")
elif "--no-whisper" not in sys.argv:
    import soundfile as sf
    model = None
    for c in clips:
        stem = P.prefix + c
        out, au = P.transcript(c), P.path("audio", f"{stem}.wav")
        if os.path.exists(out) or not os.path.exists(au):
            continue
        model = model or whisper_model(force_cpu="--cpu" in sys.argv)
        t0 = time.time()
        audio, sr = sf.read(au, dtype="float32")   # numpy in: PyAV 19 breaks faster-whisper's own decoder
        segs, info = model.transcribe(audio, language=P.cfg.get("language", "uk"), word_timestamps=True, vad_filter=True,
                                      vad_parameters={"min_silence_duration_ms": 300}, initial_prompt=P.cfg.get("whisper_prompt"))
        data = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                 "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)} for w in (s.words or [])]}
                for s in segs]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"file": stem, "duration": info.duration, "segments": data}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"whisper {stem}: {len(data)} segments in {time.time() - t0:.0f}s")

print(f"\n{'clip':10} {'dur':>6}  {'words':>5}  first words")
for c, m in meta.items():
    ws = P.words(c)
    print(f"{c:10} {m['dur']:6.1f}  {len(ws):5d}  {' '.join(w['w'] for w in ws[:12])}")
skipped = [f.name for f in P.samples.iterdir() if f.is_file() and f.name not in {m["file"] for m in meta.values()}]
if skipped:
    print(f"\n!! not ingested (not a video, or name doesn't start with clip_prefix '{P.prefix}'): {', '.join(skipped)}")
    print("   photos: turn into a clip if needed, e.g. ffmpeg -loop 1 -i photo.jpg -t 4 -r 30 -pix_fmt yuv420p <prefix>photo1.mp4")
hdr = [c for c, m in meta.items() if m["hdr"]]
land = [c for c, m in meta.items() if m["landscape"]]
if hdr:
    print(f"!! HDR (HLG/PQ) clips - build.py tonemaps them to SDR automatically: {', '.join(hdr)}")
if land:
    print(f"!! landscape/square clips - fitted over a blurred fill; project.json \"fit\": {{clip: \"crop\"}} to centre-crop: {', '.join(land)}")
print(f"\nNext: Read sheets/*.jpg + transcripts, then write {P.dir / 'edl.py'}")
