# Definition of done — check every item before telling the owner it's ready

| # | Check | How |
|---|---|---|
| 1 | Duration within brief and ≤ 3:00 | `build.py --plan`, render.py prints it |
| 2 | No word chopped at a cut; ≥0.25 s natural tail where a phrase ends | `cut_audit.py` (Read the png: red cut after cyan decay), `verify_words.py` → 0 real "AT CUT" (confirm suspects with an isolated snippet) |
| 3 | No next-sentence fragment leaking ("Це", "Також" start) | verify_words + cut_audit (cut before the next onset) |
| 4 | Captions: correct words, brand spellings, none under big titles, none for words that aren't heard | Read `stills/review_*.jpg`; gen_tsx prints hidden words |
| 5 | Captions/plates at the bottom, above the IG UI zone, not overlapping each other | review sheet |
| 6 | Transitions: no black edges, B-roll/tags don't cross a transition | review sheet (whip-in/out frames) |
| 7 | Facts on screen verified (names, address, phone, hours, claims) | list unverified ones in the report |
| 8 | Audio: voice clean (rustle repaired), music audible but under speech, no music-only silence gaps | measure; tell the owner which timecodes to check by ear |
| 9 | Loudness −14 LUFS integrated, true peak ≤ −1.5 dBTP | render.py prints it |
| 10 | Export: 1080×1920, 30 fps, H.264 High yuv420p bt709, AAC 48 kHz, faststart, ~10 Mbps | render.py; `ffprobe` |
| 11 | Cover: text inside centre 1080×1440 (4:5 grid crop), readable | Read `out/<id>_cover.jpg` |
| 12 | Studio project opens (`render.py <p> --studio`) and the TSX type-checks (`npx tsc --noEmit` in toolkit/reel) | |

Report format (Ukrainian, short): files → what changed → what was verified and how → what to check by ear (timecodes)
→ open questions / unverified facts → how to tweak (Studio / edl.py). Don't claim what you didn't measure or look at.
