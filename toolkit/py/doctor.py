"""Environment check for a fresh machine. Usage: python toolkit/py/doctor.py
Prints OK / MISSING for everything the pipeline needs and how to fix it. Changes nothing."""
import importlib, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ok = True


def line(good, what, fix=""):
    global ok
    ok &= bool(good) or what.startswith("(optional)")
    print(("OK       " if good else "MISSING  ") + what + ("" if good or not fix else f"\n         -> {fix}"))


line(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (need 3.10+)", "install Python 3.11+ from python.org")
for mod, pipname in [("numpy", "numpy"), ("scipy", "scipy"), ("soundfile", "soundfile"), ("PIL", "pillow"),
                     ("matplotlib", "matplotlib"), ("faster_whisper", "faster-whisper")]:
    try:
        importlib.import_module(mod); line(True, f"python package {pipname}")
    except Exception:
        line(False, f"python package {pipname}", "pip install -r requirements.txt")
try:
    importlib.import_module("librosa"); line(True, "(optional) librosa — music_probe.py")
except Exception:
    line(False, "(optional) librosa — music_probe.py", "pip install librosa")

try:
    sys.path.insert(0, str(Path(__file__).parent))
    import common
    line(True, f"ffmpeg at {common.FFBIN}")
    line(True, f"QA label font {common.ui_font()}")
    cuda = common.has_cuda()
    line(cuda, "(optional) NVIDIA CUDA for whisper — without it transcription runs on CPU (slower, same result)",
         "NVIDIA GPU: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
    nv = "h264_nvenc" in common.h264_mezz_args()
    line(nv, "(optional) NVENC video encoder — without it libx264 is used (slower, same quality)")
except SystemExit as e:
    line(False, f"ffmpeg / fonts: {e}", "Windows: winget install Gyan.FFmpeg | macOS: brew install ffmpeg | Linux: apt install ffmpeg")

node = shutil.which("node")
line(node, "Node.js (Remotion)", "install Node.js LTS from nodejs.org")
if node:
    v = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    line(int(v.lstrip("v").split(".")[0]) >= 18, f"Node {v} (need 18+)", "update Node.js LTS")
line((ROOT / "toolkit/reel/node_modules/remotion").exists(), "Remotion installed (toolkit/reel/node_modules)",
     "cd toolkit/reel && npm ci")
line(any((ROOT / ".claude/skills").glob("remotion-*")), "(optional) official Remotion agent skills in .claude/skills",
     "from the repo root: npx skills add remotion-dev/skills  (they must end up in .claude/skills/remotion-*)")
line((ROOT / ".secrets/deepgram.key").exists() or bool(__import__("os").environ.get("DEEPGRAM_API_KEY")),
     "(optional) Deepgram key — cloud speech-to-text (recommended without an NVIDIA GPU)",
     "sign up at deepgram.com (free credit), put the key into .secrets/deepgram.key (never into chat or code)")
line((ROOT / ".secrets/elevenlabs.key").exists() or bool(__import__("os").environ.get("ELEVENLABS_API_KEY")),
     "(optional) ElevenLabs key — only for animated reels with AI voice-over",
     "put the key into .secrets/elevenlabs.key (never into chat or code)")
print("\nREADY" if ok else "\nFix the MISSING lines above, then run this again.")
