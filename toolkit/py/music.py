"""Background music bed, auto-ducked under the voice.
Track: FreePD "City Sunshine" (CC0 / public domain — commercial use OK, no attribution needed).
Usage: python music.py <project_dir> [track.mp3]   (run after build.py; reads clean/master_raw.wav for the voice envelope)
Default track = project.json "music". CC0 library + licences: toolkit/music/LICENSES.md
"""
import sys, subprocess, json, os
sys.path.insert(0, os.path.dirname(__file__))
from common import project, FF, ROOT
import numpy as np, soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d

P = project()
W = P.W
SR = 48000
track = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / P.cfg["music"])
BED_LUFS = -21      # music level when nobody speaks (hook, pauses, end card)
DUCK_DB = -11       # extra attenuation under speech  -> ~-32 LUFS bed vs -16 voice

voice, _ = sf.read(f"{W}/clean/master_raw.wav", dtype="float32")
n = len(voice)
tmp = f"{W}/clean/music_norm.wav"
subprocess.run([FF, "-v", "error", "-y", "-i", track, "-ac", "2", "-ar", str(SR),
                "-af", f"loudnorm=I={BED_LUFS}:TP=-3:LRA=11", tmp], check=True)
m, _ = sf.read(tmp, dtype="float32")
if len(m) < n:  # loop if the track is shorter than the reel
    m = np.concatenate([m] * (n // len(m) + 1))
m = m[:n]

# voice activity envelope (10 ms hops)
h = SR // 100
k = n // h
r = np.sqrt(np.mean(voice[: k * h].reshape(k, h) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(r)
sel = db[db > -90]                                   # silent voice (anim draft without TTS) -> no ducking
active = (db > np.percentile(sel, 30)).astype(float) if len(sel) else np.zeros_like(db)
active = maximum_filter1d(active, size=45)          # hold 450 ms so it doesn't pump between words
g_db = DUCK_DB * active
g_db = uniform_filter1d(g_db, size=25)              # ~250 ms smooth attack/release
g = 10 ** (np.repeat(g_db, h) / 20)
g = np.pad(g, (0, n - len(g)), mode="edge")
# fades: 0.6 s in, 2.5 s out
fi, fo = int(0.6 * SR), int(2.5 * SR)
g[:fi] *= np.linspace(0, 1, fi)
g[-fo:] *= np.linspace(1, 0, fo) ** 1.5
bed = m * g[:, None]
sf.write(f"{P.pub}/music_bed.wav", bed.astype(np.float32), SR)
print(f"music bed {n/SR:.1f}s, ducked {active.mean()*100:.0f}% of the time -> public/music_bed.wav")
