"""Render a project's reel and produce the deliverables.
  python render.py <project_dir>              full 1080x1920 render -> out/<id>_vN_master.mp4 + out/<id>_vN_insta.mp4
                                              + out/<id>_cover.jpg + stills/review_vN.jpg (contact sheet for self-review)
  python render.py <project_dir> --preview    half-res quick check -> out/preview.mp4 (+ review sheet)
  python render.py <project_dir> --studio     open Remotion Studio on this project (visual editing in the browser)
Finishing chain (Instagram): two-pass loudnorm -14 LUFS / TP -1.5 -> master (video stream copied);
insta = libx264 high, 10 Mbps (max 12), yuv420p bt709 tv-range, 30 fps, AAC 192k 48 kHz, +faststart.
"""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, FFPROBE, REEL

P = project()
pub = P.pub
npx = "npx.cmd" if os.name == "nt" else "npx"

if "--studio" in sys.argv:
    print(f"Studio: composition '{P.id}' (media from {pub}). Ctrl+C to stop.")
    subprocess.run([npx, "remotion", "studio", "src/index.ts", f"--public-dir={pub}"], cwd=REEL)
    sys.exit()

os.makedirs(f"{P.W}/out", exist_ok=True)
preview = "--preview" in sys.argv
raw = f"{P.W}/out/{'preview' if preview else 'render_full'}.mp4"
cmd = [npx, "remotion", "render", "src/index.ts", P.id, raw, f"--public-dir={pub}", "--concurrency=8", "--audio-bitrate=192k",
       "--color-space=bt709"]   # default tags yuvj420p/pc/bt470bg; bt709 tv-range is what phones expect
cmd += ["--scale=0.5", "--crf=23"] if preview else ["--crf=16"]
subprocess.run(cmd, cwd=REEL, check=True)


def loud(path):
    r = subprocess.run([FF, "-hide_banner", "-i", path, "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return json.loads(r[r.rindex("{"):r.rindex("}") + 1])


if preview:
    final = raw
else:
    n = 1 + max([int(m.group(1)) for f in glob.glob(f"{P.W}/out/{P.id}_v*_master.mp4") if (m := re.search(r"_v(\d+)_master", f))] or [0])
    master, insta = f"{P.W}/out/{P.id}_v{n}_master.mp4", f"{P.W}/out/{P.id}_v{n}_insta.mp4"
    j = loud(raw)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000")
    subprocess.run([FF, "-v", "error", "-y", "-i", raw, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", master], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", master, "-c:v", "libx264", "-preset", "slow", "-b:v", "10M", "-maxrate", "12M", "-bufsize", "20M",
                    "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", "30",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", insta], check=True)
    os.remove(raw)
    # cover still
    subprocess.run([npx, "remotion", "still", "src/index.ts", f"{P.id}-cover", f"{P.W}/out/{P.id}_cover.jpg", f"--public-dir={pub}"], cwd=REEL, check=True)
    j2 = loud(insta)
    dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", insta],
                               capture_output=True, text=True).stdout)
    lim = P.cfg.get("max_seconds", 180)
    print(f"\n{insta}\n  duration {dur:.2f}s (limit {lim}s){'  <-- TOO LONG' if dur > lim else ''}  loudness {j2['input_i']} LUFS  true-peak {j2['input_tp']} dBTP")
    final = insta
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "review.py"), str(P.dir), final,
                f"{P.W}/stills/review_{'preview' if preview else 'v' + str(n)}.jpg"], check=True)
