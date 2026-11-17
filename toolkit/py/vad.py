"""Spectral voice-activity tracking on the RAW lav track (<project>/a48/{clip}.wav). Call vad.use(project) first.

Idea: estimate the clip's own noise floor per frequency bin (room tone, HVAC hum, mic hiss),
then measure how much energy sits ABOVE that floor in the speech band (90 Hz – 8 kHz) every 10 ms.
Soft endings ("-ть", "-сь", breathy vowels) are quiet in RMS but clearly above the floor in their
own bands, so they are kept; constant background noise is subtracted away, so it is not mistaken for voice.

voice(clip) -> dict(t, rel, thr, active, S, f)
  rel    : dB of above-floor speech energy relative to the clip's loud-speech level (0 = loud speech)
  active : rel > thr (with a short hangover)
voice_off(clip, t0, hold)  -> first time >= t0 where voice has been silent for `hold` s
voice_on(clip, t1, lookback) -> true onset of the phrase that whisper says starts at t1
"""
import os, subprocess
import numpy as np, soundfile as sf
from scipy.ndimage import uniform_filter1d

from common import FF
P = None   # set by use(project) before anything else


def use(project):
    global P
    P = project
    _cache.clear()

SR, NFFT, HOP = 48000, 2048, 480          # 10 ms hop, 43 ms window
F_LO, F_HI = 90, 8000
NOISE_PCT = 10                             # per-bin noise floor percentile
OVER = 2.0                                 # energy must exceed 2x (3 dB) the floor to count
NOISE_REL_PCT, MARGIN = 10, 8.0             # per clip: pause level = 10th pct of rel; voice = pause level + 8 dB
THR_MIN, THR_MAX = -40.0, -20.0

_cache = {}


def _load(clip):
    p = P.path("a48", f"{clip}.wav")
    if not os.path.exists(p):
        subprocess.run([FF, "-v", "error", "-y", "-i", P.raw(clip),
                        "-vn", "-ac", "1", "-ar", str(SR), p], check=True)
    x, _ = sf.read(p, dtype="float32")
    return x


def voice(clip):
    if clip in _cache:
        return _cache[clip]
    x = _load(clip)
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(NFFT).astype(np.float32)
    S = np.abs(np.fft.rfft(x[idx] * win, axis=1)) ** 2          # (frames, bins) power
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    band = (f >= F_LO) & (f <= F_HI)
    Sb = S[:, band]
    N = np.percentile(Sb, NOISE_PCT, axis=0)                     # noise floor per bin
    resid = np.clip(Sb - OVER * N, 0, None).sum(axis=1)
    sc = 10 * np.log10(resid + 1e-12)
    sc = uniform_filter1d(sc, 3)
    ref = np.percentile(sc, 95)
    rel = np.maximum(sc - ref, -80)
    t = (np.arange(n) * HOP + NFFT / 2) / SR                     # frame centre times
    thr = float(np.clip(np.percentile(rel, NOISE_REL_PCT) + MARGIN, THR_MIN, THR_MAX))
    active = rel > thr
    _cache[clip] = dict(t=t, rel=rel, thr=thr, active=active, S=S, f=f, x=x)
    return _cache[clip]


def _i(v, tt):
    return int(np.clip(np.searchsorted(v["t"], tt), 0, len(v["t"]) - 1))


def voice_off(clip, t0, hold=0.12, limit=3.0):
    """first time >= t0 at which the voice has been below threshold for `hold` seconds"""
    v = voice(clip)
    k, kend, h = _i(v, t0), _i(v, t0 + limit), int(round(hold * 100))
    while k < kend:
        if not v["active"][k:k + h].any():
            return float(v["t"][k])
        k += 1
    return None


def voice_on(clip, t1, lookback=0.6):
    """walk back from t1 to where the voice actually starts (onset of breath / first consonant)"""
    v = voice(clip)
    k, kmin = _i(v, t1), _i(v, t1 - lookback)
    # if whisper's start is in silence, step forward to the first active frame first
    while k < len(v["t"]) - 1 and not v["active"][k] and v["t"][k] < t1 + 0.3:
        k += 1
    while k > kmin and v["active"][k - 1]:
        k -= 1
    return float(v["t"][k])


def is_active(clip, t, win=0.05):
    v = voice(clip)
    return bool(v["active"][_i(v, t - win):_i(v, t) + 1].any())


def next_active(clip, t, limit=3.0):
    """first time >= t at which the voice is active again (the next real onset)"""
    v = voice(clip)
    k, kend = _i(v, t), _i(v, t + limit)
    while k < kend and not v["active"][k]:
        k += 1
    return float(v["t"][k]) if k < kend else t + limit


def dip(clip, t0, t1, last=False, depth=12.0):
    """a natural cut point inside running speech: the first (or last) local energy minimum in [t0,t1]
    that comes close to silence (< thr + depth dB); falls back to the quietest point in the window"""
    v = voice(clip)
    k0, k1 = _i(v, t0), _i(v, t1)
    if k1 <= k0:
        return t0
    r = v["rel"]
    ks = [k for k in range(max(k0, 1), min(k1, len(r) - 1) + 1)
          if r[k] <= r[k - 1] and r[k] <= r[k + 1] and r[k] < v["thr"] + depth]
    if ks:
        return float(v["t"][ks[-1] if last else ks[0]])
    return float(v["t"][k0 + int(np.argmin(r[k0:k1 + 1]))])
