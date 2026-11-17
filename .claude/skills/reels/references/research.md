# Reels research & conclusions (Nov 2026)

Context: the first project was a ~3-min vet-clinic tour reel in Ukrainian, cut for Instagram from raw iPhone footage for an SMM agency client. Alongside the edit, Claude was asked to research online how people edit video with Claude, because Claude's built-in knowledge may be outdated. The research was done 2026-11-15 → 2026-11-17.

Everything below was either fetched from the web during that work (cited with links) or measured or observed on the working machine. Items marked **(unverified)** came from Claude's memory, a secondary blog, or a guess.

Scripts: `python toolkit/py/<script>.py projects/<id>`.

---

## 0. TL;DR — what to reuse

| Area | Decision |
|---|---|
| Pipeline | Python EDL → `build.py` (pause tightening from raw audio, mezzanine files, cleaned voice, SFX) → `gen_tsx.py` (flat, Studio-editable Remotion JSX) → `remotion render` → ffmpeg 2-pass loudnorm → 10 Mbps H.264 for Instagram. |
| "Seeing" footage | Transcript with word timestamps first. Then contact sheets (ffmpeg `tile`) and spectrograms. A review sheet of every render at text and transition frames. This is the same pattern used by video-use and reelsmith. |
| Transcription | faster-whisper 1.2.1, `large-v3`, CUDA float16, `language="uk"`, `word_timestamps=True`, VAD on, plus an initial prompt with brand words. **Never cut on whisper times**: word starts come 0.3–0.5 s early and word ends are too early. |
| Cut points | Spectral VAD on the raw lav track (`vad.py`). End = voice decay + 0.28 s. In running speech, cut at the first near-silent dip between words. |
| Rustle | No free dedicated tool exists. Use the own impulse-click detector plus a spectral clamp (`rustle.py`). Then `highpass=85, afftdn, deesser, acompressor`. Sustained rub under speech can't be fixed for free. |
| Remotion | 4.0.543. Licence note: Remotion is free for individuals/teams ≤3 (when the client receives only the MP4, only the agency's headcount counts). Official agent skills are installed. Write flat JSX with `Interactive.create` components so the user can edit in Studio. |
| brag / Hyperframes | Don't use for camera footage. brag makes ~20 s launch videos of web projects. |
| Music | FreePD (CC0) via the mirror en.freepd.cn. Chosen track: "City Sunshine" (86 BPM), auto-ducked −11 dB under voice, bed at −21 LUFS. |
| Delivery | 1080×1920, 30 fps CFR, H.264 High, yuv420p, 10 Mbps VBR (maxrate 12M), AAC 48 kHz, −14 LUFS integrated, TP ≤ −1.5, `+faststart`, ≤ 3:00. |
| Layout | Captions at y≈1470 (top edge). Plates/cards with bottom edge at y=1450 (`bottom: 470`). Nothing in the bottom ~420 px (IG UI). Cover text inside the centre 1080×1440. |

---

## 1. How people edit video with Claude / agents (2026 landscape)

Researched by a subagent on 2026-11-15 (33 tool calls). Its conclusion: everyone converges on **"the LLM reads the video rather than watches it"**. That means a transcript with word timestamps, images only at decision points, an EDL/JSON edit list compiled to ffmpeg or Remotion, and a self-review render (contact sheet) before showing the user.

### Projects / skills found

- **browser-use/video-use** ([GitHub](https://github.com/browser-use/video-use)). MIT, ~29k stars (Oct 2026 sources; an older guide said 11.6k).
  - Turns a folder of raw footage into `edit/final.mp4`. It cuts filler words and dead air, colour-grades, adds **30 ms audio fades at every cut**, and burns in subtitles (default **2-word UPPERCASE chunks**).
  - Animations come from HyperFrames, Remotion, Manim or PIL, with one subagent per animation. It checks its own render at every cut (up to 3 retries). Session memory goes in `project.md`.
  - Footage is packed into `takes_packed.md` (~12 KB, word timestamps, speakers, audio events). `timeline_view` renders a PNG (filmstrip + waveform + word labels) only at decision points: "12KB text + a handful of PNGs" vs "45M tokens of noise".
  - Workflow: ask → confirm strategy → execute → self-evaluate → persist. It never cuts before you approve.
  - **Transcription needs an ElevenLabs Scribe API key, with no local whisper option.**
  - Install docs are macOS/Unix only: `git clone … ~/Developer/video-use`, `ln -sfn` into `~/.claude/skills/video-use`, `uv sync`, `brew install ffmpeg`.
  - Also see [chen.media guide](https://chen.media/guides/video-use-the-free-repo-that-lets-claude-edit-your-whole-video-from-raw-footage) and [explainx guide](https://www.explainx.ai/blog/video-use-claude-code-ai-video-editor-guide-2026).
  - **Verdict: copy the ideas, don't install.** It needs a paid cloud ASR key and isn't documented for Windows. The local whisper pipeline here does the same job.
- **vumhvo/reelsmith** ([GitHub](https://github.com/vumhvo/reelsmith)).
  - `cstudio ingest` produces contact sheets, scene cuts, loudness, silences and word transcripts.
  - Claude writes `edits/main.edl.json`, and `cstudio render` compiles it into one ffmpeg command.
  - Review step: loudness, black frames, silences and a contact sheet of the render.
  - Flow: init → ingest → read sheets and transcripts → plan → EDL → preview → review → final.
  - **Verdict: "cleanest pattern to copy"**. The pipeline here follows it (edl.py → build → review.py).
- **PitterLopes/ai-reels-editor-skill** ([GitHub](https://github.com/PitterLopes/ai-reels-editor-skill)). Talking-head → Reel with silence cuts, word-timed kinetic captions, words behind the speaker, cards and SFX. Built on HyperFrames + ffmpeg + Whisper. QA: a contact sheet at every beat, audio peaks, and a 720p phone copy.
- **talking-head-reel**: [mariagorskikh](https://github.com/mariagorskikh/talking-head-reel) / [zokyzhou](https://github.com/zokyzhou/talking-head-reel). Prep, transcribe, cut, stills, render and contact-sheet scripts.
- **ghost-editor** ([skillsllm](https://skillsllm.com/skill/ghost-editor)).
  - Contact sheet: `ffmpeg -v error -i talk.mp4 -vf "fps=1/10,scale=216:384,tile=6x3" -frames:v 1 -update 1 sheet.jpg`.
  - Talking-head rules: full-screen B-roll ≤ 25%, speaker's face on screen ≥ 65%, ≤ 3 inserts per minute.
- **assafkip/claude-video-editor** ([GitHub](https://github.com/assafkip/claude-video-editor)). Plugin bundling video-use, plus AI generation.
- **digitalsamba/claude-code-video-toolkit**: script, voiceover, music, visuals and render, from a prompt. Has its own transitions lib (glitch, lightLeak, rgbSplit, pixelate…).
- Directories: [aansh.ai, 92 video-editing skills](https://aanshai.vercel.app/skills), [github topic claude-video-editing](https://github.com/topics/claude-video-editing), [wilwaldon/Claude-Code-Video-Toolkit](https://github.com/wilwaldon/Claude-Code-Video-Toolkit), [a1adams/mcp-servers-for-video-editing](https://github.com/a1adams/mcp-servers-for-video-editing) (compares MCPs for Resolve/Premiere/AE/FFmpeg/Descript).
- Blogs:
  - [learnclaudeskills: Safe FFmpeg for Claude Code](https://learnclaudeskills.com/blog/safe-ffmpeg-editor-for-claude): probe first, typed scripts, `check.py` compliance, `look.py` sheets.
  - [hashp Substack faceless reel skill](https://hashp.substack.com/p/free-claude-code-skill-faceless-reels): contact sheet `fps=2,scale=216:384,tile=6x5`.

### ffmpeg MCP servers (all judged hobby-grade, maturity not checked)

- [kevinwatt/ffmpeg-mcp-lite](https://github.com/kevinwatt/ffmpeg-mcp-lite): `claude mcp add ffmpeg uvx ffmpeg-mcp-lite`. MIT; trim, convert, subtitles.
- [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill): `npx ffmpeg-skill`. 42 tools plus an MCP; reframe, loudness, platform exports.
- [github774/claude-video-studio](https://github.com/github774/claude-video-studio): one Python file (Py 3.9+ and ffmpeg).
  - 15 tools: probe, trim, concat, reframe, remove_silence, normalize_audio, add_music, burn_captions, export presets.
  - Also routes to brag, onetake, HyperFrames and Remotion.
- [yubraaj11/ffmpeg-mcp](https://github.com/yubraaj11/ffmpeg-mcp) (FastMCP), [gxtontata/video-editor-mcp](https://github.com/gxtontata/video-editor-mcp) (Node, `MEDIA_DIR`), [beambuilder/ffmpeg-mcp-server](https://github.com/beambuilder/ffmpeg-mcp-server), [bitscorp-mcp/mcp-ffmpeg](https://glama.ai/mcp/servers/bitscorp-mcp/mcp-ffmpeg) (`npx -y @smithery/cli install @bitscorp-mcp/mcp-ffmpeg --client claude`), [ffmpeg-micro-mcp](https://github.com/ffmpeg-micro/ffmpeg-micro-mcp) (cloud, REST).
- **Verdict:** not needed. Claude drives ffmpeg directly via Bash/Python with full control. MCPs add nothing for this workflow.

### Auto-cut / scene tools

- **auto-editor** ([GitHub](https://github.com/wyattblue/auto-editor), [install](https://auto-editor.com/installing)).
  - Now written in Nim, licence Unlicense. **No longer published on pip.** PyPI stops at 29.3.1 (Nov 2025); a Nov-2026 guide reports CLI 31.8.0 **(unverified)**.
  - Windows install: download the release binary and rename it `auto-editor.exe`. It is unsigned, so expect "Unknown developer" warnings.
  - Agent skill: `npx skills add WyattBlue/auto-editor`.
  - Examples: `--margin 0.2s` (default), `--margin 0.3s,1.5sec`, `--edit audio:threshold=0.04`, `--edit audio:-19dB`, `--edit motion:threshold=0.02`, `--export v1` (JSON timeline), `--export premiere|resolve|final-cut-pro|shotcut|kdenlive`.
  - **Verdict:** not used. The pipeline here does energy and spectral-VAD pause tightening itself, with more control. The idea ("cut silence by loudness, keep margins") was borrowed.
- **PySceneDetect v0.7.3** (2026-11-08) ([site](https://www.scenedetect.com/), [CLI](https://www.scenedetect.com/cli/)).
  - Install: `pip install scenedetect[opencv]`. Usage: `scenedetect -i in.mp4 detect-adaptive list-scenes save-images`.
  - v0.7 removed `-d/--min-delta-hsv` (use `-c`), and `-f/--framerate` became `--frame-rate`.
  - **Verdict:** not needed for single-take phone clips. ffmpeg `select='gt(scene,0.25)'` was enough to probe the reference.

### Remotion + Claude guides (third-party, for context)

[tella](https://www.tella.com/blog/how-to-use-remotion-agent-skills-with-claude-code), [apidog](https://apidog.com/blog/claude-code-remotion/), [wireflow](https://www.wireflow.ai/blog/remotion-claude-code), [voyager (MCP vs skills)](https://voyager.so/blog/remotion-mcp), [nihardaily](https://www.nihardaily.com/posts/claude-code-and-remotion-install-the-skill-render-a-video).

---

## 2. Remotion

- **Version used:** `remotion` 4.0.543 (latest on npm 2026-11-15), with `@remotion/cli`, `@remotion/media`, `@remotion/captions` and `@remotion/media-utils` all at 4.0.543, React 19.1.0, TypeScript 5.8.3, Node v22.21.0 / npm 10.9.4.
- Add packages with `npx remotion add @remotion/media @remotion/captions`, which keeps versions aligned.

### License — who must pay ([pricing](https://www.remotion.dev/docs/license/pricing.md), [FAQ](https://www.remotion.dev/docs/license/faq.md))

- **Free License:** "completely free to use for any individual or small company", "For individuals and companies of up to 3 people", "all features included, unlimited commercial use". This holds "Even if you are incorporated … as long as your total headcount is 3 or less". Qualifying non-profits are free regardless of headcount.
- **Agencies:**
  - If the client receives only the finished file (MP4), "their headcount does not count toward yours. Only your agency's headcount counts". So an agency of ≤3 is covered, and 4+ needs a Company License.
  - If the client owns or operates the Remotion project, both headcounts are aggregated. The IP owner buys the licence, and an agency may administer it.
  - Freelancers or studios brought in to operate the same project aggregate too.
- **Company License:**
  - **Creators** $25/month per seat. A seat is everyone who has the project on their machine and makes videos. Reviewers, recipients, AI agents and automation developers are excluded.
  - **Automators** $0.01/render, billed in blocks of 1000 ($10), minimum $100/month.
  - **Enterprise** from $500/month.
  - Buy at remotion.dev/dashboard.
- **Licence note:** Remotion is free for individuals/teams ≤3 that deliver only MP4s to clients. A 4th person making videos means Creators seats are needed.

### Official agent skills ([docs](https://www.remotion.dev/docs/ai/skills))

- Install options:
  - `npx remotion skills add` inside a project. This puts the skills in `.agents/skills/` and symlinks them into `.claude/skills/`. **The symlinks worked on Windows 11.**
  - `npx skills add remotion-dev/skills` (add `-a claude-code -y` for no prompts, `--global`)
  - `gh skill install remotion-dev/skills`
  - `npx create-video@latest --skills`
  - Update with `npx remotion skills update`. Source: `remotion-dev/remotion/packages/skills`.
- Skills (v4.0.543): remotion-best-practices (router), -create, -markup, -studio, -render, -maps, -captions, -saas, -interactivity, -docs, -license (from v4.0.540), -upgrade, -multimedia (Mediabunny). They are now installed under `.claude/skills/`.
- A Claude Code plugin repo, [remotion-dev/claude-code-plugin](https://github.com/remotion-dev/claude-code-plugin), exists ("internal package", docs at remotion.dev/docs/ai/claude-code-plugin). The commands `claude plugin marketplace add remotion-dev/claude-code-plugin` and `claude plugin install remotion@remotion` came from a third-party guide **(unverified)**.
- Skill guidance worth remembering:
  - **Don't render unless the user explicitly asks; open Studio instead** (`npx remotion studio`, or `--no-open` in agents with an in-app browser; open `/[composition-id]`).
  - "The Studio supports WebMCP tools."
  - Preserve user edits made outside the conversation.

### Studio visual editing (Interactivity) — facts verified in 4.0.543 typings

- Studio edits the JSX nodes themselves, so markup must be **flat, with inline literal props**:
  - No style constants, no object spreading, no math in `style`.
  - Animate only through inline `interpolate(frame, [..], [..], {…})`. The input range may use `fps`/`durationInFrames` from `useVideoConfig()`.
  - Use the CSS props `scale`/`rotate`/`translate`, not `transform`.
  - Keep `defaultProps` inline on `<Composition>`/`<Still>`.
  - **A JSON-driven composition (`timeline.json` → map) is NOT editable**, which is why `gen_tsx.py` was written to emit a flat TSX.
- `Interactive.create({Component, layout: 'none' | 'absolute-fill', componentName, schema})`:
  - Schema field types: `string`, `number` (min/max/step/integer, keyframable), `boolean`, `color`, `enum` (`variants: Record<string, schema>`), `array`, `asset` (`assetType: audio|video|image`), `font-family`, `font-weight`, transform types, `remotion-captions`, `hidden`.
  - Built-in fragments: `Interactive.textSchema`, `backgroundSchema`, `borderRadiusSchema`, `borderSchema`, `childrenSchema`, `captionsSchema`.
  - `style.translate/scale/rotate/transformOrigin/opacity` are added automatically.
  - **Gotcha: in 4.0.543 TS, `NumberFieldSchema` requires `hiddenFromList: boolean`**, so add `hiddenFromList: false` or tsc fails.
- `Interactive.Div`/`Span`/`Svg`/`Path`… make plain elements editable. `<Img>` is already interactive.
- Timeline structure:
  - A named `<Track name="…">` holds non-overlapping clips with independent `from`.
  - `TransitionSeries` keeps adjacent clips adjacent.
  - Put a shot's video, voice and captions under **one** `<Sequence from durationInFrames trimBefore>` so trimming moves them together.
  - The captions array must be inline on each caption node (`captions={[{text, startMs, endMs, timestampMs, confidence}]}`, source-ms of the clip) for Studio's Caption editor to write back.
  - Cutaways go on a separate track, and the speech audio must stay underneath.
- `startFrom` is deprecated, renamed to **`trimBefore`**.
- **Clock inside a trimmed Sequence (probed):** `useCurrentFrame()` = local + trimBefore, and `useVideoConfig().durationInFrames` = dur + trim. The local clock is recovered with `Internals.SequenceContext.cumulatedNegativeFrom` (= −trimBefore): `local = frame + cumulatedNegativeFrom`. This is used by `useShotClock()` in `elements.tsx`.
- `<Video>` from `@remotion/media`: `trimBefore`, `durationInFrames`, `volume` (keyframes shown as a curve in Studio), `playbackRate` (no reverse), `toneFrequency` (render only), `objectFit`.
- **Gotcha:** `OffthreadVideo` with `trimBefore` inside a `<Still>` ignored the trim and showed the wrong frame. Workaround: extract a JPG with ffmpeg and use `<Img>`.
- Other packages seen in skills:
  - `@remotion/transitions` (since 4.0.53): fade, slide (from-left/right/top/bottom), wipe, flip, clockWipe, iris, plus newer HTML-in-canvas ones (zoomBlur, dreamyZoom, zoomInOut, crossZoom, pushCut, filmBurn, linearBlur, blurSlide, cube, dissolve, crosswarp, swap…).
    - Transitions shorten the timeline (60+60−15 = 105). `TransitionSeries.Overlay` doesn't.
    - Timing: `linearTiming({durationInFrames})` or `springTiming({config:{damping:200}})`.
  - `@remotion/effects/light-leak` `lightLeak({progress, seed, hueShift})` on `<Solid>` (≥ 4.0.500).
  - `@remotion/motion-blur` `<HtmlInCanvasMotionBlur samples shutterAngle>` (≥ 4.0.529). Live preview needs Chrome 149+ with `chrome://flags/#canvas-draw-element`.
- **Captions API** ([docs](https://www.remotion.dev/docs/captions/create-tiktok-style-captions)):
  - `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds})` (≥ 4.0.216) → `pages[].tokens[{fromMs,toMs}]`.
  - 1200 ms gives a few words per page; 200–500 ms gives word-by-word. Export SRT with `serializeSrt()`.
  - Local ASR: `@remotion/install-whisper-cpp` with `tokenLevelTimestamps: true` → `toCaptions()`.
  - Skill advice: use the "Basic Captions" element (fetch `https://www.remotion.dev/elements/captions/basic-captions.md`).
  - **Not used here:** own `Captions` component, see §9.
- **Performance on the test machine (RTX 3060 Ti, i5-10400):**
  - The first `npx remotion still` took ~43 s (bundling).
  - The half-scale preview of the JSON-driven v1 took ~48 s. **The flat, editable version took 6 min 42 s at half scale.**
  - A full 1080×1920 render takes ~10–15 min (`--concurrency=8 --crf=16 --audio-bitrate=192k`).
  - Every render copies `public/` (1.1 GB of mezzanine files), which shows as "Copying public dir".
- **Caveat:** the music bed is pre-ducked from the voice envelope, so ducking does not follow clips moved in Studio. Re-run `music.py`.

---

## 3. brag / Hyperframes evaluation

- **brag** ([site](https://latent-spaces.github.io/brag/), [repo](https://github.com/latent-spaces/brag)), evaluated because it had been recommended as a Claude video tool.
  - What it is: "An agent skill that turns the project you created into a **twenty-second launch video**. Music, motion, share copy included". MIT, ~21.6k stars, v0.4.0 (pre-1.0), by @shunithaviv.
  - Run as `let's /brag` (optionally `--tone "…"`). Output: `brag-output/` with the plan, a composition brief, share copy and `brag.mp4`.
  - Modes:
    - `/brag-slim` (default from v0.4.0): "Everything built by the model… No Hyperframes, no bundled assets". It auto-activates on Opus 5.5, Sonnet 5.5 or Fable 5.2.
    - `/brag --full`: the classic mode, built on **Hyperframes** ([hyperframes.heygen.com](https://hyperframes.heygen.com)).
  - Install:
    - Claude Code: `/plugin marketplace add latent-spaces/brag` then `/plugin install brag@brag`
    - Other agents: `npx skills add https://github.com/latent-spaces/brag --skill brag` (or `--skill brag-slim`)
    - Update: `claude plugin update brag`
  - Dependencies: Node 22+, FFmpeg on PATH, Hyperframes CLI (`npx hyperframes`, `npx hyperframes doctor`). TTS is Kokoro via Hyperframes (`--voice`, off by default). Music is ende.app "Happy Beats / Business Moves" (**CC BY 4.0, attribution required**). SFX from Kenney.
  - Windows: symlinks need `core.symlinks=true` plus Developer Mode or admin, or copy the folder.
  - The hosted version, letsbrag.app, takes a site URL ("pay once", no price shown).
  - **Verdict: don't use for camera-footage reels.** It is built for 20 s promo videos of web projects. The README never mentions using your own footage, and its bundled music needs attribution.
- **Hyperframes** (HeyGen) is the renderer behind brag --full, video-use animations and PitterLopes' reels skill. Not tried here. Remotion covers the same need and is free for small teams (§2).

---

## 4. Transcription

- **Used:** faster-whisper **1.2.1** + ctranslate2 **4.9.0** (has a cp314 win_amd64 wheel) on Python 3.14, GPU **RTX 3060 Ti 8 GB**.
  - Model `large-v3`, `device="cuda"`, `compute_type="float16"` (CPU fallback: `int8`).
  - Speed: a 50 s clip took 18.6 s including model load. All ~12 min of footage took about a minute.
  - Settings (the initial prompt lists the client's name, city and domain words; fill in from `brand.json`):
    ```python
    model.transcribe(audio_np_16k_mono, language="uk", word_timestamps=True, vad_filter=True,
                     vad_parameters={"min_silence_duration_ms": 300},
                     initial_prompt="Ветеринарна клініка <Назва>, <Місто>. Лікар, кіт, собака, стаціонар.")
    ```
  - Output per clip: `transcripts/IMG_xxxx.json` → segments → words `{w, s, e, p}`.
- **Windows setup that works:**
  - `pip install faster-whisper librosa numpy pillow nvidia-cublas-cu12 nvidia-cudnn-cu12`. The packages land in the **user** site-packages.
  - In the script, before importing faster_whisper:
    ```python
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        for b in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(b); os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
    ```
  - **PyAV 19.0.2 breaks faster-whisper's file decoder** (`TypeError: open() got an unexpected keyword argument 'metadata_errors'`). Feed a numpy array read with `soundfile` (16 kHz mono WAV made by ffmpeg) instead of a path.
- **Whisper timing is wrong in both directions (measured with spectral VAD):**
  - Word *starts* come 0.3–0.5 s early (e.g. «Отже,» whisper 0.72 s vs real 1.08 s; «Тут» 109.98 vs real >110.39).
  - Word *ends* come early.
  - Whisper also stretches a word over the following pause («стерилізатор,» lasted 2.3 s).
  - So never cut on whisper times. Use whisper only for *what* was said; take *where* from the audio (§5).
- **Mis-hearings, fixed via the `FIX` dict in edl.py:** «мен,» → «мене,», «Айдекс» → «IDEXX», «-22.» → «22.» (a house number), a missing comma after a street name, «свармет.» → removed. Whisper also misspelled both pet names in the footage (unusual names get mangled — always check them). One clip gave a hallucinated subtitler credit line («Субтитрувальниця …») on a 2.9 s clip with no speech: ignore such lines.
- **Alternatives researched, not used:**
  - **WhisperX** gives wav2vec2 forced alignment, about ±50 ms vs ±500 ms for vanilla whisper (vendor figures). Its default Ukrainian aligner is `Yehor/wav2vec2-xls-r-300m-uk-with-small-lm` (confirmed in [alignment.py](https://raw.githubusercontent.com/m-bain/whisperX/main/whisperx/alignment.py)). But whisperX 3.8.7rc1 requires **Python >=3.10,<3.14** and `torch~=2.8.0`, so it can't install on Python 3.14 without a separate venv (`uv venv -p 3.12`). Digits and Latin words may get no timestamps. Paper: [arXiv 2303.00747](https://arxiv.org/pdf/2303.00747).
  - **Ukrainian fine-tunes:**
    - [ihnatov-yuri/whisper-large-v3-turbo-uk](https://huggingface.co/ihnatov-yuri/whisper-large-v3-turbo-uk): mean WER 8.23% vs 9.79% for large-v3 across 10 held-out sets. Common Voice is in its training data.
    - [egorsmkv/speech-recognition-uk](https://github.com/egorsmkv/speech-recognition-uk) table: large-v3 20.53% WER, `Yehor/whisper-large-v3-turbo-quantized-uk` 12.75% WER / 3.25% CER. Test set not stated.
    - Ready-made CT2 (faster-whisper) conversions were **not verified**, so you may need `ct2-transformers-converter`. Stock turbo is reportedly −2–5% accuracy in non-English languages.
  - **ElevenLabs Scribe** (used by video-use) is a paid cloud service and wasn't needed.
- **Verdict:** stock large-v3 was good enough for this clinic speech. Next time, consider the Ukrainian turbo fine-tune if accuracy matters, and keep VAD-based timing regardless.

---

## 5. Audio: rustle/clicks, denoise, cut boundaries, loudness

### Research findings (lav rustle)

- **No free or open-source tool targets lav rustle.** The dedicated tools are paid:
  - [iZotope RX De-rustle](https://www.izotope.com/en/products/rx/features/de-rustle.html), RX Advanced only. It is ML-trained on isolated rustle.
  - [CrumplePop/Boris FX RustleRemover](https://borisfx.com/products/rustleremover/), with plugins for Premiere/Resolve/Audacity…
  - Audition has no equivalent ([Adobe feature request](https://community.adobe.com/feature-requests-545/need-de-rustle-to-remove-clothing-rubbing-sounds-or-buy-izotope-to-get-their-de-rustle-1436133)).
- **Free denoisers handle steady noise, not rustle:**
  - RNNoise (`arnndn`, models `sh.rnnn` / `cb.rnnn` from GregorR/rnnoise-models, BSD) and `afftdn` handle hiss and hum.
  - [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) (MIT/Apache) is best of the free options on non-stationary noise and is conservative.
    - pip `deepfilternet` 0.5.6 supports only Python ≤3.11 (fork `DeepFilterNet-py312` is unverified).
    - A standalone `deep-filter` binary exists in the GitHub releases (v0.5.6). The Windows asset name was not confirmed.
  - [Resemble Enhance](https://github.com/resemble-ai/resemble-enhance) is generative and can fabricate detail.
  - Demucs does separation and dereverb.
  - Benchmarks on VoiceBank+DEMAND ([ClearerVoice paper](https://arxiv.org/pdf/2506.19398)): DeepFilterNet PESQ 3.03 vs Resemble 2.84. No test on rustle exists.
- **Pro workflow** ([gearspace](https://gearspace.com/board/post-production-forum/644411-tips-removing-clothing-noise-lavs.html), [audioedit.io](https://www.audioedit.io/blog/how-to-fix-lavalier-mic-rustle)):
  1. Edit first: cut rustle between words and fill with room tone or alternate takes.
  2. De-click and de-crackle passes.
  3. Spectral repair (rectangle and patch).
  4. High-pass ~80–100 Hz for thuds, gentle high-shelf for crackle.
  5. Accept that rub under speech mostly remains. Re-record if the capsule rubbed for minutes.
- **Windows `arnndn` path escaping:** the drive colon breaks the filter syntax. Use a relative path, or `-af "arnndn=m='C\:/models/sh.rnnn':mix=0.85"` **(untested)**.

### What was built and used (`rustle.py`)

- **Spectrogram observation on this footage:** rub clicks are razor-thin vertical lines from DC to 19 kHz that collapse by more than 12 dB within 25 ms. Ukrainian sibilants (с, ш, ч, ц) are 80–200 ms blobs mostly in 4–12 kHz that sustain.
- **First detector failed:** 11–19 kHz energy vs a 1.5 s median gave 50–120 "events" per minute, because it flagged sibilants.
- **Final detector:** STFT NP=512, HOP=128 at 48 kHz.
  - Onset condition: the fraction of 1.5–19 kHz bins jumping >12 dB over a 3-hop lag is ≥ **0.8**.
  - Impulse condition: band energy falls ≥ **8 dB** within 25 ms. The first value of 12 dB missed the known clicks.
  - Result: 0–9 clicks per minute.
- **Repair (spectral clamp):** for each event, pre=3 frames and post=0.08 s (widened from 0.035 s because a tail remained). Each bin is clamped to **1.3×** the per-bin median of unflagged neighbours within ±120 ms. Phase is kept.
  - About 55 clicks were repaired across clips (e.g. 2364: 16, 2376: 17, 2385: 7).
  - Verified visually by before/after spectrograms.
- **Clean-voice chain after repair:** `highpass=f=85,afftdn=nr=8:nf=-44:tn=1,deesser=i=0.25,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2`.
- **Per-clip voice for Remotion:** `loudnorm=I=-16:TP=-2:LRA=7` at 48 kHz. The master voice is `loudnorm I=-15:TP=-1.5:LRA=9`.
- **Limitation (tell the client):** sustained rub directly under speech is not removable without paid tools.

### Cut boundaries (the biggest quality issue; owner feedback twice)

- **v1** cut on whisper word times and tightened pauses >0.32 s (pad 0.08/0.10). The owner reported phrases cut off before the speaker finished and asked to hold roughly half a second to a second after each phrase.
- **v2** used an RMS envelope at 10 ms with thr = max(floor+8, speech−24).
  - Pause tightening: `GAP_MAX, PAD_PRE, PAD_POST = 0.50, 0.15, 0.32`.
  - `natural_bounds`: end = 150 ms of quiet + 0.30 s, capped at +1.0 s and before the next word.
  - Plus voice fades: 2 frames in / 4 out, none on contiguous joins (≤3-frame tolerance).
  - Still, 11 of 32 cut ends were loud.
- **v3 (`vad.py`, spectral VAD on the raw 48 kHz lav track)** came after the owner asked to analyse the bare voice track and find where the frequencies actually drop. Spectrum: NFFT 2048, hop 480 (10 ms), band 90 Hz–8 kHz.
  - Noise floor is computed per bin (10th percentile) and subtracted ×2.0. `rel` = residual energy relative to the clip's 95th percentile.
  - **Threshold is adaptive per clip:** 10th percentile of `rel` + 8 dB, clamped to [−40, −20] dB. A fixed −40 dB threshold treated clinic or street noise as voice: 31 of 42 edges were "clipped".
  - **End** = voice-off (held ≥0.12 s below threshold) + **TAIL 0.28 s**, but never past the next real onset − 0.06 s.
  - If speech runs straight on, cut at the **first near-silent dip** (local minimum < thr + 12 dB) and quantise frames *away* from the neighbouring word. These are "valley" cuts.
  - **Start** = real onset − **PRE_ROLL 0.12 s**, never before the previous word has decayed.
  - EDL ranges that touch (≤0.06 s apart) are visual-only splits (B&W or punch-in), so their audio is joined exactly. An earlier bug removed 0.13 s inside a word (a pet's name).
  - Voice fades: 0 on seamless joins, **1 frame** on valley/tight cuts, 2 in / 4 out where the voice has already decayed.
- **QA tools:**
  - `cut_audit.py`: a table plus a spectrogram sheet per cut. Red = cut, yellow = whisper, cyan = VAD.
  - `verify_words.py`: re-transcribes the *edited* voice and diffs it against the expected words, as an "ear test".
  - **Whisper on the whole reel gives false alarms** («адміністрат.»). Confirm any suspect by transcribing an isolated snippet: it was recognised fully at all 6 cut points tested.
- **Final v3 numbers:** 20 cut ends = 6 ok, 2 tight, 9 valley, 3 "CLIPPED" (audit artefacts from whisper-stretched words). verify_words: all 305 expected words heard, similarity 0.992. The owner was asked to listen to the valley cuts at 27.8, 35.2, 51.0, 54.8, 60.0, 72.0, 83.0, 114.5 and 133.7 s.

### Loudness targets used

- Final: **two-pass** `loudnorm=I=-14:TP=-1.5:LRA=9` with `measured_*` values and `linear=true`, then `aresample=48000`. This measured −14.0 LUFS, TP −2.2 dBTP. Single-pass in v1 gave −13.8 LUFS, peak −1.4.
- **−14 LUFS as "the Instagram standard" was Claude's assumption, not taken from a fetched source (unverified).**
- Music bed −21 LUFS; under voice it is ducked −11 dB, roughly −32 LUFS vs voice −16 (§7).

---

## 6. Instagram Reels delivery specs

- **Length:** the client brief asked to shorten the video to 3 minutes, and Claude treated **3:00 as the Reels maximum (unverified, not fetched)**. Delivered 2:55 (v1/v2) and 2:53.85 (v3).
- **Official-ish spec** (Meta developer docs via third-party summaries: [revid](https://www.revid.ai/blog/instagram-video-formats), [thepostflow](https://thepostflow.com/post-production/post-production-workflows/export-settings-youtube-instagram-tiktok/)):
  - MP4 or MOV, no edit lists, moov atom at the front.
  - H.264 or HEVC, closed GOP, 4:2:0.
  - AAC 48 kHz, ≤128 kbps stereo.
  - Max width 1920, 9:16, 23–60 fps.
  - VBR ≤ 25 Mbps, which seems to apply to the API publishing path.
  - HEVC gains nothing because IG transcodes to H.264.
- **Bitrate advice varies:** 5 Mbps ([ffmpeg-micro](https://www.ffmpeg-micro.com/blog/best-video-settings-for-instagram-reels-bitrate-resolution-ffmpeg-preset)), 5–8 ([screensnap](https://www.screensnap.pro/blog/instagram-reels-size-guide)), 8–12 ([invideo](https://invideo.io/blog/instagram-reel-size-guide/)), 10–16 (Resolve). Constant 30 fps (60 only for fast motion). InVideo: enable high-quality uploads in the app.
- **Used encode** (master → insta):
  ```
  ffmpeg -i master.mp4 -c:v libx264 -preset slow -profile:v high -pix_fmt yuv420p -r 30 \
    -b:v 10M -maxrate 12M -bufsize 20M [-g 60] -c:a aac -b:a 192k -ar 48000 -movflags +faststart insta.mp4
  ```
  Result: ~10.1 Mbps, 221 MB for 2:55. The master (Remotion crf16, ~18 Mbps) was 400 MB, too heavy to upload from a phone. The master's audio is AAC 256k.
  - **Noticed in logs, not investigated:** ffprobe reports `yuvj420p(pc, bt470bg/unknown/unknown)` for both master and insta files, i.e. a full-range flag and non-bt709 tags inherited from Remotion's output. It might be worth adding `-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709` (unverified whether IG cares).
- **Safe zones** on 1080×1920 (sources disagree; [kreatli](https://kreatli.com/guides/instagram-reels-safe-zone), [filmscribe](https://filmscribe.ai/en/tools/instagram-reels-safe-zone), [outfy](https://www.outfy.com/blog/instagram-safe-zone/), [lilachbullock](https://www.lilachbullock.com/instagram-reels-safe-zone/), [adchecklab](https://adchecklab.com/articles/instagram-reels-safe-zone-template)):
  - Meta ads guidance: top 14% / bottom 35% / sides 6%, i.e. **269 / 672 / 65 px**, leaving a 950×979 safe box. Ads with a disclaimer: bottom 2/5 = 768 px.
  - Like/comment/share column: ~227 px wide on the right, starting ~1152 px from the top.
  - Organic Reel UI measured:
    - Kreatli: 297 top / **422 bottom** / 49 sides (safe 982×1201)
    - Filmscribe (Oct 2026): ~250 top / 420 bottom / 130 right
    - Xyla: 220 / 430 / 130
    - Outfy: 108 / 320 / 60 L / 120 R
  - **Profile grid shows the middle 1080×1440** (240 px lost top and bottom). The 4:5 feed preview cuts 285 px top and bottom.
- **Used layout:**
  - Captions: top edge at y=1470 (≈1470–1540).
  - Name/address cards and `//` tags: bottom edge at y=1450 (`bottom: 470`). Plates sit above captions.
  - Kinetic titles: `paddingBottom: 470` with a dark gradient, or centred for the hook.
  - Everything stays out of the bottom ~420 px.
  - The owner explicitly wanted captions and plates **at the bottom, not mid-screen**. This contradicts generic "upper-middle" advice, so follow the owner.
- **Cover:** a separate `Still` (1080×1920) with a JPG background frame. Text sits inside the centre 1080×1440 so it survives the grid crop. Rendered with `npx remotion still … --image-format=jpeg --jpeg-quality=92`.
- **Hook and pacing research** (generic; [quso](https://quso.ai/blog/instagram-reels-best-practices), [reelxo](https://www.reelxo.tech/blog/reel-hook-ideas), [creatorlane](https://creatorlanehq.com/blog/how-to-write-instagram-reel-hooks), [slidycreator](https://slidycreator.com/blog/instagram-reel-trends-2026/), [digitalapplied](https://www.digitalapplied.com/blog/instagram-reels-ads-2026-creative-strategy-guide)):
  - The first 3 s decide; ads want the hook within 0.5 s. Socialinsider 2026: 60.5–65.5% skip within 3 s. Creator Lane: the decision comes in ~1.7 s.
  - Frame 1 must have motion. **Never a black first frame.**
  - On-screen text: under 10 words, visible on frame 1.
  - Hook devices: a burst of 3 half-second cuts, or a freeze on a peak moment.
  - Suggested length 21–34 s (Quso), which conflicts with this 3-min clinic tour brief.
  - Nothing was found on B&W "live moment" inserts; that implementation is Claude's own.
  - **Used hook:** 6 shots × 0.6 s with zoom 1.08 and a "tick" SFX each, plus the kinetic title «ЕКСКУРСІЯ / клінікою <назва>», 3.6 s total.

---

## 7. Music

- **FreePD.com** is **closed** ("free-to-use, Public Domain music downloads" 2008–2025, now permanently closed).
- **FreePD mirror [en.freepd.cn](https://en.freepd.cn/music)**:
  - Licence: "released under CC0 … The original authors have waived all copyright", "Free for personal and commercial use — no attribution required".
  - Categories: `/music/upbeat`, `/scoring`, `/romance`, `/comedy`, `/electronic`, `/epic`, `/world`, `/zoned`, `/miscellaneous`, `/horror`.
  - **Download API:** `https://en.freepd.cn/api/music/<hex of "Upbeat/<Title>.mp3">`, for example:
    ```bash
    hex=$(printf 'Upbeat/%s.mp3' "City Sunshine" | xxd -p | tr -d '\n'); curl -sL -o "City Sunshine.mp3" "https://en.freepd.cn/api/music/$hex"
    ```
  - The Upbeat page says 18 tracks but listed only 12 (Advertime, And Just Like That, Bar Brawl, Be Chillin, City Sunshine, From Page to Practice, Funshine, Happy Whistling Ukulele, Inspiration, Inventing Flight, Limit 70, Motions).
- **[Pixabay Music](https://pixabay.com/music/)**: 300k+ tracks, "Free for commercial use, No attribution required". It uses Pixabay's own Content License, **not CC0**, with possible YouTube Content ID claims (subagent's knowledge, **unverified**). Not used.
- **[Chosic, no-attribution filter](https://www.chosic.com/free-music/all/?sort=&attribution=no)**: mixed licences, so check each track. Not used.
- **Rejected:**
  - FreePD Comedy tracks: off-tone for a clinic (Creepy Comedy, Drunken Party…). Candidates from that category were never downloaded.
  - brag's bundled CC BY 4.0 track, because it needs attribution.
- **Downloaded:** 8 Upbeat tracks into `toolkit/music/`. Analysed with librosa (`music_probe.py`: tempo, spectral centroid, onset density, harmonic ratio, 10-chunk energy curve):

| Track | Dur | BPM | Centroid | Notes |
|---|---|---|---|---|
| Advertime | 134 s | 117 | 965 Hz | steady |
| And Just Like That | 114 s | 123 | 1629 Hz | too short |
| Be Chillin | 203 s | 136 | 1403 Hz | **backup choice** |
| **City Sunshine** | 185 s | **86** | 1159 Hz | **chosen**: calm, steady energy (span 14.4 dB), muted timbre, longer than the reel |
| From Page to Practice | 137 s | 161 | 1075 Hz | builds up |
| Funshine | 165 s | 96 | 1924 Hz | bright, loud |
| Happy Whistling Ukulele | 123 s | 129 | 2440 Hz | very bright |
| Inspiration | 138 s | 117 | 515 Hz | dark |

- **Bed (`music.py`):**
  - The track is loudnormed to **−21 LUFS** (TP −3).
  - Voice activity comes from `clean/master_raw.wav` (10 ms RMS > 30th percentile). The ducking envelope uses `maximum_filter1d` size 45 (450 ms hold) and `uniform_filter1d` size 25 (~250 ms attack/release).
  - **Duck −11 dB** under speech. Fades: 0.6 s in, 2.5 s out (curve ^1.5). Loops if the track is too short.
  - Ducked about 93–94% of the time; full level only in the hook, pauses and the end card.
  - Output `public/music_bed.wav`, placed on the "Музика" track.
- **Caveat told to the owner:** Claude can't listen, so the mood and absence of vocals in City Sunshine are not confirmed.
  - Swap the track: re-run `music.py` with another track, then `gen_tsx.py`.
  - Claude also suggested that adding a trending IG track in-app at 5–10% may help reach. That is Claude's suggestion, unverified.

---

## 8. Reference reel & client brand

### Reference reel ([instagram.com/reel/Dfpb3nLPZby](https://www.instagram.com/reel/Dfpb3nLPZby/?rpxt=Z2RzOG5wdTNwZjNs))

- Author: @mon_toutou.grooming, a dog-grooming salon, posted 2026-11-12. Caption: "Боїтеся, що з короткою шерстю ваш пухнастик мерзнутиме взимку? …", with the slogan "Mon Toutou — догляд, який гріє". "Original audio", 42 likes.
- **Downloaded with `python -m yt_dlp` without login** (public reel): 720×1280, 30 fps, 32.5 s, 3.77 MiB.
- Format: an educational talking head (a groomer at the reception desk, then on a sofa), with dog B-roll.
- Style, from the reference project's stored contact sheets (`ref/ref_sheet*.jpg`), re-checked when writing this doc:
  - **Huge bold uppercase sans** words («ДУМАЄТЕ», «ВОНА ВЗАГАЛІ») combined with a **handwritten script accent** in a contrasting colour (lime or pink: «ваша собака», «шерсті», «тим тепліше»).
  - Small **`//`-prefixed labels** with one highlighted word («//тільки **чиста**», «//буде мерзнути»).
  - Plain small white subtitle lines in the lower third.
  - B-roll inside a **framed inset over a textured background** (grid paper, leopard fur).
  - Photo cut-outs pinned over the speaker.
  - Light, playful, bright.
- **Translated to the client's brand:**
  - Kinetic titles: Montserrat 900 caps, 124 px (92 px if >11 chars), white with a navy drop-shadow, spring scale-in, plus a MarckScript script line in sky blue, rotated −4°, revealed with a clip-path wipe.
  - `// section` tags on navy pills.
  - Word-highlight captions.
  - Whip, zoom and flash transitions with a synthesized whoosh.
  - B&W "живі моменти" with grain.
- Scene-cut probe: `select='gt(scene,0.25)'` printed no cuts **(unclear whether the probe failed or the reel is continuous)**.

### Client brand (how it was derived)

- The client's Instagram profile was read with WebFetch (partial): display name, category, phone and a bio line were visible; the bio was truncated (the address may have been in the cut-off part). No staff names were available there.
- **Brand colours.** The profile avatar was quantized with PIL into 6 colours (mostly whites plus one mid-blue and one pale blue). Together with the owner's verbal description of the palette (white / blue / light blue), a 5-step palette was derived and stored in `brands/<client>/brand.json`:
  - navy/dark, blue/mid, sky/accent, ice/pale, white.
  - These are derived and tuned, not official brand values **(unverified with client)**.
- **Fonts:** Montserrat, required by the client. Downloaded the variable `Montserrat[wght].ttf` from google/fonts. Script accent is **Marck Script** (Cyrillic-capable). Caveat was also downloaded but not used.
  - Loaded in Remotion via `new FontFace(...)` with `delayRender`/`continueRender`, from `public/fonts/`.
- **Facts used on screen that needed client confirmation** (lesson: list these in the report):
  - The street address came only from the whisper transcript.
  - The doctor's name and titles came from the footage; Claude assumed the same doctor appears in the surgery and lab footage.
  - **24/7:** the door showed opening hours (10:00–20:00), so the end card said "24-hour inpatient ward" instead of «24/7». **But the client's IG profile name itself says "24/7"**, so the client may actually want "24/7". Ask.
- **Footage facts:**
  - 39 iPhone `.MOV` files: 3840×2160 HEVC with rotation −90 (portrait), 60 fps (one at 59.94), bt709 SDR, AAC. About 12 min and 4.1 GB in total. A/V start offsets are all 0.
  - One stray, unrelated PNG was ignored.
  - Content: a clinic tour led by a doctor.
    - Entrance and introduction (2403), therapy department and reception (2404), cabinet 1 / dermatology (2407), thermostat (2408, cut), cabinet 2 / ultrasound (2412), therapists (2413).
    - Surgery and dentistry (2362 earlier take, 2364), lab (2384–2386), inpatient ward (2375/2376/2401), upcoming X-ray (2414).
    - Short B-roll and pet moments.

---

## 9. Other notable findings, environment quirks, failed approaches

### Environment (Windows 11 test machine)

- **ffmpeg 9.0.2** (gyan.dev full build) installed with `winget install --id Gyan.FFmpeg -e`. **It is not on PATH.** Path: `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\`. ImageMagick and whisper CLI are not installed.
- Python 3.14 (system install), pip 26.0.1. Packages go to the **user site**, so **don't run `python -I`** (ModuleNotFoundError). matplotlib needed `pip install --user matplotlib` (3.11.2).
- Console is cp1252, so always set `PYTHONIOENCODING=utf-8` when printing Cyrillic.
- Hardware: RTX 3060 Ti 8 GB, i5-10400 (12 threads), 31.9 GB RAM.
  - 4K HEVC decode on CPU is slow (proxies took minutes). Use `-hwaccel cuda` with `h264_nvenc` for mezzanine files:
    ```
    -hwaccel cuda -i IMG.MOV -vf "fps=30,scale=1080:1920:flags=lanczos,eq=contrast=1.05:saturation=1.07:gamma=0.98,unsharp=5:5:0.35,format=yuv420p" -c:v h264_nvenc -preset p6 -rc vbr -cq 17 -b:v 0 -g 15 -an
    ```
    The short GOP of 15 is for fast seeking in Remotion.
- ffmpeg `drawtext` with Windows font paths breaks on the drive colon. `cd` into the fonts dir and use a relative `fontfile=mont.ttf`. Montserrat's `%5Bwght%5D` filename was copied to `mont.ttf`.
- Pillow 13: `Image.getdata` is deprecated (removed in Pillow 14), so use `get_flattened_data`.
- Background commands: a `grep -v`/`tail` filter once hid a Remotion render error, so the first preview "finished" with no file. Rerun with the full log. Root cause unclear (maybe the output path).

### "Seeing" footage — tools that worked

- Proxies: `scale=540:-2,fps=30` with libx264 crf 26. Audio: 16 kHz mono WAV for whisper, 48 kHz mono for analysis.
- Per-clip contact sheet: ≤24 frames, `fps=1/iv,scale=200:-2,drawtext=…%{pts\:hms}…,tile=8x3` (now part of `ingest.py`). For short clips, one 6-frame row each, stacked 5 per page with PIL.
- Spectrograms: `showspectrumpic=s=1600x400:legend=1:scale=log:fscale=lin:color=intensity`, and zoomed 2 s windows for events.
- `review.py <video> <out.jpg> [frames]` tiles labelled frames at every text start and transition in/out. It caught glued captions, black whip edges, spill-over tags, and captions under titles.
- Crop checks for detail: `-vf "crop=1080:500:0:1250"`.

### Visual implementation details (for reuse)

- Punch-in on every jump cut alternates zoom 1.0 / 1.12. Each shot has a gentle push-in from 1 to 1.035.
- Transitions, with half-length H = 7 frames:
  - **whip**: translateX 300 px + scale ×1.4 + blur 30, with cubic easing in and out. An earlier 760 px translate showed black edges.
  - **zoom**: scale ×1.55 + blur 20.
  - **flash** and **pop** are also used.
  - SFX volumes: whoosh 0.32, pop 0.22, tick 0.15.
- SFX are **synthesized in numpy**, so there are no licensing issues:
  - whoosh: noise through a sweeping band-pass, 0.42 s
  - pop: a pitched 0.09 s blip
  - tick: a 0.03 s click
- B&W live moment: grayscale + contrast + SVG `feTurbulence` grain overlay (opacity 0.35, `mix-blend-mode: overlay`, seed changes per frame).
- Captions (own component):
  - Pages hold ≤3 words, ≤22 chars, break after punctuation or a 300 ms gap. A page stays ≤ last word end + 500 ms.
  - The active word changes **colour only** (sky). Scaling it ate the inter-word gap and spans lost spaces, so a flex row with `columnGap 18` is used instead.
  - Montserrat 700, 58 px, white with a text shadow.
  - Words starting during a kinetic title, or ≤12 frames before one, are hidden. Pages that would linger into a title are shortened.
  - Word ownership comes from whisper *start*: the first piece of an EDL range owns words from a−0.6 s. Words starting in the last 0.12 s of the EDL range belong to the next sentence.
- Texts and B-roll are clamped to their block, so they never spill into the next scene: texts end ≤ block_end−3 frames, B-roll ≤ block_end−8.
- End card: a 3.6 s flash-in with the title, a script sub-line, address, phone, a "24-hour inpatient" line and the client's IG handle.

### Editorial decisions

- 12 min of footage was cut to ≤3 min. Removed: the tissue-welding device, the thermostat block, the lab-assistant line, a take with swearing in the lab, and the sterilisation/instrument talk.
- The order follows the tour route.
- B&W live moments: two clinic cats, each with a playful spoken line and a tag (e.g. "<cat> is not in the mood").

### Client feedback that applies to all future reels

1. Hold 0.5–1 s after speech ends. Never chop a phrase.
2. Captions and context plates go at the **bottom**, above the IG UI.
3. Always add a light music bed: silence or room noise distracts.

## ElevenLabs models with Ukrainian (account check, 2026-11-17; Creator plan = 300k credits/month)
| model_id | cost × | note |
|---|---|---|
| eleven_v4, eleven_v3, eleven_multilingual_v2 | 1.0 | full price |
| eleven_v4_turbo, eleven_v3_conversational, eleven_flash_v2_5, eleven_turbo_v2_5 | 0.5 | half price; all return with-timestamps alignment |

Deepgram check of «…Крок перший: накрийтеся ковдрою» in a Ukrainian library voice: v4 / v4_turbo / v3_conversational said «накрийтеся»
correctly; flash_v2_5 and turbo_v2_5 said «накритися» (wrong verb form). One 40 s episode ≈ 900 characters.
Let the human pick voice AND model by ear (auditions in projects/<id>/tts/audition_*.mp3).
