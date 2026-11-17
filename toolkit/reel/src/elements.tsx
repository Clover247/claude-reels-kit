// Reusable, Studio-editable building blocks for vertical reels (any brand: see <Brand>).
// Every component is wrapped with Interactive.create so its props show up in Remotion Studio.
import React, { useContext, useEffect, useState } from "react";
import {
  AbsoluteFill, Easing, Img, Interactive, Internals, continueRender, delayRender, interpolate,
  spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { Audio, Video } from "@remotion/media";

// ── brand (colours + fonts) comes from the project's brand.json via <Brand value={...}> ──
export type BrandT = {
  name?: string;
  colors: { dark: string; mid: string; accent: string; pale: string; light: string };
  fonts: { sans: { family: string; file: string; weight?: string }; script: { family: string; file: string } };
};
export const DEFAULT_BRAND: BrandT = {
  colors: { dark: "#1F3D7A", mid: "#3D6BB3", accent: "#8FCBF5", pale: "#E7F1FB", light: "#FFFFFF" },
  fonts: { sans: { family: "Montserrat", file: "Montserrat.ttf", weight: "100 900" }, script: { family: "MarckScript", file: "MarckScript.ttf" } },
};
const BrandCtx = React.createContext<BrandT>(DEFAULT_BRAND);
const useB = () => {
  const b = useContext(BrandCtx);
  return { C: b.colors, SANS: b.fonts.sans.family, SCRIPT: b.fonts.script.family };
};
const H = 7; // transition half-length (frames)

/** Wrap a whole composition: provides brand tokens and blocks rendering until the brand fonts (public/fonts/) load. */
export const Brand: React.FC<{ value: BrandT; children: React.ReactNode }> = ({ value, children }) => {
  const [handle] = useState(() => delayRender("fonts"));
  useEffect(() => {
    const { sans, script } = value.fonts;
    const faces = [
      new FontFace(sans.family, `url(${staticFile("fonts/" + sans.file)})`, sans.weight ? { weight: sans.weight } : {}),
      new FontFace(script.family, `url(${staticFile("fonts/" + script.file)})`),
    ];
    Promise.all(faces.map((f) => f.load())).then((ls) => {
      ls.forEach((f) => (document as any).fonts.add(f));
      continueRender(handle);
    });
  }, [handle, value]);
  return <BrandCtx.Provider value={value}>{children}</BrandCtx.Provider>;
};

/** Local clock of the enclosing shot Sequence, even when it uses trimBefore (frame = source frame inside). */
const useShotClock = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const ctx = useContext(Internals.SequenceContext);
  const trim = -(ctx?.cumulatedNegativeFrom ?? 0);
  return { local: frame - trim, dur: durationInFrames - trim, frame };
};

const transEnum = (def: string, description: string) => ({
  type: "enum" as const, default: def, description,
  variants: { cut: {}, whip: {}, zoom: {}, pop: {} },
});

// ── Shot: footage with punch-in zoom, B&W 'live moment' look and in/out transitions ──
const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: 0.35 }}>
      <svg width="100%" height="100%">
        <filter id={`g${f}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.abs(f) % 50} />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g${f})`} />
      </svg>
    </AbsoluteFill>
  );
};

const ShotInner: React.FC<{ src: string; zoom: number; bw: boolean; transIn: string; transOut: string }> = ({
  src, zoom, bw, transIn, transOut,
}) => {
  const { local, dur } = useShotClock();
  let tx = 0, scale = zoom * interpolate(local, [0, Math.max(1, dur)], [1, 1.035]), blur = 0, opacity = 1;
  if (transIn === "whip" && local < H) { const p = Easing.out(Easing.cubic)(local / H); tx = (1 - p) * 300; blur = (1 - p) * 30; scale *= 1 + (1 - p) * 0.4; }
  if (transOut === "whip" && local >= dur - H) { const p = Easing.in(Easing.cubic)((local - (dur - H)) / H); tx = -p * 300; blur = p * 30; scale *= 1 + p * 0.4; }
  if (transIn === "zoom" && local < H) { const p = Easing.out(Easing.cubic)(local / H); scale *= 1 + (1 - p) * 0.55; blur = (1 - p) * 20; }
  if (transOut === "zoom" && local >= dur - H) { const p = Easing.in(Easing.cubic)((local - (dur - H)) / H); scale *= 1 + p * 0.55; blur = p * 20; }
  if (transIn === "pop") { const p = Easing.out(Easing.cubic)(Math.min(1, local / 9)); scale *= 1.14 - 0.14 * p; opacity = Math.min(1, local / 4); }
  if (transOut === "pop") { opacity *= interpolate(local, [dur - 5, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }); }
  const filter = [blur > 0.3 ? `blur(${blur}px)` : "", bw ? "grayscale(1) contrast(1.25) brightness(1.05)" : ""].join(" ").trim();
  return (
    <>
      <AbsoluteFill style={{ overflow: "hidden", opacity }}>
        <Video src={staticFile(src)} muted objectFit="cover"
          style={{ width: "100%", height: "100%", translate: `${tx}px 0px`, scale: `${scale}`, filter: filter || undefined }} />
        {bw && <Grain />}
      </AbsoluteFill>
    </>
  );
};

