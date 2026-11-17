"""Shared paths/helpers for every toolkit script.

Every script takes the project folder as its FIRST argument (or env REEL_PROJECT):
    python toolkit/py/build.py projects/my-reel
A project folder contains project.json + edl.py; everything generated lives inside it:
    audio/ (16k wav for whisper)  a48/ (48k raw voice)  proxy/  sheets/  transcripts/  clean/
    public/ (Remotion public dir: mezz/, voice/, sfx/, fonts/, timeline.json, music_bed.wav)
    stills/ (QA images)  out/ (deliverables)
"""
import glob, importlib.util, json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root
TOOLKIT = ROOT / "toolkit"
REEL = TOOLKIT / "reel"                             # the one Remotion project (shared node_modules)
VIDEO_EXT = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts")


def _find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return Path(exe).parent
    hits = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe")))
    if hits:
        return Path(hits[-1]).parent
    sys.exit("ffmpeg not found: `winget install Gyan.FFmpeg` (it is not added to PATH automatically)")


FFBIN = _find_ffmpeg()
FF = str(FFBIN / "ffmpeg")
FFPROBE = str(FFBIN / "ffprobe")


def setup_cuda_dlls():
    """Windows: pip-installed CUDA libs (nvidia-cublas-cu12 / nvidia-cudnn-cu12) live in the USER site-packages
    and are not on the DLL path -> faster-whisper fails with 'cublas64_12.dll not found'."""
    import site
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        for b in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            if hasattr(os, "add_dll_directory"):     # Windows only; Linux finds them via the loader
                os.add_dll_directory(b)
            os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]


def ui_font():
    """Static BOLD font for QA labels (ffmpeg drawtext / PIL). Variable fonts render hairline-thin there.
    toolkit/fonts/_ui_bold.ttf if present (not shipped: licence), else a system bold font."""
    cands = [TOOLKIT / "fonts" / "_ui_bold.ttf",
             Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf",
             Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"), Path("/Library/Fonts/Arial Bold.ttf"),
             Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf")]
    for c in cands:
        if c.exists():
            return str(c)
    sys.exit("no static bold font for QA labels: put any bold .ttf at toolkit/fonts/_ui_bold.ttf")


_GPU = {}


def has_cuda():
    """NVIDIA GPU usable by faster-whisper (ctranslate2)?"""
    if "cuda" not in _GPU:
        try:
            setup_cuda_dlls()
            import ctranslate2
            _GPU["cuda"] = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            _GPU["cuda"] = False
    return _GPU["cuda"]


def whisper_model(name="large-v3", force_cpu=False):
    from faster_whisper import WhisperModel
    if not force_cpu and has_cuda():
        return WhisperModel(name, device="cuda", compute_type="float16")
    print("whisper on CPU (no CUDA GPU) — slow; ~1x realtime for large-v3", file=sys.stderr)
    return WhisperModel(name, device="cpu", compute_type="int8")


def h264_mezz_args():
    """Encoder for mezzanine files: NVENC if it actually works on this machine, else libx264 (same quality, slower)."""
    if "nvenc" not in _GPU:
        import subprocess
        r = subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2", "-c:v", "h264_nvenc",
                            "-f", "null", "-"], capture_output=True)
        _GPU["nvenc"] = r.returncode == 0
    if _GPU["nvenc"]:
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "17", "-b:v", "0", "-g", "15"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-g", "15"]


class Project:
    def __init__(self, d):
        self.dir = Path(d).resolve()
        cfg_p = self.dir / "project.json"
        if not cfg_p.exists():
            sys.exit(f"{cfg_p} missing — create the project with toolkit/py/new_project.py")
        self.cfg = json.load(open(cfg_p, encoding="utf-8"))
        self.id = self.cfg["id"]
        s = Path(self.cfg["samples"])
        self.samples = s if s.is_absolute() else (self.dir / s).resolve()
        self.prefix = self.cfg.get("clip_prefix", "")
        self.fps = self.cfg.get("fps", 30)
        self.W = str(self.dir).replace("\\", "/")          # string form used in f-strings
        self.pub = f"{self.W}/public"
        self._raw = None

    # clip id <-> files.  clip id = file stem without clip_prefix (IMG_2403.MOV with prefix "IMG_" -> "2403")
    def clips(self):
        if self._raw is None:
            self._raw = {}
            for f in sorted(self.samples.iterdir()):
                if f.suffix.lower() in VIDEO_EXT and f.stem.startswith(self.prefix):
                    self._raw[f.stem[len(self.prefix):]] = f
        return self._raw

    def raw(self, clip):
        return str(self.clips()[clip])

    def transcript(self, clip):
        return f"{self.W}/transcripts/{self.prefix}{clip}.json"

    def words(self, clip):
        p = self.transcript(clip)
        if not os.path.exists(p):
            return []
        d = json.load(open(p, encoding="utf-8"))
        return [w for s in d["segments"] for w in s["words"]]

    def edl(self):
        spec = importlib.util.spec_from_file_location("edl", self.dir / "edl.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def path(self, *parts):
        p = os.path.join(self.W, *parts).replace("\\", "/")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p


def project(argv_index=1):
    d = sys.argv[argv_index] if len(sys.argv) > argv_index and not sys.argv[argv_index].startswith("-") else os.environ.get("REEL_PROJECT")
    if not d:
        sys.exit("usage: <script> <project_dir> ...   (or set REEL_PROJECT)")
    return Project(d)
