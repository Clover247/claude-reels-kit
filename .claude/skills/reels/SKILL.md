---
name: reels
description: Playbook for editing Instagram Reels / TikTok / Shorts from raw phone footage in this repo (ingest, transcription, edit decision list, captions, kinetic titles, transitions, B&W live moments, music, lav-mic rustle repair, Remotion Studio, QA, Instagram export). Use for ANY request to edit, cut, montage, subtitle, re-time, re-render or fix a video/reel ("змонтуй", "рілс", "відео", "субтитри", "переходи", "обрізається фраза", "музика", "відрендери"), and before touching toolkit/ or projects/.
---

# Reels playbook

**This skill owns the workflow.** The bundled `remotion-*` skills are API reference only: never scaffold a new
Remotion project (`create-video`, remotion-create) — use `toolkit/reel`; never skip rendering — `render.py` is how we deliver.

Goal: from raw footage + a vague brief, deliver a reel the owner can post without embarrassment — and that a client
pays for. Quality bar and the reasons behind every rule are in `references/`. Read what you need:

| file | read when |
|---|---|
| `references/lessons.md` | ALWAYS before editing — owner feedback and bugs already paid for |
| `references/creative.md` | planning the story/edit (structure, pacing, text styles, transitions, B&W, hook, end card) |
| `references/pipeline.md` | running/changing the toolkit, edl.py schema, timeline format, adding components |
| `references/quality.md` | before delivering — the QA checklist and how to verify each item |
| `references/remotion.md` | Studio visual editing, Remotion licence, API gotchas |
| `references/research.md` | tool landscape, Instagram specs, music sources, what was evaluated and rejected |

## Workflow

1. **Brief** — collect: client, goal of the reel, must-say facts (names, address, phone, hours), max length,
   brand (colours/fonts/handle → `brands/<client>/brand.json`), reference reels. Missing facts are not a blocker:
   proceed, and list open questions in the report. Don't ask about things you can decide yourself.
2. **New project** — `python toolkit/py/new_project.py <id> "<samples_dir>" --brand <client> [--prefix IMG_] [--max 60]`
   (Git Bash: quote Windows paths / use forward slashes). Fill `project.json` now: `whisper_prompt` (names, brand
   and topic terms improve recognition), `max_seconds` (from the brief), `music`. Write the brief verbatim into
   `projects/<id>/NOTES.md`. `labels` and `cover` come after the edit (cover clip must be a clip used in the edit;
   empty = first spoken shot).
   Same client again → reuse `brands/<client>/` and read its `brand.md` (verified/unverified facts).
   "Like the previous reel" → the latest delivered version listed in that project's NOTES.md.
3. **Ingest & research the footage** — `python toolkit/py/ingest.py projects/<id>`. Then actually LOOK:
   Read every `sheets/*.jpg` and skim every transcript. Classify clips: talking (A-roll, has speech),
   b-roll (equipment, rooms, animals, details), hook candidates (most striking 0.5 s moments), live moments
   (unscripted, warm — candidates for B&W). Group by topic/room; decide the story order (`references/creative.md`).
   Ingest warns about HDR clips (auto-tonemapped), landscape clips (blur-fit, or `"fit": {clip: "crop"}`) and
   files it skipped (wrong prefix, photos). Check monitors/papers in shot for private data (owner/patient names).
4. **Write `projects/<id>/edl.py`** — copy the structure of `examples/edl_example.py`. Ranges are source
   seconds from transcripts; rough is fine (the build snaps to the real voice). Use `python toolkit/py/build.py
   projects/<id> --plan` to iterate on duration (Instagram Reels ≤ 3:00; aim for the brief).
5. **Build** — `build.py` → `music.py` → `gen_tsx.py`. Caches: mezz/ and clean/ are reused if present —
   after changing the grade/geometry or replacing a source file run `build.py <p> --fresh`.
   If the owner edited the composition in Studio, gen_tsx.py would overwrite it — copy the .tsx first and ask
   (or commit it first).
6. **Verify the cuts** — `cut_audit.py` (Read `stills/cut_audit_now.png`) and `verify_words.py`. A missing/garbled
   word "AT CUT" = suspect; confirm by transcribing an isolated snippet before changing anything (whole-reel
   whisper has false alarms). Fix by changing the EDL range, not by hand-tuning frames.
7. **Preview & self-review** — `python toolkit/py/render.py projects/<id> --preview`, Read `stills/review_preview.jpg`,
   go through `references/quality.md`. Fix, repeat.
8. **Deliver** — `render.py projects/<id>` (full res, −14 LUFS, 10 Mbps insta file, cover jpg, review sheet).
   Report in Ukrainian: file paths, what changed, what to check by ear (timecodes of tight cuts), open questions
   (unverified facts), how to tweak in Studio (`render.py ... --studio`). Cite web sources if you researched.
9. **Notes** — update `projects/<id>/NOTES.md`: version, what changed, open questions, delivered file names.
10. **Learn** — new owner feedback or a new bug → add it to `references/lessons.md` (rule + why) so the next session
   doesn't repeat it. New research → `references/research-*.md`. Keep CLAUDE.md short; details go here.

## Defaults that already worked (change only with a reason)
- 1080x1920, 30 fps; grade `eq=contrast=1.05:saturation=1.07:gamma=0.98,unsharp=5:5:0.35`; punch-in zoom 1.12
  alternating on every jump cut; transitions whip / zoom / flash between topics, plain cut inside a topic.
- Hook: 5–7 shots × 0.6 s with a kinetic title (`HOOK = None` → voice-first opening, often better ≤ 60 s);
  end card 3.6 s with name / address / phone / handle. Short reels: see "Short form" in creative.md.
- Captions: ≤3 words / 22 chars per page, active word in brand accent, Montserrat 700 58 px, bottom (top=1470);
  hidden while a big kinetic title is on screen. Plates (name / address / section tags) at bottom 470 px.
- Voice: rustle repair → highpass 85 → afftdn → de-esser → gentle compressor; per-clip loudnorm −16.
  Music: CC0 bed at −21 LUFS, ducked −11 dB under speech, 0.6 s fade-in / 2.5 s fade-out. Master −14 LUFS.
- Renders: full ≈ 10 min, preview (half-res) ≈ 5–7 min — run them in the background.
