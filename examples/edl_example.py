"""EXAMPLE edit decision list (anonymized from a real ~3 min clinic-tour reel). Copy to projects/<id>/edl.py and replace
everything: clip ids come from YOUR footage (file stem minus clip_prefix), times from YOUR transcripts/ + sheets/.
All times are SOURCE seconds in the given clip. build.py turns this into a frame timeline and snaps every range edge to
the real voice (spectral VAD) — rough whisper-ish times are fine.

block keys:
  clip, ranges=[(a,b),...]   spoken ranges; pauses > 0.5 s inside are tightened automatically.
                              Ranges that touch (gap <= 0.06 s) = same take split for a visual change (bw / punch-in).
  trans                       transition INTO this block: cut | whip | zoom | flash
  section                     small "// tag" shown at block start (room / topic name)
  broll=[(clip, src_in, dur, at_src)]  cutaway video over the voice (voice keeps playing); at_src = time in THIS block's clip
  texts=[dict(kind=..., at=src_time, dur=sec, ...)]
        kind="kinetic" lines=[("BIG CAPS","bold"), ("handwritten","script")]   (captions are hidden under it)
        kind="lower3" title=, sub=   name plate        kind="pin" title=, sub=   address plate
        kind="tag" text=, pos="left"|"right"
  bw=[(a,b)]                  'live moment' spans rendered black & white
"""

# Hook: 5-7 striking 0.6 s shots + kinetic title. HOOK = None -> voice-first opening (often better for <= 60 s reels).
HOOK = dict(
    shots=[("2403", 0.3), ("2364", 50.6), ("2399", 2.2), ("2374", 0.6), ("2366", 0.3), ("2368", 1.0)],
    shot_dur=0.6,
    title=dict(kind="kinetic", lines=[("ЕКСКУРСІЯ", "bold"), ("клінікою <Назва>", "script")]),
)

BLOCKS = [
    # ── Intro: host at the entrance, name plate ──
    dict(clip="2403", ranges=[(3.0, 17.3)], trans="flash",
         texts=[dict(kind="lower3", at=5.2, dur=4.2, title="<Ім'я Прізвище>", sub="<посада · посада>")]),
    # ── Topic 1: reception — section tag, address plate, a person tag ──
    dict(clip="2404", ranges=[(0.55, 11.55)], trans="whip", section="<відділення>",
         texts=[dict(kind="pin", at=6.5, dur=4.0, title="<вул. Назва, 1>", sub="<Місто>"),
                dict(kind="tag", at=10.3, dur=3.2, text="адміністратор", pos="right")]),
    # ── Topic 2: two ranges = one jump cut (alternating punch-in is automatic); b-roll over the voice ──
    dict(clip="2407", ranges=[(3.2, 9.95), (12.75, 17.0)], trans="zoom", section="кабінет №1",
         broll=[("2410", 0.2, 1.4, 8.4)]),
    # ── A claim with a number → kinetic title at the moment it is said ──
    dict(clip="2413", ranges=[(7.5, 11.35), (24.15, 29.5)], trans="cut",
         texts=[dict(kind="kinetic", at=7.9, dur=3.3, lines=[("2 ЛІКАРІ", "bold"), ("та 2 асистенти", "script")])]),
    # ── The strongest department gets the most time: many ranges, several titles, b-roll ──
    dict(clip="2364", trans="zoom",
         ranges=[(0.45, 5.0), (5.45, 12.0), (44.7, 53.25), (72.3, 81.5)],
         broll=[("2366", 0.1, 1.8, 6.6)],
         texts=[dict(kind="kinetic", at=2.5, dur=2.5, lines=[("ХІРУРГІЯ", "bold"), ("святая святих", "script")]),
                dict(kind="tag", at=6.6, dur=3.0, text="стоматологія", pos="left"),
                dict(kind="kinetic", at=79.2, dur=2.3, lines=[("БЕЗПЕКА", "bold"), ("наших пацієнтів", "script")])]),
    # ── Live moments in black & white (touching ranges split the same take for the B&W switch) ──
    dict(clip="2376", ranges=[(13.0, 17.5), (17.55, 19.85), (19.85, 34.7)], trans="cut",
         bw=[(17.55, 19.95)],
         texts=[dict(kind="tag", at=17.6, dur=2.3, text="живі моменти", pos="left")]),
    # ── Outro: teaser ──
    dict(clip="2414", ranges=[(0.55, 13.1)], trans="whip",
         texts=[dict(kind="kinetic", at=5.3, dur=2.9, lines=[("СКОРО", "bold"), ("<новинка>", "script")])]),
]

# End card over a still frame of `clip` at `src`: name, sub, 3 lines (address / phone / key promise), handle.
# Only facts confirmed by the client or seen in the footage — list the rest as open questions.
END = dict(clip="2403", src=0.3, dur=3.6,
           title="<Назва>", sub="<хто ви · місто>",
           lines=["<адреса>", "<телефон>", "<головна обіцянка>"], handle="@<handle>")

# caption text fixes: whisper word -> correct spelling ("" = drop the word from captions)
FIX = {"Айдекс": "IDEXX", "СДМА,": "SDMA,"}