export const Shot = Interactive.create({
  Component: ShotInner,
  layout: "absolute-fill",
  componentName: "Shot",
  schema: {
    src: { type: "asset", assetType: "video", default: "", description: "Відео" },
    zoom: { type: "number", default: 1, min: 1, max: 2, step: 0.01, description: "Наближення (punch-in)", hiddenFromList: false },
    bw: { type: "boolean", default: false, description: "Ч/Б «живий момент»" },
    transIn: transEnum("cut", "Перехід на вході"),
    transOut: transEnum("cut", "Перехід на виході"),
  },
});

// ── Captions: 1-3 words per page, current word highlighted. Caption times are SOURCE ms of the shot's clip. ──
type Cap = { text: string; startMs: number; endMs: number; timestampMs: number | null; confidence: number | null };
const paginate = (caps: Cap[]) => {
  const pages: Cap[][] = [];
  let cur: Cap[] = [];
  for (const c of caps) {
    const joined = cur.map((x) => x.text.trim()).concat(c.text.trim()).join(" ");
    const last = cur[cur.length - 1];
    if (cur.length && (cur.length >= 3 || joined.length > 22 || c.startMs - last.endMs > 300 || /[.,?!:]$/.test(last.text.trim()))) {
      pages.push(cur); cur = [];
    }
    cur.push(c);
  }
  if (cur.length) pages.push(cur);
  return pages;
};

const CaptionsInner: React.FC<{ captions: Cap[]; style?: React.CSSProperties }> = ({ captions, style }) => {
  const { C, SANS, SCRIPT } = useB();
  const { frame } = useShotClock();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const pages = paginate(captions ?? []);
  const idx = pages.findIndex((p, i) => ms >= p[0].startMs - 40 && ms < Math.min(pages[i + 1]?.[0].startMs ?? Infinity, p[p.length - 1].endMs + 500));
  if (idx < 0) return null;
  const page = pages[idx];
  const age = (ms - page[0].startMs) / 1000 * fps;
  const sp = interpolate(age, [0, 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", top: 1470, left: 60, right: 60, ...style }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 18, rowGap: 4,
        fontFamily: SANS, fontWeight: 700, fontSize: 58, lineHeight: 1.2, color: C.light,
        textShadow: "0 3px 0 rgba(0,0,0,.35), 0 0 24px rgba(0,0,0,.55)", opacity: sp, translate: `0px ${(1 - sp) * 14}px` }}>
        {page.map((w, i) => {
          const active = ms >= w.startMs && ms < (page[i + 1]?.startMs ?? Infinity);
          return <div key={i} style={{ color: active ? C.accent : C.light }}>{w.text.trim()}</div>;
        })}
      </div>
    </div>
  );
};

export const Captions = Interactive.create({
  Component: CaptionsInner,
  layout: "none",
  componentName: "Captions",
  schema: { ...Interactive.captionsSchema },
});

