import sys, numpy as np, soundfile as sf
from scipy.signal import stft
def feat(path):
    x, sr = sf.read(path, dtype='float32')
    f, t, Z = stft(x, sr, nperseg=256, noverlap=256-120, boundary=None)  # 2.5ms hop, 5ms win
    L = 20*np.log10(np.abs(Z)+1e-9)
    band = (f>=1500)&(f<=19000); lo=(f>=1500)&(f<4000); hi=(f>=12000)&(f<=19000)
    d = L[:, 3:] - L[:, :-3]            # jump vs 7.5ms earlier
    frac = np.mean(d[band] > 12, axis=0)
    rise_lo = np.mean(d[lo],axis=0); rise_hi=np.mean(d[hi],axis=0)
    return t[3:], frac, rise_lo, rise_hi
t, frac, rl, rh = feat(sys.argv[1])
for q in map(float, sys.argv[2:]):
    i0 = np.searchsorted(t, q-0.06); i1 = np.searchsorted(t, q+0.06)
    k = i0 + np.argmax(frac[i0:i1])
    print(f"{q:7.2f}: peak frac={frac[k]:.2f} at {t[k]:.3f}  riseLo={rl[k]:.1f}dB riseHi={rh[k]:.1f}dB")
