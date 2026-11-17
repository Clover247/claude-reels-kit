"""Compare candidate music tracks (tempo, brightness, energy steadiness, harmonic ratio). Usage: python music_probe.py [dir]"""
import sys, glob, numpy as np, librosa, warnings
warnings.filterwarnings("ignore")
for f in sorted(glob.glob((sys.argv[1] if len(sys.argv) > 1 else "toolkit/music") + "/*.mp3")):
    y, sr = librosa.load(f, sr=22050, mono=True)
    dur = len(y)/sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]; db = 20*np.log10(rms+1e-9)
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    # energy over time in 10 chunks (dB) -> steadiness
    ch = [float(np.mean(db[i*len(db)//10:(i+1)*len(db)//10])) for i in range(10)]
    # vocal-ish presence proxy: harmonic ratio
    h, p = librosa.effects.hpss(y)
    hr = float(np.sum(h**2)/(np.sum(y**2)+1e-9))
    print(f"{f.replace(chr(92),"/").rsplit("/",1)[-1]:28s} {dur:5.0f}s tempo {float(np.atleast_1d(tempo)[0]):5.0f} centroid {np.median(cent):5.0f}Hz onsets {np.mean(onset):.2f} harm {hr:.2f} energy-span {max(ch)-min(ch):4.1f}dB  curve {' '.join(f'{c:.0f}' for c in ch)}")
