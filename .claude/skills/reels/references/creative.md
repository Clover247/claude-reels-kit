# Creative playbook (what made the first clinic-tour reel work — adapt, don't copy blindly)

## Structure of a "tour / about us" reel (≤ 3:00)
1. **Hook 3–4 s**: 5–7 most striking shots × 0.6 s (surgical light, sleepy patient, equipment close-up, cat),
   tick SFX on each cut, kinetic title over it ("ЕКСКУРСІЯ / клінікою <Назва>"). No talking in the hook.
2. **Flash → host intro**: the speaker at the entrance; name plate (lower third: name + role).
3. **Blocks = rooms/topics**, each opens with a transition (whip / zoom) + `// section` tag (room name).
   Inside a block: jump cuts with alternating punch-in (1.0 ↔ 1.12) so cuts feel intentional.
4. **Big claims as kinetic titles** at the moment they are said: numbers and differentiators
   ("2 ТЕРАПЕВТИ / та 2 асистенти", "24/7", "ВЛАСНА / лабораторія", "БЕЗПЕКА / наших пацієнтів"). Captions hide under them.
5. **B-roll over the voice** where the speaker names equipment ("мікроскоп", "аналізатор", "стоматологія") — 1.5–3 s,
   never across a transition, never more than ~25% of the runtime.
6. **Live moments in B&W** (client asked: "живі моменти в ч/б"): unscripted warm bits — petting a patient, a cat
   refusing to cooperate; `// живі моменти` tag, light grain. Two or three are enough.
7. **Outro**: future/teaser ("СКОРО / рентген-установка"), then **end card** 3.6 s: name, sub, address, phone,
   one key promise, handle. Flash into it.

## Short form (15–60 s, one topic — e.g. "new X-ray machine")
Research optimum for informational Reels is ~21–34 s (research.md §6); ≤ 60 s if the brief says so.
- 0–3 s: hook = the payoff first. Either a 3–4 shot montage (≤2 s) with a kinetic title, or voice-first
  (`HOOK = None`): open on the strongest sentence + kinetic title over it. No slow intros, no "Доброго дня".
- 1 speaker block (name plate only if the name is heard/confirmed) → 1–2 content blocks → 2–2.5 s end card.
- 1–2 kinetic titles total (the key claim / number), not one per sentence.
- Equipment/product showcase: B-roll can be 40–60% of the runtime (the 25% rule is for talking-head tours).
- Cut harder: every sentence must earn its place; jump cuts every 2–4 s; transitions only between ideas.
- End on a CTA line from the brief (book / call / visit) + handle.

## Editing judgement
- Cut what a viewer doesn't need: repeated phrasings, "ну", false starts, long walking with no info, mic rub.
  Prefer complete sentences; a cut mid-sentence must land in a real pause (the build handles the exact point).
- Keep personality: a joke or a pet reacting is worth 2 s even if it carries no info.
- One idea per block; ~10–40 s per block; the most impressive department gets the most time (surgery here).
- Read the room for facts: door signs, certificates, equipment brands (IDEXX…) are visible in footage — use them, but
  flag anything contradicting the brief.

## Text styles (reference reel: bold caps + handwritten accent + `//` labels)
- Kinetic: brand sans 900 caps (124 px, 92 px if >11 chars), light colour with dark drop-shadow, spring scale-in;
  script accent (Marck Script, Cyrillic-capable) in accent colour, −4°, wipe reveal. Centered in the hook, bottom elsewhere.
- Captions: 1–3 words, active word in accent colour, bottom. Fix brand spellings via FIX.
- Plates: white card, dark left border, title 800 / sub 600; address variant with a pin icon.
- Section tag: dark pill with accent `//`. Tags left/right for people ("// адміністратор") and moments.
- Everything above the bottom ~420 px (Instagram UI) and inside 1080×1440 centre for the cover.

## Transitions & sound design
- whip (fast pan + blur), zoom (scale + blur), flash (white), pop (b-roll in/out). Whoosh SFX on whip/zoom/flash,
  pop SFX on titles, tick on hook cuts — all synthesized in build.py (no licensing).
- Music: calm, steady, no vocals, 80–100 BPM for informational content; full level only in hook/pauses/end card.

## Ideas not used yet (from the reference reel)
- B-roll inside a framed inset over a textured background (paper grid, fur).
- Photo cut-outs pinned over the speaker. Highlighted single word inside a `//` label.
