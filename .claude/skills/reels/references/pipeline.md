# Toolkit internals

## Data flow
```
samples/*.MOV ──ingest.py──> proxy/ sheets/ audio/(16k) transcripts/ clips.json
edl.py + transcripts + raw audio ──build.py──> public/timeline.json, public/mezz/<clip>.mp4 (1080x1920 graded, nvenc cq17 g15),
                                               clean/<clip>.wav (rustle-repaired + denoised), clean/master_raw.wav, public/sfx/
clean/master_raw.wav ──music.py──> public/music_bed.wav (ducked)
timeline.json ──gen_tsx.py──> toolkit/reel/src/projects/<id>.tsx + src/Root.tsx, public/voice/<clip>.wav (−16 LUFS),
                              public/fonts/, public/cover_bg.jpg
remotion (toolkit/reel, --public-dir=projects/<id>/public) ──render.py──> out/<id>_vN_master.mp4, _insta.mp4, _cover.jpg
```
`common.py`: `project()` loads `projects/<id>/project.json`; `P.raw(clip)`, `P.words(clip)`, `P.edl()`, `P.path(...)`;
`FF/FFPROBE` (winget ffmpeg), `setup_cuda_dlls()`. Clip id = file stem minus `clip_prefix` (IMG_2403.MOV → "2403").

## Footage handling (build.py `mezz_filter`)
- iPhone HDR (HLG / Dolby Vision, PQ) is detected from `color_transfer` and tonemapped to SDR bt709 (zscale + hable).
- Geometry uses the displayed orientation (rotation metadata). Portrait → scale; landscape/square → whole frame over a
  blurred fill (default) or centre crop via project.json `"fit": {"<clip>": "crop"}`.
- Caches: public/mezz/, clean/, public/voice/ (re-made when clean/ is newer), public/cover_bg.jpg (re-made when the
  cover clip/at changes). `build.py <p> --fresh` re-makes mezz + clean.
- ingest.py lists skipped files (non-video, wrong prefix). Photos: convert to a short clip with ffmpeg if needed.

## project.json
id (= Remotion composition id), title, client, brand (path to brand.json), samples (abs path), clip_prefix, fps,
language, whisper_prompt, max_seconds, fit {clip: crop|blur}, music (path from repo root), labels {clip: name in Studio},
cover {clip, at, title, script, line} (clip must be used in the edit; empty → first spoken shot).

## edl.py schema (source seconds)
`HOOK = dict(shots=[(clip, t)], shot_dur=0.6, title=dict(kind="kinetic", lines=[(text, "bold"|"script")]))` or `HOOK = None` (voice-first)
`BLOCKS = [dict(clip, ranges=[(a,b)], trans="cut|whip|zoom|flash", section=str, broll=[(clip, src_in, dur, at_src)],
texts=[dict(kind="kinetic"|"lower3"|"pin"|"tag", at=src_t, dur=s, ...)], bw=[(a,b)])]`
`END = dict(clip, src, dur, title, sub, lines=[3], handle)`; `FIX = {whisper_word: correct}`.

