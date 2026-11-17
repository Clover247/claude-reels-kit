"""Create a new reel project.
Usage: python new_project.py <id> <samples_dir> [--brand <client>] [--prefix IMG_] [--title "..."] [--max 60]
  (Git Bash: quote Windows paths or use forward slashes: "D:/clients/x")
  id          lowercase-with-dashes, e.g. clinic-xray-2026-12  (becomes the Remotion composition id)
  samples_dir folder with the raw footage (left where it is, never modified)
  --brand     brands/<client>/brand.json; created from brands/_example if missing -> EDIT colours/fonts!
Creates projects/<id>/project.json + edl.py (template). Next: python toolkit/py/ingest.py projects/<id>
"""
import argparse, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("id"); ap.add_argument("samples")
ap.add_argument("--brand", default=None); ap.add_argument("--prefix", default=""); ap.add_argument("--title", default="")
ap.add_argument("--max", type=int, default=180, help="max seconds from the brief (default 180 = Reels limit)")
a = ap.parse_args()
if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.id):
    sys.exit("id must be lowercase letters/digits separated by dashes")
d = ROOT / "projects" / a.id
if d.exists():
    sys.exit(f"{d} already exists")
brand = a.brand or a.id.split("-")[0]
bdir = ROOT / "brands" / brand
if not (bdir / "brand.json").exists():
    shutil.copytree(ROOT / "brands" / "_example", bdir, ignore=shutil.ignore_patterns("*.jpg", "*.png"))
    b = json.load(open(bdir / "brand.json", encoding="utf-8")); b["name"] = brand; b["instagram"] = ""
    json.dump(b, open(bdir / "brand.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"!! created brands/{brand}/brand.json from brands/_example — set the client's real colours/fonts/handle")
d.mkdir(parents=True)
cfg = {
    "id": a.id, "title": a.title or a.id, "client": brand, "brand": f"brands/{brand}/brand.json",
    "samples": str(os.path.abspath(a.samples)).replace("\\", "/"), "clip_prefix": a.prefix, "fps": 30,
    "language": "uk", "whisper_prompt": "", "max_seconds": a.max, "music": "toolkit/music/City Sunshine.mp3",
    "labels": {}, "fit": {}, "cover": {"clip": "", "at": 1.0, "title": "", "script": "", "line": ""},
}
json.dump(cfg, open(d / "project.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
(d / "edl.py").write_text('''"""Edit decision list. All times are SOURCE seconds in the given clip (see transcripts/ + sheets/).
Reference implementation: examples/edl_example.py.  build.py turns this into a frame timeline.

block keys:
  clip, ranges=[(a,b),...]   spoken ranges; pauses > 0.5 s inside are tightened automatically; ends/starts are
                              snapped to the real voice (spectral VAD) — give whisper-ish times, the tool refines them.
                              Ranges that touch (gap <= 0.06 s) = same take split for a visual change (bw / punch-in).
  trans                       transition INTO this block: cut | whip | zoom | flash
  section                     small "// tag" at block start (room / department name)
  broll=[(clip, src_in, dur, at_src)]   cutaway over the voice (voice keeps playing); at_src = time in THIS block's clip
  texts=[dict(kind=..., at=src_time, dur=sec, ...)]
        kind="kinetic" lines=[("BIG CAPS","bold"), ("handwritten","script")]   (captions are hidden under it)
        kind="lower3" title=, sub=        name plate      kind="pin" title=, sub=   address plate
        kind="tag" text=, pos="left"|"right"
  bw=[(a,b)]                  'live moment' spans in black & white
"""

HOOK = dict(
    shots=[],            # [(clip, src_second), ...] 5-7 punchy 0.6 s shots.  HOOK = None -> voice-first opening
    shot_dur=0.6,
    title=dict(kind="kinetic", lines=[("TITLE", "bold"), ("subtitle", "script")]),
)

BLOCKS = [
    # dict(clip="", ranges=[(0.0, 5.0)], trans="flash", texts=[]),
]

END = dict(clip="", src=0.0, dur=3.6, title="", sub="", lines=["", "", ""], handle="")

FIX = {}   # caption spelling fixes: whisper word -> correct text ("" = drop)
''', encoding="utf-8")
(d / "NOTES.md").write_text(f"""# {a.id} - status

Brief (owner's words, verbatim):

Reference / style:

## Versions
- v1 -

## Open with the owner / client
-

## Decisions & why
-
""", encoding="utf-8")
print(f"created {d}\nnext: python toolkit/py/ingest.py projects/{a.id}")
