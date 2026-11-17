# Setup (for Claude — do this for the user, explaining each step in plain words)

Target: Windows 10/11, macOS or Linux. Disk: ~2 GB for tools + space for footage. An NVIDIA GPU is optional
(whisper transcription ~10x faster); everything works on CPU.

1. **Check what's there:** `python toolkit/py/doctor.py` (on macOS/Linux maybe `python3`). Fix only the MISSING lines.
2. **Python 3.10+** — Windows: `winget install Python.Python.3.12` · macOS: `brew install python` (or python.org).
   Then `pip install -r requirements.txt` (Windows: don't use `python -I`; packages go to the user site).
   NVIDIA GPU: also `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`.
   The first `ingest.py` run downloads the whisper large-v3 model (~3 GB) once.
3. **ffmpeg** — Windows: `winget install Gyan.FFmpeg` (not added to PATH; `toolkit/py/common.py` finds it) ·
   macOS: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg`.
4. **Node.js 18+** — Windows: `winget install OpenJS.NodeJS.LTS` · macOS: `brew install node`.
   Then `cd toolkit/reel && npm ci` (Remotion + React, exact versions from package-lock.json).
5. **Remotion agent skills (recommended):** from the repo root `npx skills add remotion-dev/skills`; they must end up
   in `.claude/skills/remotion-*`. They are API reference — the `reels` skill owns the workflow.
6. **Optional, animated reels only:** ElevenLabs API key → ask the user to paste it into the file `.secrets/elevenlabs.key`
   themselves (not into the chat). Without it anim_build makes a silent draft with estimated timing.
7. Run `doctor.py` again → `READY`. Smoke test: put 2–3 short phone videos in a folder, then
   `python toolkit/py/new_project.py test-reel "<folder>" --brand test --max 30` and follow the `reels` skill.

**Remotion licence:** free for individuals and companies with up to 3 people (commercial use included); bigger teams
need a company licence — https://www.remotion.dev/license. Music in `toolkit/music` is CC0, fonts are OFL.
