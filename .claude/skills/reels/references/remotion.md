# Remotion in this repo

- **Precedence:** the `reels` skill owns the workflow. The official `remotion-*` skills are API reference only — ignore
  their "create a new project" (remotion-create / `npx create-video`) and "don't render by default" defaults here.
- Version 4.0.543, one project in `toolkit/reel` (one node_modules for all reels). Media is per project via
  `--public-dir=projects/<id>/public` (render.py passes it). Official agent skills: `.claude/skills/remotion-*` (installed by SETUP.md)
  (`remotion-interactivity` = rules for Studio-editable markup; `remotion-render`, `remotion-captions`, `remotion-docs`…).
- **Licence**: free for individuals and companies with ≤3 people, commercial use included. A client that only receives
  an MP4 doesn't need a licence. Bigger company → check remotion.pro/license (details + links in research.md §2).

## Studio (visual editing for the owner)
`python toolkit/py/render.py projects/<id> --studio` → browser; pick composition `<id>`. Click any clip/title in the
timeline → props panel: texts, transition type, B&W, zoom, voice fades/gain, caption words. Drag to move/trim.
Studio writes changes back into `src/projects/<id>.tsx` → that file becomes the source of truth
(re-running gen_tsx.py overwrites it — ask the owner first; copy the .tsx aside or commit first).
Limits: the music bed ducking is pre-computed (moving clips doesn't re-duck → re-run music.py after big moves);
renders of the editable composition are slower than a data-driven one.

## Rules for Studio-editable markup (verified on 4.0.543)
- Flat JSX, literal props inline (no `.map()` over data) — that's why gen_tsx emits one element per item.
- `Interactive.create({Component, layout: "none"|"absolute-fill", componentName, schema})`; schema field types used:
  string, number (needs `hiddenFromList`), boolean, enum (`variants: {a: {}, …}`), asset (`assetType`), `Interactive.captionsSchema`.
- `<Track name>` groups rows in the timeline; `<Sequence name from durationInFrames trimBefore>` per shot.
- Inside a trimmed Sequence `useCurrentFrame()` = local + trim; use `useShotClock()` from elements.tsx.
- `@remotion/media` `<Video>`/`<Audio>` (not OffthreadVideo) for the editable composition.

## Gotchas
- Cover `<Still>` ignored trimBefore on video → cover background is a jpg extracted by gen_tsx.
- Fonts must be loaded with delayRender/continueRender (done in `<Brand>`); variable Montserrat works in Chrome.
- Default output colour tags are yuvj420p/pc/bt470bg → render.py passes `--color-space=bt709` (tv range, bt709).
- Full render ~10 min at concurrency 8; preview `--scale=0.5` for checks.
