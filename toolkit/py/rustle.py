"""Detect & repair lavalier clothing-rub clicks/crackle (no listening needed).

Findings from spectrogram inspection of this footage:
  * rub/crackle = razor-thin vertical lines DC..19 kHz, energy collapses >12 dB within 25 ms
  * Ukrainian sibilants = 80-200 ms blobs mostly 4-12 kHz, sustain (small fall)
Detector (2.7 ms hop): fraction of 1.5-19 kHz bins jumping >12 dB in 8 ms  (broadband onset)
                       + band energy falls >=12 dB within 25 ms             (impulse, not sibilant)
Repair: spectral clamp over the ~35 ms event: each bin limited to k * per-bin median of
        surrounding unflagged frames (+-120 ms). Phase kept. Voice harmonics survive; crackle flattens.

Usage:
  python rustle.py detect <wav> [transcript.json]
  python rustle.py repair <in.wav> <out.wav>
"""
import sys, json
import numpy as np, soundfile as sf
from scipy.signal import stft, istft

NP, HOP = 512, 128


def _stft(x, sr):
    return stft(x, sr, nperseg=NP, noverlap=NP - HOP, boundary="even", padded=True)


def detect(x, sr, frac_thr=0.8, fall_thr=8.0):
    f, t, Z = _stft(x, sr)
    A = np.abs(Z)
    L = 20 * np.log10(A + 1e-9)
    band = (f >= 1500) & (f <= 19000)
    E = 10 * np.log10(np.mean(A[band] ** 2, axis=0) + 1e-18)
    lag = 3
    d = np.zeros_like(L[0]); d[lag:] = np.mean(L[band][:, lag:] - L[band][:, :-lag] > 12, axis=0)
    ev, n, k = [], len(t), lag
    fall_n = int(round(0.025 * sr / HOP))
    while k < n - fall_n - 4:
        if d[k] >= frac_thr:
            pk = E[k:k + 4].max()
            if pk - E[k + fall_n] >= fall_thr:
                ev.append(k)
                k += fall_n  # skip ahead
                continue
        k += 1
    return f, t, Z, A, ev


def repair(x, sr, k=1.3):
    f, t, Z, A, ev = detect(x, sr)
    n = len(t)
    pre, post = 3, int(round(0.08 * sr / HOP))
    flag = np.zeros(n, bool)
    for e in ev:
        flag[max(0, e - pre):min(n, e + post)] = True
    ctx = int(round(0.12 * sr / HOP))
    out = Z.copy()
    for e in ev:
        a, b = max(0, e - pre), min(n, e + post)
        lo, hi = max(0, a - ctx), min(n, b + ctx)
        ref = [j for j in range(lo, hi) if not flag[j]]
        if len(ref) < 6:
            continue
        cap = k * np.median(A[:, ref], axis=1)
        g = np.minimum(1.0, cap[:, None] / (A[:, a:b] + 1e-12))
        out[:, a:b] = Z[:, a:b] * g
    _, y = istft(out, sr, nperseg=NP, noverlap=NP - HOP, boundary=True)
    y = y[: len(x)]
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    return y.astype(np.float32), [float(t[e]) for e in ev]


if __name__ == "__main__":
    cmd = sys.argv[1]
    x, sr = sf.read(sys.argv[2], dtype="float32")
    if cmd == "detect":
        f, t, Z, A, ev = detect(x, sr)
        times = [float(t[e]) for e in ev]
        words = []
        if len(sys.argv) > 3:
            dj = json.load(open(sys.argv[3], encoding="utf-8"))
            words = [(w["s"], w["e"]) for s in dj["segments"] for w in s["words"]]
        gap = [q for q in times if not any(ws <= q <= we for ws, we in words)]
        dur = len(x) / sr
        print(f"{sys.argv[2].split('/')[-1]}: {len(times)} clicks/{dur:.0f}s ({len(times)/dur*60:.0f}/min); in gaps {len(gap)}  ::", " ".join(f"{q:.2f}" for q in times[:30]))
    elif cmd == "repair":
        y, times = repair(x, sr)
        sf.write(sys.argv[3], y, sr)
        print(f"{sys.argv[2].split('/')[-1]}: repaired {len(times)} clicks")
