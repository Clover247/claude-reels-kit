# Lessons learned (rule — why). Add new ones at the bottom of the right section.

## Owner / client feedback (highest priority)
- **Hold 0.5–1 s after a phrase ends; never cut while the speaker is still finishing.** v1 cut on whisper word ends
  and the owner heard words being chopped. Now: spectral VAD finds the real decay, +0.28 s tail, never into the next
  word; in running speech cut in the first near-silent dip and use a 1-frame audio fade (`build.py natural_bounds`).
- **Track the raw voice, not the transcript** (owner's own idea): "see where the frequencies dropped and at
  which timecode, then add a few tenths of a second". That is exactly `vad.py` + `cut_audit.py`.
- **Captions and context plates at the bottom of the screen**, not in the middle (owner sent screenshots).
  Keep them above the Instagram UI zone (bottom ~420 px): captions top=1470, plates bottom=470.
- **Always a light music bed** — silence or bare room noise is distracting. CC0 track, ducked under the voice.
- Client brief wording to expect: "гарні переходи", "скоротити до 3 хв", "написи (вулиця, імена лікарів)",
  "живі моменти в ч/б", "мікрофон потерся об одяг — видалити або виправити".
- Owners usually want proactive research and creative initiative, not a list of questions.

## Whisper / timing
- Whisper word STARTS are 0.3–0.5 s early (e.g. "Отже," whisper 0.72 s, real onset 1.08 s); ENDS are early too; one word
  can be stretched over a whole pause ("стерилізатор," 2.3 s). Never use whisper times as cut points.
- A word whisper places in the last 0.12 s of an EDL range is the NEXT sentence ("Також", "тому", "Це") — exclude it.
- Captions: assign each word to exactly one shot by its start; filter by the EDL range intent, not by midpoint
  (midpoint rule produced a stray "Тут" caption for a word cut off in the audio).
- Whole-reel re-transcription gives false alarms ("адміністрат." while the snippet alone is recognised fine) —
  confirm any suspect with an isolated snippet before changing the edit.
- faster-whisper + PyAV 19: pass numpy audio (soundfile), not a path. Windows CUDA DLLs: `common.setup_cuda_dlls()`.
- `initial_prompt` with brand names/terms improves recognition; still keep a FIX dict for brand spellings (IDEXX, SDMA, T4).

## Audio
- Fixed VAD threshold failed: street/clinic noise sits ~30 dB under speech and is non-stationary. Use per-clip
  per-bin noise floor + threshold = clip pause level + 8 dB.
- Ranges that (almost) touch (≤0.06 s) are one take split for a visual change (B&W, punch-in) → join audio exactly;
  processing both edges removed 0.13 s mid-word (a name lost its middle syllable).
- Lav rustle: detect impulse clicks (broadband onset + fast decay) and clamp spectrally; sibilants must be left alone
  (first detector flagged "с/ш"). Sustained rub under speech can't be fixed → choose other takes or cover with music.
- 4-frame fade on a cut placed in running speech eats the last syllable → 1 frame there; 4 only where the voice decayed.

## Visual / Remotion
- Scaling the active caption word eats the inter-word gap → flex gap + colour-only highlight.
- Tags/plates and B-roll must be clamped to their block end (they spilled into the next scene / covered transitions).
- Whip transition showed black edges → smaller translate + scale-up.
- A caption page lingers until the next page → it showed under big titles. Page lifetime = last word + 0.5 s,
  and words starting ≤0.4 s before a title are dropped, others end before the title.
- `trimBefore` inside a `<Still>` was ignored → cover background is an extracted jpg.
- Variable fonts (Montserrat[wght]) render hairline-thin in ffmpeg drawtext/PIL → `_ui_bold.ttf` for QA labels.
- Interactive.create: number schema fields need `hiddenFromList`; components with layout "none" must accept `style`.
- Studio visual editing needs flat JSX with inline literal props (that's why gen_tsx emits long flat files).

## Facts & honesty
- Door sign showed 10:00–20:00 while the brief said "24/7" → end card says "цілодобовий стаціонар"; flag such conflicts.
- An address heard only in the voice-over (whisper text) → list as "to verify" until the client confirms.
- Only one doctor is named in the footage; don't invent other names — ask.
- You cannot listen: say what was verified by measurement vs what the owner should check by ear.

## Environment
- Windows 11, Git Bash + PowerShell. ffmpeg via winget, not on PATH. Python 3.14, user site-packages (don't use `-I`).
- `PYTHONIOENCODING=utf-8` for Ukrainian output. A folder that is the session cwd can't be moved (Windows lock).
- Full render ≈ 10 min, writes ~400 MB master; previews at --scale=0.5.

## Animated explainers (first one: an HVAC company's winter series)
- A reference that is fully animated (AI 2D explainer, no footage) → build it in Remotion code with the anim kit, voice via TTS.
  TTS = ElevenLabs (owner picks the voice by ear from auditions). Ask before installing new packages.
- React hooks (usePop/useCurrentFrame) must run BEFORE any conditional `return null` — otherwise the render crashes mid-way
  ("Rendered more hooks…"); 6-frame test renders don't catch it, a full preview does.
- A front-view seated character reads as standing unless the thighs are drawn as a lap block over the hips and the hips sit low.
- Camera push-ins bring scene content into the caption zone → always a dark gradient band behind captions (y≥1180).
- Never leave a 1–2 letter word («в», «з», «й», «по») at the end of a caption page (anim_build paging rule).
- White ground (snow) under captions killed contrast — keep everything below y≈1120 dark in diagrams.
- Facts the voice-over implies but doesn't state (COP "кілька кіловат") → show a conservative range with a footnote
  ("3–4 кВт* · залежить від моделі та температури надворі") and list it as [перевірити] for the client.
- Camera framing in anim rooms: the wall AC must stay under the status bar / step pill (screen y ≥ 250):
  cy ≤ acTop + 400/s. Push-ins that break this hide the AC behind the HUD (seen in ep2/ep4 first drafts).
- Deepgram drops the first short word of an isolated TTS clip («Крок», «Дме», «А») — pad 0.8 s of silence before judging;
  a word still missing after padding = real TTS glitch → regenerate that line (delete tts/<line>.* or tweak punctuation).
- A rotated AcUnit flap at 0.8–1.0 reads as a stick across the room — keep flap ≈ 0.35 in room shots.
- A series: put pieces shared by episodes 2+ (cues, end card, cards, badges) in `toolkit/reel/src/anim/series_<name>.tsx`. Quick visual QA without a full render: `python toolkit/py/anim_qa.py <p>`
  (0.4-scale silent render + labelled sheet, 3 frames per line) ≈ 1–2 min.