## build.py — how boundaries are decided (the part the owner cares most about)
1. `natural_bounds(clip, a, b)` per EDL range, using `vad.py` (spectral VAD on raw 48k audio: per-bin noise floor
   10th pct, energy above 2× floor in 90 Hz–8 kHz, threshold = clip's pause level + 8 dB, clamped −40…−20 dB):
   - words "inside" = whisper start in [a−0.05, b−0.12)
   - END: decay after the last word (`voice_off`, 120 ms hold) → end = decay + 0.28 s, but ≤ next onset − 0.06.
     If there is no decay before the next word (running speech) → first near-silent dip (`vad.dip`), `tight_out`.
   - START: next onset after the previous word decays − 0.12 s, never before that decay + 0.04; else last dip, `tight_in`.
   - ranges touching (≤0.06 s) → joined exactly (visual split only).
2. `tighten()` splits inner pauses > 0.5 s (VAD), keeping 0.32 s after / 0.15 s before the voice.
3. Tight cuts are quantised to frames away from the neighbouring word (ceil start / floor end).
Tunables at the top of build.py: GAP_MAX, PAD_PRE, PAD_POST, TAIL_MAX, TAIL, PRE_ROLL.

## timeline.json (frames)
main[] {clip, src, frm, dur, zoom, bw, hook?, end?, tight_in, tight_out, rng, piece}; broll[] {clip, src, frm, dur};
texts[] {kind, frm, dur, ...}; transitions[] {at, kind}; sfx[] {kind, at}; captions[] (legacy); durationInFrames.

## Remotion side (toolkit/reel/src)
- `elements.tsx` — design system, all `Interactive.create` (Studio-editable): Shot (src, zoom, bw, transIn/Out),
  Captions (captionsSchema; times are SOURCE ms of the shot's clip), Kinetic (bold, script, scriptDelay, centered),
  Card (title, sub, pin), Tag (text, variant section|left|right), EndCard, Flash, Voice (src, fadeIn, fadeOut, gain),
  CoverCard. `<Brand value={brand}>` provides colours {dark, mid, accent, pale, light} + fonts and waits for font load.
- `useShotClock()`: inside a Sequence with trimBefore, local = frame + `Internals.SequenceContext.cumulatedNegativeFrom`.
- Generated `projects/<id>.tsx` exports `meta`, `brand`, `<PascalId>` component, `Cover`. Tracks: Кадри, B-roll,
  Великі титри, Плашки, Фінальна картка, Спалахи, Музика, SFX.
- New visual element → add an Interactive component to elements.tsx (accept `style` prop if layout "none"),
  emit it from gen_tsx.py, `npx tsc --noEmit`, check a still: `npx remotion still src/index.ts <id> x.jpg --frame=N --public-dir=...`.

## QA tools
`cut_audit.py <p> [tag]` table + spectrogram sheet; `verify_words.py <p>` re-transcription diff; `review.py <p> <video> <out.jpg> [frames]`;
`music_probe.py [dir]` tempo/brightness/steadiness of candidate tracks; `click_probe.py <wav> t…` rustle feature at given times.

## Speech-to-text / text-to-speech — pluggable
- STT for `ingest.py` / `verify_words.py`: `--stt whisper|deepgram` or project.json `"stt"`; default auto = whisper
  on an NVIDIA GPU, Deepgram when there is no GPU but a key, else whisper on CPU. Both write the same transcript format
  (`transcripts/<stem>.json`: segments → words {w, s, e, p}); `"keyterms": [...]` in project.json boosts brand words
  on Deepgram nova-3 (whisper uses `whisper_prompt`). `stt.py` = the Deepgram client (key: env DEEPGRAM_API_KEY or
  `.secrets/deepgram.key`).
- Any other service (AssemblyAI, OpenAI, Google, Azure, local models…) = add a function to `stt.py` returning that same
  segment format and a branch in `stt.engine` — the rest of the pipeline doesn't care. Same for TTS: `tts.py` writes
  `tts/<line>.mp3` + `.json` {chars, starts, ends}; another provider only has to produce that.
- Cut points never come from any ASR (they come from `vad.py`), so switching STT doesn't change where the edit cuts.

## Animated projects — no footage (project.json `"type": "anim"`)
For faceless 2D explainers (e.g. a winter how-to series for an HVAC company).
```
script.py (LINES: id, text with caption markup, gap)  ──tts.py──> tts/<line>.mp3 + .json (ElevenLabs character alignment, cached)
script.py + tts/ ──anim_build.py──> public/vo.wav, clean/master_raw.wav, public/sfx/, public/fonts/, public/timeline.json,
                                    src/projects/<id>.data.ts (line/word frames + caption pages), src/Root.tsx
music.py (ducks under vo) → render.py (same as footage projects; composition + <id>-cover)
```
- Markup: `*warm*` `_cold_` `!danger!` `~ok~` colour a caption word once spoken; `{HEAT|хіт}` = show | say (pronunciation).
- No ElevenLabs key → anim_build ESTIMATES timing (≈2.7 words/s) and writes silent vo; the episode shows a red "ЧЕРНЕТКА" tag.
  Key lives in env ELEVENLABS_API_KEY or `.secrets/elevenlabs.key` (never in chat/code). `tts.py <p> --voices`, `--audition id…`.
- Line clips are cut from the first character −0.06 s to the measured energy decay +0.15 s (not to the alignment end).
- Episode .tsx is HAND-WRITTEN: cues = `W(lineId, "wordfragment")` → frame, so re-voicing re-times every animation.
  No `<Sequence>` around visuals (kit components use absolute frames); Sequences only for audio.
- Kit `toolkit/reel/src/anim/kit.tsx`: Room (wall/door/window with snow, frost, tape, drafts/lamp/sofa), Person (sit↔stand,
  shiver, cold glow, breath, hug, mug, walk), Blanket, Heater, AcUnit, Remote, HeatPumpDiagram, StatusBar, StepPill, Callout
  (screen-space box + dashed leader to a world point via `toScreen(cam, x, y)`), Chip, Captions (karaoke pages), Flash, camera `camAt`.
- Example script: `examples/script_example.py`. Series pieces for episodes 2+: `toolkit/reel/src/anim/series_<name>.tsx`. Fast QA: `python toolkit/py/anim_qa.py <p> [frames…]` → stills/qa_sheet.jpg.
- QA: render --preview, then a 1 fps contact sheet (ffmpeg fps=1,tile=8x2) and read it; full-res `remotion still --frame=N` for detail.