// ── Kinetic title: BOLD caps + handwritten accent ──
const KineticInner: React.FC<{ bold: string; script: string; scriptDelay: number; centered: boolean; style?: React.CSSProperties }> = ({
  bold, script, scriptDelay, centered, style,
}) => {
  const { C, SANS, SCRIPT } = useB();
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const out = interpolate(f, [durationInFrames - 7, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const sp = spring({ frame: f, fps, config: { damping: 12, stiffness: 170 } });
  const p = interpolate(f - scriptDelay - (bold ? 4 : 0), [0, 14], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: centered ? "center" : "flex-end", paddingBottom: centered ? 0 : 470, opacity: out, ...style }}>
      {!centered && <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(10,25,60,.55) 0%, rgba(10,25,60,0) 45%)" }} />}
      {bold ? (
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: bold.length > 11 ? 92 : 124, color: C.light, letterSpacing: -1,
          textTransform: "uppercase", lineHeight: 1, scale: `${0.5 + 0.5 * sp}`, opacity: Math.min(1, sp * 2),
          textShadow: `0 6px 0 ${C.dark}, 0 10px 40px rgba(0,0,0,.45)`, textAlign: "center", padding: "0 40px" }}>{bold}</div>
      ) : null}
      {script ? (
        <div style={{ fontFamily: SCRIPT, fontSize: 92, color: C.accent, marginTop: -6, rotate: "-4deg",
          clipPath: `inset(-20% ${100 - p}% -20% 0)`, textShadow: "0 4px 22px rgba(0,0,0,.5)", textAlign: "center", padding: "0 30px" }}>{script}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export const Kinetic = Interactive.create({
  Component: KineticInner,
  layout: "none",
  componentName: "Kinetic",
  schema: {
    bold: { type: "string", default: "", description: "Великий текст (капс)" },
    script: { type: "string", default: "", description: "Рукописний акцент" },
    scriptDelay: { type: "number", default: 0, min: 0, step: 1, description: "Затримка акценту (кадри)", hiddenFromList: false },
    centered: { type: "boolean", default: false, description: "По центру (для хука)" },
  },
});

// ── Lower third / address pin ──
const CardInner: React.FC<{ title: string; sub: string; pin: boolean; style?: React.CSSProperties }> = ({ title, sub, pin, style }) => {
  const { C, SANS, SCRIPT } = useB();
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const sp = spring({ frame: f, fps, config: { damping: 20, stiffness: 120 } });
  const sp2 = spring({ frame: f - 5, fps, config: { damping: 20, stiffness: 120 } });
  const out = interpolate(f, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 64, bottom: 470, opacity: out, ...style }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, background: C.light, borderRadius: 22,
        padding: "20px 34px 20px 24px", boxShadow: "0 12px 40px rgba(0,0,0,.28)",
        translate: `${(1 - sp) * -120}px 0px`, opacity: sp, borderLeft: `10px solid ${C.dark}` }}>
        {pin && (
          <svg width="46" height="58" viewBox="0 0 24 30">
            <path d="M12 0C5.4 0 0 5.2 0 11.7 0 20.4 12 30 12 30s12-9.6 12-18.3C24 5.2 18.6 0 12 0z" fill={C.dark} />
            <circle cx="12" cy="11.5" r="4.6" fill={C.light} />
          </svg>
        )}
        <div>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 54, color: C.dark, lineHeight: 1.1 }}>{title}</div>
          <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 32, color: C.mid, marginTop: 8, maxWidth: 820,
            opacity: sp2, translate: `0px ${(1 - sp2) * 10}px` }}>{sub}</div>
        </div>
      </div>
    </div>
  );
};

export const Card = Interactive.create({
  Component: CardInner,
  layout: "none",
  componentName: "Card",
  schema: {
    title: { type: "string", default: "", description: "Заголовок" },
    sub: { type: "string", default: "", description: "Підпис" },
    pin: { type: "boolean", default: false, description: "Іконка локації" },
  },
});

