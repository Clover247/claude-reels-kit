"""EXAMPLE episode script for an ANIMATED reel (project.json "type": "anim", no footage). Copy to projects/<id>/script.py.
Voice-over lines + caption styling. Scene choreography lives in toolkit/reel/src/projects/<id>.tsx (hand-written) and
refers to lines by `id` and to words by their text: W("s1", "ковдр") -> frame where that word is spoken.

Markup inside `text` (captions only — stripped before TTS):
  *слово*   brand warm accent      _слово_   cold (blue)      !слово!   danger (red)     ~слово~  ok (green)
  {HEAT|хіт}  show "HEAT" in captions, say "хіт" in the voice-over (pronunciation fix)
`gap` = silence after the line, seconds (pacing; a step change gets a longer beat).
Pipeline: tts.py -> anim_build.py -> (write the episode .tsx with the anim kit) -> music.py -> render.py
"""

LINES = [
    dict(id="hook",   text="Інструкція з виживання в _холодній_ квартирі.", gap=0.55),
    dict(id="s1",     text="Крок перший: накрийтеся *ковдрою.*", gap=0.25),
    dict(id="s1ok",   text="Працює ~чудово.~", gap=0.2),
    dict(id="s1fail", text="Рівно до моменту, коли треба встати по _чай._", gap=0.6),
    dict(id="s2",     text="Крок другий: увімкніть *обігрівач.*", gap=0.25),
    dict(id="s2fail", text="А разом із ним — очікування !рахунку! за світло.", gap=0.6),
    dict(id="final",  text="Крок третій: *кондиціонер* з режимом обігріву *{HEAT|хіт}.*", gap=0.7),
]

END_CARD_SEC = 4.0
