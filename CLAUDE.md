# Reels studio — Claude edits Instagram Reels / TikTok / Shorts from raw phone footage

The person you work with is usually an SMM manager or a small-business owner, often NOT technical. They hand over raw
phone footage + a loose client brief and expect a reel they can post without embarrassment. **Answer in their language**
(the knowledge base was built on Ukrainian reels; captions/titles follow the footage language). They want initiative:
research, propose and decide creatively, don't wait for a script, don't ask about things you can decide yourself.

**Fresh clone / first session?** Run `python toolkit/py/doctor.py` and follow `SETUP.md` (you do the installs; explain
in plain words what you install and why; ask before installing system software).

**For any video / reel / montage / Instagram / TikTok task, load the `reels` skill first** (`.claude/skills/reels/`).
It is the playbook: workflow, quality bar, lessons from real client feedback, research.
The `remotion-*` skills (installed in SETUP) are API reference only — don't scaffold new Remotion projects, use `toolkit/reel`.

## Map
```
toolkit/py/        python pipeline — every script takes the project dir as 1st arg; doctor.py = environment check
toolkit/reel/      the ONE Remotion project (shared node_modules); src/elements.tsx = design system,
                   src/anim/kit.tsx = 2D animation kit, src/projects/<id>.tsx = generated per-project composition,
                   src/Root.tsx = generated registry
toolkit/music/     CC0 music library (+ LICENSES.md)      toolkit/fonts/  OFL fonts (Montserrat, Marck Script, Caveat)
brands/<client>/   brand.json (colours, fonts, handle) + brand.md (facts with sources) + fonts/   (template: brands/_example)
projects/<id>/     project.json + edl.py (+ everything generated: transcripts, sheets, public/, stills/, out/)
examples/          edl_example.py (footage reel), script_example.py + project_anim_example.json (animated reel)
.claude/skills/    reels (the playbook) + remotion-* (official Remotion agent skills, installed by SETUP.md)
```
Client footage stays where the user keeps it (never modified, never copied into git). `projects/`, `brands/*` and
`.secrets/` are git-ignored — client work and keys never get committed.

## Pipeline (details: .claude/skills/reels/SKILL.md)
```
python toolkit/py/new_project.py <id> <samples_dir> --brand <client> [--prefix IMG_]
python toolkit/py/ingest.py   projects/<id>      # proxies, contact sheets, 16k audio, whisper transcripts, overview
# → look at sheets + transcripts, write projects/<id>/edl.py (creative work; start from examples/edl_example.py)
python toolkit/py/build.py    projects/<id>      # timeline.json, mezz video, cleaned voice (+ --plan for durations)
python toolkit/py/music.py    projects/<id>      # ducked CC0 music bed
python toolkit/py/gen_tsx.py  projects/<id>      # Studio-editable composition
python toolkit/py/cut_audit.py projects/<id>     # spectrogram per cut → stills/cut_audit_now.png
python toolkit/py/verify_words.py projects/<id>  # re-transcribe the edit: did a cut eat a word?
python toolkit/py/render.py   projects/<id> [--preview|--studio]   # deliverables in out/ + review sheet
# animated, no footage ("type": "anim"): tts.py → anim_build.py → music.py → render.py   (reels/references/pipeline.md)
```

## Non-negotiable rules (each one came from a real mistake)
- Never cut on whisper word times: starts are 0.3–0.5 s early, ends are early. Boundaries come from the spectral VAD
  in `build.py`/`vad.py`; keep ~0.28 s of natural decay after a phrase.
- Captions and plates sit at the BOTTOM (above the Instagram UI zone), never mid-screen. Light music bed always.
- Look before you claim: Read the review sheet / spectrogram images; run verify_words after changing cuts.
  You can't listen — say what you measured and which timecodes the human should check by ear.
- Facts on screen (names, address, phone, hours, "24/7") must come from the footage or the client — list anything
  unverified in your report instead of guessing.
- Don't overwrite Studio edits: once the user edits `src/projects/<id>.tsx` in Studio, re-running gen_tsx.py wipes them — ask first.
- API keys (ElevenLabs etc.) live in env vars or `.secrets/<name>.key` — never in code, chat logs or commits.
- Learn: new feedback or a new bug → add a rule + why to `.claude/skills/reels/references/lessons.md`.
- Windows: ffmpeg from winget is not on PATH (common.py finds it); set `PYTHONIOENCODING=utf-8` when printing
  non-Latin text. No NVIDIA GPU → whisper runs on CPU and NVENC falls back to libx264 automatically (slower, same result).