// ── "// tag" pill: section label (top-left) or callout (middle) ──
const TagInner: React.FC<{ text: string; variant: string; style?: React.CSSProperties }> = ({ text, variant, style }) => {
  const { C, SANS, SCRIPT } = useB();
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const sp = spring({ frame: f, fps, config: { damping: 16, stiffness: 150 } });
  const out = interpolate(f, [durationInFrames - 7, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const section = variant === "section";
  const right = variant === "right";
  const pos: React.CSSProperties = right ? { right: 64, bottom: 470 } : { left: 64, bottom: 470 };
  return (
    <div style={{ position: "absolute", ...pos, opacity: out, ...style }}>
      <div style={{ fontFamily: SANS, fontWeight: section ? 700 : 600, fontSize: section ? 44 : 40,
        color: section ? C.light : C.dark, background: section ? `${C.dark}D9` : C.light,
        padding: section ? "12px 28px" : "12px 26px", borderRadius: section ? 14 : 40, boxShadow: "0 8px 30px rgba(0,0,0,.28)",
        translate: section ? `${(1 - sp) * -80}px 0px` : undefined, scale: section ? undefined : `${0.6 + 0.4 * sp}`,
        transformOrigin: right ? "right center" : "left center" }}>
        <span style={{ color: section ? C.accent : C.mid, fontWeight: 800 }}>// </span>{text}
      </div>
    </div>
  );
};

export const Tag = Interactive.create({
  Component: TagInner,
  layout: "none",
  componentName: "Tag",
  schema: {
    text: { type: "string", default: "", description: "Текст" },
    variant: { type: "enum", default: "left", description: "Позиція", variants: { section: {}, left: {}, right: {} } },
  },
});

// ── End card ──
const EndCardInner: React.FC<{ title: string; sub: string; line1: string; line2: string; line3: string; handle: string }> = ({
  title, sub, line1, line2, line3, handle,
}) => {
  const { C, SANS, SCRIPT } = useB();
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = (d: number) => spring({ frame: f - d, fps, config: { damping: 16, stiffness: 120 } });
  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${C.dark}EE 0%, ${C.mid}D9 100%)`, alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", color: C.light, fontFamily: SANS }}>
        <div style={{ fontWeight: 900, fontSize: 112, letterSpacing: -2, scale: `${0.7 + 0.3 * a(0)}`, opacity: a(0) }}>{title}</div>
        <div style={{ fontFamily: SCRIPT, fontSize: 70, color: C.accent, marginTop: -4, opacity: a(5) }}>{sub}</div>
        <div style={{ width: 140, height: 4, background: C.accent, margin: "40px auto", borderRadius: 2, scale: `${a(8)} 1` }} />
        {[line1, line2, line3].filter(Boolean).map((l, i) => (
          <div key={i} style={{ fontWeight: 600, fontSize: 48, margin: "14px 0", opacity: a(10 + i * 4), translate: `0px ${(1 - a(10 + i * 4)) * 20}px` }}>{l}</div>
        ))}
        <div style={{ fontWeight: 500, fontSize: 38, color: C.pale, marginTop: 40, opacity: a(24) }}>{handle}</div>
      </div>
    </AbsoluteFill>
  );
};

export const EndCard = Interactive.create({
  Component: EndCardInner,
  layout: "absolute-fill",
  componentName: "EndCard",
  schema: {
    title: { type: "string", default: "", description: "Назва" },
    sub: { type: "string", default: "", description: "Підзаголовок" },
    line1: { type: "string", default: "", description: "Рядок 1" },
    line2: { type: "string", default: "", description: "Рядок 2" },
    line3: { type: "string", default: "", description: "Рядок 3" },
    handle: { type: "string", default: "", description: "Інстаграм" },
  },
});

// ── White flash over a cut ──
const FlashInner: React.FC = () => {
  const { C, SANS, SCRIPT } = useB();
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const mid = Math.round(durationInFrames * 0.3);
  const o = interpolate(f, [0, mid, durationInFrames], [0, 0.95, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ backgroundColor: C.light, opacity: o }} />;
};

export const Flash = Interactive.create({ Component: FlashInner, layout: "absolute-fill", componentName: "Flash", schema: {} });

// ── Voice: the shot's own audio with short fades so mid-phrase cuts don't chop ──
const VoiceInner: React.FC<{ src: string; fadeIn: number; fadeOut: number; gain: number }> = ({ src, fadeIn, fadeOut, gain }) => {
  const { local, dur } = useShotClock();
  const fi = fadeIn > 0 ? interpolate(local, [0, fadeIn], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  const fo = fadeOut > 0 ? interpolate(local, [dur - fadeOut, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  return <Audio src={staticFile(src)} volume={gain * fi * fo} />;
};

export const Voice = Interactive.create({
  Component: VoiceInner,
  layout: "absolute-fill",
  componentName: "Voice",
  schema: {
    src: { type: "asset", assetType: "audio", default: "", description: "Аудіо" },
    fadeIn: { type: "number", default: 0, min: 0, max: 30, step: 1, description: "Fade-in (кадри)", hiddenFromList: false },
    fadeOut: { type: "number", default: 0, min: 0, max: 30, step: 1, description: "Fade-out (кадри)", hiddenFromList: false },
    gain: { type: "number", default: 1, min: 0, max: 2, step: 0.05, description: "Гучність", hiddenFromList: false },
  },
});

// ── Reel cover (Still). Text kept inside the centre 1080x1440 so it survives the 4:5 profile-grid crop. ──
const CoverInner: React.FC<{ bg: string; title: string; script: string; line: string; style?: React.CSSProperties }> = ({ bg, title, script, line, style }) => {
  const { C, SANS, SCRIPT } = useB();
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", ...style }}>
      <Img src={staticFile(bg)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill style={{ background: `linear-gradient(to bottom, ${C.dark}00 45%, ${C.dark}E0 80%)` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 330 }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: title.length > 10 ? 110 : 136, color: C.light, letterSpacing: -2,
          textShadow: `0 7px 0 ${C.dark}, 0 12px 40px rgba(0,0,0,.4)`, textAlign: "center", padding: "0 40px" }}>{title}</div>
        <div style={{ fontFamily: SCRIPT, fontSize: 96, color: C.accent, transform: "rotate(-4deg)", marginTop: -4,
          textShadow: "0 4px 22px rgba(0,0,0,.5)", textAlign: "center" }}>{script}</div>
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 40, color: C.pale, marginTop: 34, textAlign: "center" }}>{line}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export const CoverCard = Interactive.create({
  Component: CoverInner,
  layout: "none",
  componentName: "CoverCard",
  schema: {
    bg: { type: "string", default: "cover_bg.jpg", description: "Фон (файл у public/)" },
    title: { type: "string", default: "", description: "Заголовок" },
    script: { type: "string", default: "", description: "Рукописний рядок" },
    line: { type: "string", default: "", description: "Нижній рядок" },
  },
});
