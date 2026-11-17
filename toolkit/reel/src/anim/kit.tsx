// Animation kit for faceless 2D explainer reels (first used for an HVAC company's winter series).
// Flat-vector night interior, a "you" character, props, HUD callouts in the style of TikTok explainers,
// karaoke captions. Everything is drawn in 1080x1920 frame coordinates; the room sits in y 0..1085,
// floor below, captions at y≈1290..1500 (above the Instagram UI zone), HUD at the top (y≥130).
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// ── palette ──
export const PAL = {
  cold: "#5DB8FF", warm: "#FF9A3C", danger: "#FF4D5E", ok: "#3DDC84", yellow: "#FFD23F",
  ink: "#0E1322", panel: "rgba(14,19,34,0.92)", text: "#F4F6FB", dim: "rgba(244,246,251,0.36)",
  skin: "#E9B894", hair: "#2A2A33", sweater: "#3E6FD1", pants: "#26304A", shoe: "#15151C",
  sofa: "#8A3644", sofaHi: "#A2465A", blanket: "#E3A83E", blanketDark: "#C78A26",
};
export const MONO = "Consolas, 'Cascadia Mono', 'Courier New', monospace";
export const SANS = "Montserrat";
export const STYLE_COLOR: Record<string, string> = { warm: PAL.warm, cold: PAL.cold, danger: PAL.danger, ok: PAL.ok, "": PAL.text };

// ── math helpers ──
export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const mix = (c1: string, c2: string, t: number) => {
  const p = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const a = p(c1), b = p(c2);
  return "#" + a.map((v, i) => Math.round(lerp(v, b[i], clamp01(t))).toString(16).padStart(2, "0")).join("");
};
/** 0→1 between frames a..b (eased, clamped) */
export const ramp = (f: number, a: number, b: number, ease = Easing.inOut(Easing.cubic)) =>
  interpolate(f, [a, Math.max(a + 1, b)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
/** visible window with fade in/out (frames) */
export const win = (f: number, a: number, b: number, fade = 5) =>
  f < a || f > b ? 0 : Math.min(1, (f - a) / fade, (b - f) / fade);
export const usePop = (from: number, damping = 12) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return spring({ frame: f - from, fps, config: { damping, stiffness: 180, mass: 0.7 } });
};

// ── camera: cx,cy = world point at screen centre (540,650); s = zoom ──
export type Cam = { cx: number; cy: number; s: number };
export const CAM0: Cam = { cx: 540, cy: 650, s: 1 };
export const camAt = (f: number, keys: [number, Cam][]): Cam => {
  if (f <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [f1, c1] = keys[i];
    const [f0, c0] = keys[i - 1];
    if (f <= f1) {
      const t = Easing.inOut(Easing.cubic)(clamp01((f - f0) / Math.max(1, f1 - f0)));
      return { cx: lerp(c0.cx, c1.cx, t), cy: lerp(c0.cy, c1.cy, t), s: lerp(c0.s, c1.s, t) };
    }
  }
  return keys[keys.length - 1][1];
};
export const camTransform = (c: Cam) => `translate(540 650) scale(${c.s}) translate(${-c.cx} ${-c.cy})`;
export const toScreen = (c: Cam, x: number, y: number) => ({ x: 540 + (x - c.cx) * c.s, y: 650 + (y - c.cy) * c.s });

// ══════════════════════════ ROOM ══════════════════════════
export type RoomState = {
  warmth: number;   // 0 cold blue night … 1 cosy warm
  frost: number;    // frost on the window panes
  tape: number;     // 0..1 insulation tape drawn along the window
  draft: number;    // visible cold drafts from the window
  dim?: number;     // 0..1 lights down (teaser)
};

const Snow: React.FC<{ x: number; y: number; w: number; h: number; n?: number; speed?: number }> = ({ x, y, w, h, n = 46, speed = 1 }) => {
  const f = useCurrentFrame();
  return (
    <g>
      {Array.from({ length: n }).map((_, i) => {
        const sp = (0.8 + ((i * 37) % 10) / 10) * speed;
        const yy = y + ((i * 83 + f * sp * 2.2) % (h + 20)) - 10;
        const xx = x + ((i * 131) % w) + Math.sin((f + i * 20) / 22) * 8;
        const r = 2 + ((i * 7) % 3);
        return <circle key={i} cx={xx} cy={yy} r={r} fill="#fff" opacity={0.55 + ((i * 3) % 4) / 10} />;
      })}
    </g>
  );
};

export const Window: React.FC<{ s: RoomState }> = ({ s }) => {
  const f = useCurrentFrame();
  const X = 640, Y = 330, Wd = 280, Ht = 430, b = 16;
  const frame = mix("#AEB9CB", "#D9CDBE", s.warmth);
  const panes = [[X + b, Y + b, 117, 190], [X + b + 117 + 14, Y + b, 117, 190], [X + b, Y + b + 204, 117, 194], [X + b + 117 + 14, Y + b + 204, 117, 194]];
  const tapeLen = (k: number) => clamp01(s.tape * 4 - k);
  return (
    <g>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#081028" /><stop offset="1" stopColor="#1A2A55" />
        </linearGradient>
        <radialGradient id="frost">
          <stop offset="0" stopColor="#EAF6FF" stopOpacity="0.9" /><stop offset="1" stopColor="#EAF6FF" stopOpacity="0" />
        </radialGradient>
        <clipPath id="glass"><rect x={X + b} y={Y + b} width={Wd - 2 * b} height={Ht - 2 * b} /></clipPath>
      </defs>
      <rect x={X - 6} y={Y - 6} width={Wd + 12} height={Ht + 12} rx={6} fill="#0B0F1C" opacity={0.35} />
      <rect x={X} y={Y} width={Wd} height={Ht} rx={4} fill={frame} />
      <g clipPath="url(#glass)">
        <rect x={X} y={Y} width={Wd} height={Ht} fill="url(#sky)" />
        {/* city */}
        {[[0, 250, 70], [60, 300, 55], [110, 210, 80], [180, 280, 60], [230, 240, 70]].map(([dx, top, w], i) => (
          <g key={i}>
            <rect x={X + b + dx} y={Y + top} width={w} height={Ht} fill="#0D1733" />
            {Array.from({ length: 12 }).map((_, k) => (
              (k * 7 + i * 3) % 4 === 0 ? null :
                <rect key={k} x={X + b + dx + 8 + (k % 3) * 20} y={Y + top + 14 + Math.floor(k / 3) * 26} width={8} height={10}
                  fill={(k + i) % 5 === 0 ? "#FFD27A" : "#2B3A66"} opacity={(k + i) % 5 === 0 ? 0.9 : 1} />
            ))}
          </g>
        ))}
        <Snow x={X} y={Y} w={Wd} h={Ht} />
        {/* frost */}
        {panes.map(([px, py, pw, ph], i) => (
          <g key={i} opacity={s.frost}>
            <ellipse cx={px} cy={py + ph} rx={pw * 0.75} ry={ph * 0.5} fill="url(#frost)" />
            <ellipse cx={px + pw} cy={py} rx={pw * 0.45} ry={ph * 0.35} fill="url(#frost)" />
          </g>
        ))}
      </g>
      {/* mullions */}
      <rect x={X + b + 117} y={Y + b} width={14} height={Ht - 2 * b} fill={frame} />
      <rect x={X + b} y={Y + b + 190} width={Wd - 2 * b} height={14} fill={frame} />
      {/* tape */}
      <g fill="#F2C94C" stroke="#B8902A" strokeWidth={2} opacity={0.97}>
        <rect x={X - 6} y={Y - 6} width={(Wd + 12) * tapeLen(0)} height={22} />
        <rect x={X + Wd - 16} y={Y - 6} width={22} height={(Ht + 12) * tapeLen(1)} />
        <rect x={X + Wd + 6 - (Wd + 12) * tapeLen(2)} y={Y + Ht - 16} width={(Wd + 12) * tapeLen(2)} height={22} />
        <rect x={X - 6} y={Y + Ht + 6 - (Ht + 12) * tapeLen(3)} width={22} height={(Ht + 12) * tapeLen(3)} />
        <rect x={X + b + 113} y={Y + b} width={22} height={(Ht - 2 * b) * tapeLen(3)} />
      </g>
      {/* sill */}
      <rect x={X - 22} y={Y + Ht} width={Wd + 44} height={18} rx={3} fill={mix("#C9D2E0", "#E5D6C2", s.warmth)} />
      {/* drafts */}
      <g opacity={s.draft} fill="none" stroke={PAL.cold} strokeWidth={5} strokeLinecap="round">
        {[0, 1, 2, 3].map((i) => {
          const y0 = Y + 60 + i * 100;
          return (
            <path key={i} d={`M ${X} ${y0} C ${X - 70} ${y0 + 10}, ${X - 110} ${y0 + 60}, ${X - 200 - i * 20} ${y0 + 80}`}
              strokeDasharray="60 40" strokeDashoffset={-(f * 6 + i * 25)} opacity={0.75} />
          );
        })}
      </g>
    </g>
  );
};

export const Door: React.FC<{ warmth: number }> = ({ warmth }) => (
  <g>
    <rect x={62} y={420} width={196} height={665} fill={mix("#2C2520", "#3A2A20", warmth)} />
    <rect x={76} y={434} width={168} height={651} fill={mix("#4F4034", "#6A4E36", warmth)} />
    <rect x={98} y={470} width={124} height={250} rx={4} fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth={4} />
    <rect x={98} y={760} width={124} height={280} rx={4} fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth={4} />
    <circle cx={222} cy={760} r={9} fill="#D8C08A" />
  </g>
);

export const FloorLamp: React.FC<{ on: number; warmth: number }> = ({ on, warmth }) => (
  <g>
    <circle cx={1000} cy={640} r={170} fill="#FFC27A" opacity={0.10 * on + 0.06 * warmth} />
    <rect x={996} y={650} width={8} height={430} fill="#3A3A44" />
    <ellipse cx={1000} cy={1080} rx={44} ry={8} fill="#2A2A33" />
    <path d="M 950 650 L 1050 650 L 1030 590 L 970 590 Z" fill={on > 0.5 ? "#F2C58A" : "#8A7A66"} />
  </g>
);

export const Sofa: React.FC<{ warmth: number }> = ({ warmth }) => {
  const base = mix("#6E2C3A", PAL.sofa, 0.5 + warmth * 0.5), hi = mix("#84394C", PAL.sofaHi, 0.5 + warmth * 0.5);
  return (
    <g>
      <ellipse cx={530} cy={1082} rx={290} ry={14} fill="#000" opacity={0.25} />
      <rect x={310} y={820} width={440} height={150} rx={26} fill={base} />
      <rect x={300} y={930} width={460} height={110} rx={18} fill={hi} />
      <rect x={270} y={870} width={70} height={175} rx={22} fill={base} />
      <rect x={720} y={870} width={70} height={175} rx={22} fill={base} />
      <rect x={300} y={1040} width={16} height={34} fill="#2A1A1E" />
      <rect x={744} y={1040} width={16} height={34} fill="#2A1A1E" />
    </g>
  );
};

export const RoomBack: React.FC<{ s: RoomState }> = ({ s }) => {
  const wall = mix("#1A2236", "#3A2A28", s.warmth);
  const stripe = mix("#202B44", "#433230", s.warmth);
  const floor = mix("#111725", "#22181A", s.warmth);
  return (
    <g>
      <rect x={-600} y={-600} width={2280} height={1686} fill={wall} />
      {Array.from({ length: 40 }).map((_, i) => <rect key={i} x={-600 + i * 60} y={-600} width={26} height={1686} fill={stripe} opacity={0.55} />)}
      <rect x={-600} y={1070} width={2280} height={18} fill={mix("#0E1320", "#1E1414", s.warmth)} />
      <rect x={-600} y={1086} width={2280} height={1500} fill={floor} />
      {Array.from({ length: 8 }).map((_, i) => <rect key={i} x={-600} y={1120 + i * 46 + i * i * 4} width={2280} height={2} fill="#000" opacity={0.18} />)}
    </g>
  );
};

/** soft light/temperature grade over the whole scene (screen space) */
export const Grade: React.FC<{ warmth: number; dim?: number; glow?: { x: number; y: number; r: number; a: number }[] }> = ({ warmth, dim = 0, glow = [] }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <AbsoluteFill style={{ background: "rgba(40,110,255,1)", opacity: 0.11 * (1 - warmth) }} />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 45% 40%, rgba(255,150,70,0.20), rgba(255,120,40,0) 65%)", opacity: warmth }} />
    {glow.map((g, i) => (
      <div key={i} style={{ position: "absolute", left: g.x - g.r, top: g.y - g.r, width: 2 * g.r, height: 2 * g.r, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(255,150,60,0.45), rgba(255,150,60,0) 70%)", opacity: g.a }} />
    ))}
    <AbsoluteFill style={{ background: "#05070D", opacity: 0.55 * dim }} />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 35%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
  </AbsoluteFill>
);

// ══════════════════════════ PROPS ══════════════════════════
export const Heater: React.FC<{ x: number; on: number; heat: number; crossed?: number }> = ({ x, on, heat, crossed = 0 }) => {
  const f = useCurrentFrame();
  const y = 915;
  return (
    <g transform={`translate(${x} 0)`}>
      {/* heat waves */}
      <g opacity={heat} fill="none" stroke={PAL.warm} strokeWidth={5} strokeLinecap="round">
        {[0, 1, 2].map((i) => {
          const ph = ((f * 1.6 + i * 30) % 90) / 90;
          return <path key={i} d={`M ${20 + i * 40} ${y - 10 - ph * 120} q 12 -18 0 -36 q -12 -18 0 -36`} opacity={Math.sin(ph * Math.PI)} />;
        })}
      </g>
      <rect x={0} y={y} width={140} height={145} rx={14} fill="#C7CDD8" />
      {Array.from({ length: 6 }).map((_, i) => (
        <rect key={i} x={8 + i * 21} y={y + 8} width={16} height={128} rx={8} fill={mix("#AEB6C4", "#E8A37A", heat * 0.5)} />
      ))}
      <rect x={140} y={y + 20} width={26} height={40} rx={5} fill="#9AA3B3" />
      <circle cx={153} cy={y + 32} r={5} fill={on > 0.5 ? "#FF4D3D" : "#555"} />
      {on > 0.5 && <circle cx={153} cy={y + 32} r={12} fill="#FF4D3D" opacity={0.3} />}
      <circle cx={20} cy={y + 152} r={8} fill="#333" /><circle cx={120} cy={y + 152} r={8} fill="#333" />
      {/* cord */}
      <path d={`M 166 ${y + 50} q 40 30 20 110`} fill="none" stroke="#222" strokeWidth={5} />
      {crossed > 0 && (
        <g stroke={PAL.danger} strokeWidth={12} strokeLinecap="round" opacity={crossed}>
          <line x1={-10} y1={y - 10} x2={-10 + 170 * crossed} y2={y - 10 + 170 * crossed} />
          <line x1={160} y1={y - 10} x2={160 - 170 * clamp01(crossed * 2 - 1)} y2={y - 10 + 170 * clamp01(crossed * 2 - 1)} />
        </g>
      )}
    </g>
  );
};

/** wall-mounted AC indoor unit. flap 0..1 open, air 0..1 warm airflow, led colour */
export const AcUnit: React.FC<{ y: number; flap: number; air: number; on: number; led?: string; temp?: string; blink?: number;
  airColor?: string; airLen?: number; lid?: number; dirt?: number; shake?: number }> = ({ y, flap, air, on, led = PAL.warm, temp = "22°", blink = 0,
  airColor = PAL.warm, airLen = 1, lid = 0, dirt = 0, shake = 0 }) => {
  const f = useCurrentFrame();
  const X = 290, Wd = 320, H = 100;
  const ledOn = on > 0.5 && (blink === 0 || Math.floor(f / 8) % 2 === 0);
  const L = 330 * airLen;
  const sh = shake ? Math.sin(f * 2.1) * 3 * shake : 0;
  return (
    <g transform={`translate(${sh} ${y})`}>
      {/* airflow (warm by default; airLen < 1 = weak, short streaks) */}
      <g opacity={air} fill="none" strokeLinecap="round">
        {[0, 1, 2, 3, 4].map((i) => {
          const x0 = X + 40 + i * 60;
          return <path key={i} d={`M ${x0} ${H + 14} C ${x0 + 10} ${H + 14 + L * 0.32}, ${x0 + 70 * airLen} ${H + 14 + L * 0.5}, ${x0 + (60 + i * 12) * airLen} ${H + 14 + L}`}
            stroke={airColor} strokeWidth={7} strokeDasharray={`${50 * airLen + 8} 46`} strokeDashoffset={-(f * 5 * (0.4 + 0.6 * airLen) + i * 19)} opacity={0.65} />;
        })}
      </g>
      <rect x={X + 6} y={10} width={Wd} height={H} rx={24} fill="#000" opacity={0.25} />
      {/* housing + filter, visible when the front panel is lifted (lid 0..1) */}
      {lid > 0 && <g>
        <rect x={X} y={0} width={Wd} height={H} rx={24} fill="#AEB8C6" />
        <rect x={X + 16} y={12} width={Wd - 32} height={H - 30} rx={8} fill={mix("#E9EEF4", "#7A7266", dirt)} />
        {Array.from({ length: 15 }).map((_, i) => <rect key={i} x={X + 24 + i * 19} y={14} width={2} height={H - 34} fill="#000" opacity={0.13} />)}
        {Array.from({ length: 4 }).map((_, i) => <rect key={i} x={X + 16} y={24 + i * 14} width={Wd - 32} height={2} fill="#000" opacity={0.10} />)}
        {dirt > 0.05 && Array.from({ length: 22 }).map((_, i) => (
          <circle key={i} cx={X + 26 + ((i * 53) % (Wd - 52))} cy={18 + ((i * 29) % (H - 40))} r={3 + (i % 3) * 2} fill="#5E574C" opacity={0.55 * dirt} />))}
      </g>}
      <g opacity={1 - clamp01(lid * 3)}>
        <rect x={X} y={0} width={Wd} height={H} rx={24} fill="#EEF2F7" />
        <rect x={X} y={0} width={Wd} height={18} rx={9} fill="#FFFFFF" />
        <rect x={X + 16} y={H - 26} width={Wd - 32} height={8} rx={4} fill="#C9D1DC" />
        {/* display */}
        <rect x={X + Wd - 96} y={30} width={66} height={30} rx={8} fill="#1A1F2B" opacity={on > 0.5 ? 1 : 0.3} />
        {on > 0.5 && <text x={X + Wd - 63} y={53} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22} fill={led}>{temp}</text>}
        <circle cx={X + 26} cy={44} r={6} fill={ledOn ? led : "#9AA4B4"} />
        {ledOn && <circle cx={X + 26} cy={44} r={14} fill={led} opacity={0.3} />}
      </g>
      {/* lifted front panel (hinged at the top, swings up and towards the viewer) */}
      {lid > 0 && <g transform={`translate(${X} ${-lid * 118})`}>
        <rect x={-6 * lid} y={0} width={Wd + 12 * lid} height={H * (1 - 0.45 * lid)} rx={22} fill="#F4F7FB" stroke="#C9D1DC" strokeWidth={3} />
        <rect x={-6 * lid} y={H * (1 - 0.45 * lid) - 14} width={Wd + 12 * lid} height={14} rx={7} fill="#DCE2EA" />
      </g>}
      {/* flap */}
      <g transform={`translate(${X + 18} ${H - 10}) rotate(${flap * 28})`}>
        <rect x={0} y={0} width={Wd - 36} height={12} rx={6} fill="#D7DEE8" />
      </g>
    </g>
  );
};

export const Blanket: React.FC<{ x: number; mode: "wrap" | "sofa" | "folded"; drop?: number; standP?: number }> = ({ x, mode, drop = 1, standP = 0 }) => {
  const stripes = (id: string) => (
    <pattern id={id} width="34" height="34" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
      <rect width="34" height="34" fill={PAL.blanket} /><rect width="12" height="34" fill={PAL.blanketDark} />
    </pattern>
  );
  if (mode === "folded") {
    return (
      <g><defs>{stripes("blf")}</defs>
        <rect x={x - 70} y={884} width={140} height={34} rx={10} fill="url(#blf)" />
        <rect x={x - 70} y={914} width={140} height={22} rx={10} fill={PAL.blanketDark} /></g>
    );
  }
  if (mode === "sofa") {
    return (
      <g><defs>{stripes("bls")}</defs>
        <path d={`M ${x - 120} 975 q 30 -60 90 -40 q 50 -40 100 -5 q 60 -10 70 45 z`} fill="url(#bls)" /></g>
    );
  }
  const dy = (1 - drop) * -900;
  return (
    <g transform={`translate(0 ${dy})`} opacity={1 - standP}>
      <defs>{stripes("blw")}</defs>
      <path d={`M ${x - 66} 826 Q ${x} 800 ${x + 66} 826 Q ${x + 128} 880 ${x + 122} 1050 Q ${x} 1078 ${x - 122} 1050 Q ${x - 128} 880 ${x - 66} 826 Z`} fill="url(#blw)" />
      <path d={`M ${x - 66} 826 Q ${x} 800 ${x + 66} 826 Q ${x + 74} 842 ${x + 70} 852 Q ${x} 830 ${x - 70} 852 Q ${x - 74} 842 ${x - 66} 826 Z`} fill={PAL.blanketDark} />
    </g>
  );
};

// ══════════════════════════ CHARACTER ══════════════════════════
export type PersonP = {
  x: number;
  stand?: number;       // 0 sitting on the sofa … 1 standing
  shiver?: number;      // 0..1
  cold?: number;        // 0..1 blue outline glow + frozen face
  breath?: number;      // 0..1 vapour puffs
  hug?: number;         // 0..1 arms hugging the body
  mug?: number;         // 0..1 holding a steaming mug
  walk?: number;        // walking phase speed (0 = still)
  happy?: number;       // smile
  wrapped?: boolean;    // under the blanket (arms/torso hidden)
  sweater?: string;     // override clothing colour (e.g. the «знайомий майстер»)
  cap?: string;         // baseball cap colour
  tool?: number;        // 0..1 holding a toolbox in the right hand
};

export const Person: React.FC<PersonP> = ({ x, stand = 0, shiver = 0, cold = 0, breath = 0, hug = 0, mug = 0, walk = 0, happy = 0, wrapped = false, sweater = PAL.sweater, cap, tool = 0 }) => {
  const f = useCurrentFrame();
  const sx = Math.sin(f * 2.3) * 4 * shiver;
  const hipY = lerp(978, 880, stand);
  const shY = hipY - 140;
  const headY = shY - 52;
  const feetY = 1078;
  const step = walk ? Math.sin(f * 0.45) : 0;
  const glow = cold > 0 ? `drop-shadow(0 0 ${8 * cold}px rgba(93,184,255,${0.95 * cold})) drop-shadow(0 0 ${2 * cold}px rgba(93,184,255,${cold}))` : "none";
  const ox = x + sx;
  return (
    <g style={{ filter: glow }}>
      {/* legs */}
      <g fill={PAL.pants}>
        {stand < 0.5 ? <>
          <rect x={ox - 44} y={hipY + 16} width={34} height={feetY - hipY - 22} rx={12} />
          <rect x={ox + 10} y={hipY + 16} width={34} height={feetY - hipY - 22} rx={12} />
        </> : <>
          <rect x={ox - 40} y={hipY - 4} width={34} height={feetY - hipY - 6 - Math.max(0, step) * 16} rx={12} />
          <rect x={ox + 6} y={hipY - 4} width={34} height={feetY - hipY - 6 - Math.max(0, -step) * 16} rx={12} />
        </>}
      </g>
      <ellipse cx={ox - 24} cy={feetY - 4 - Math.max(0, step) * 16} rx={24} ry={10} fill={PAL.shoe} />
      <ellipse cx={ox + 24} cy={feetY - 4 - Math.max(0, -step) * 16} rx={24} ry={10} fill={PAL.shoe} />
      {/* torso */}
      {!wrapped && <rect x={ox - 52} y={shY} width={104} height={hipY - shY + 14} rx={30} fill={sweater} />}
      {!wrapped && <rect x={ox - 52} y={hipY - 6} width={104} height={14} rx={6} fill="#000" opacity={0.18} />}
      {/* thighs towards the viewer when sitting */}
      {stand < 0.5 && <rect x={ox - 58} y={hipY - 4} width={116} height={46} rx={22} fill={PAL.pants} />}
      {stand < 0.5 && <rect x={ox - 58} y={hipY + 22} width={116} height={20} rx={10} fill="#1C2438" opacity={0.6} />}
      {/* arms */}
      {!wrapped && (() => {
        const a = clamp01(hug), m = clamp01(mug);
        // elbow / hand targets: down (rest) → crossed over chest (hug) → in front holding a mug
        const L = { ex: lerp(ox - 66, ox - 58, a), ey: lerp(shY + 80, shY + 70, a), hx: lerp(ox - 62, ox + 30, a), hy: lerp(shY + 150, shY + 52, a) };
        const R = { ex: lerp(ox + 66, ox + 58, a), ey: lerp(shY + 80, shY + 76, a), hx: lerp(ox + 62, ox - 30, a), hy: lerp(shY + 150, shY + 62, a) };
        if (m > 0) { L.ex = lerp(L.ex, ox - 64, m); L.ey = lerp(L.ey, shY + 92, m); L.hx = lerp(L.hx, ox - 20, m); L.hy = lerp(L.hy, shY + 86, m);
          R.ex = lerp(R.ex, ox + 64, m); R.ey = lerp(R.ey, shY + 92, m); R.hx = lerp(R.hx, ox + 20, m); R.hy = lerp(R.hy, shY + 86, m); }
        const arm = (sxx: number, e: any) => `M ${sxx} ${shY + 18} L ${e.ex} ${e.ey} L ${e.hx} ${e.hy}`;
        return (
          <g>
            <path d={arm(ox - 40, L)} stroke={sweater} strokeWidth={30} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <path d={arm(ox + 40, R)} stroke={sweater} strokeWidth={30} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            {m > 0.05 && (
              <g opacity={m}>
                <rect x={ox - 26} y={shY + 50} width={52} height={60} rx={8} fill="#F4F1EA" />
                <path d={`M ${ox + 26} ${shY + 62} q 22 0 22 18 q 0 18 -22 18`} fill="none" stroke="#F4F1EA" strokeWidth={8} />
                <rect x={ox - 26} y={shY + 50} width={52} height={12} rx={6} fill="#7A4A2A" />
                <g fill="none" stroke="#fff" strokeWidth={5} strokeLinecap="round" opacity={0.7}>
                  {[0, 1].map((i) => { const ph = ((f + i * 25) % 50) / 50;
                    return <path key={i} d={`M ${ox - 8 + i * 16} ${shY + 40 - ph * 60} q 10 -14 0 -28`} opacity={Math.sin(ph * Math.PI)} />; })}
                </g>
              </g>
            )}
            {tool > 0.05 && <g opacity={tool}>
              <rect x={R.hx - 46} y={R.hy + 10} width={92} height={58} rx={8} fill="#D9452B" />
              <rect x={R.hx - 46} y={R.hy + 10} width={92} height={14} rx={6} fill="#B23720" />
              <path d={`M ${R.hx - 18} ${R.hy + 12} L ${R.hx - 18} ${R.hy - 2} L ${R.hx + 18} ${R.hy - 2} L ${R.hx + 18} ${R.hy + 12}`} fill="none" stroke="#333" strokeWidth={6} />
            </g>}
            <circle cx={L.hx} cy={L.hy} r={15} fill={PAL.skin} />
            <circle cx={R.hx} cy={R.hy} r={15} fill={PAL.skin} />
          </g>
        );
      })()}
      {/* head */}
      <rect x={ox - 14} y={shY - 22} width={28} height={30} fill={PAL.skin} />
      <circle cx={ox} cy={headY} r={44} fill={mix(PAL.skin, "#CFE3F5", cold * 0.45)} />
      <path d={`M ${ox - 46} ${headY - 4} Q ${ox - 44} ${headY - 56} ${ox} ${headY - 52} Q ${ox + 48} ${headY - 54} ${ox + 46} ${headY - 6} Q ${ox + 20} ${headY - 30} ${ox - 46} ${headY - 4} Z`} fill={PAL.hair} />
      {cap && <g>
        <path d={`M ${ox - 46} ${headY - 10} Q ${ox - 44} ${headY - 60} ${ox} ${headY - 58} Q ${ox + 46} ${headY - 60} ${ox + 46} ${headY - 10} Z`} fill={cap} />
        <path d={`M ${ox + 10} ${headY - 14} Q ${ox + 60} ${headY - 22} ${ox + 82} ${headY - 8} L ${ox + 40} ${headY - 4} Z`} fill={cap} />
        <rect x={ox - 46} y={headY - 16} width={92} height={8} rx={4} fill="#000" opacity={0.2} />
      </g>}
      <circle cx={ox - 15} cy={headY + 6} r={5} fill="#1B1B22" />
      <circle cx={ox + 15} cy={headY + 6} r={5} fill="#1B1B22" />
      <circle cx={ox - 26} cy={headY + 20} r={8} fill={cold > 0.4 ? "#7FB6F0" : "#F29C8E"} opacity={0.5} />
      <circle cx={ox + 26} cy={headY + 20} r={8} fill={cold > 0.4 ? "#7FB6F0" : "#F29C8E"} opacity={0.5} />
      {cold > 0.4
        ? <path d={`M ${ox - 12} ${headY + 26} l 6 -5 l 6 5 l 6 -5 l 6 5`} stroke="#3A2A2A" strokeWidth={3.5} fill="none" strokeLinecap="round" />
        : <path d={`M ${ox - 11} ${headY + 22} Q ${ox} ${headY + 22 + 10 * (0.4 + happy)} ${ox + 11} ${headY + 22}`} stroke="#3A2A2A" strokeWidth={4} fill="none" strokeLinecap="round" />}
      {/* breath */}
      {breath > 0 && [0, 1, 2].map((i) => {
        const ph = ((f + i * 15) % 45) / 45;
        return <circle key={i} cx={ox + 22 + ph * 70} cy={headY + 26 - ph * 50} r={8 + ph * 22} fill="#E8F3FF" opacity={breath * 0.5 * Math.sin(ph * Math.PI)} />;
      })}
    </g>
  );
};

// ══════════════════════════ HUD ══════════════════════════
export const StatusBar: React.FC<{ left: string; temp: number; tempLabel?: string; opacity?: number }> = ({ left, temp, tempLabel = "У КІМНАТІ", opacity = 1 }) => {
  const c = temp < 18 ? PAL.cold : temp < 21 ? PAL.yellow : PAL.ok;
  return (
    <div style={{ position: "absolute", top: 138, left: 0, right: 0, display: "flex", justifyContent: "center", opacity }}>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 30, letterSpacing: 2, color: "#D9DEEA", background: "rgba(10,14,26,0.82)",
        border: "2px solid rgba(255,255,255,0.14)", borderRadius: 10, padding: "10px 22px", display: "flex", gap: 16, alignItems: "center" }}>
        <span>{left}</span><span style={{ opacity: 0.4 }}>·</span><span>{tempLabel}</span>
        <span style={{ color: c, minWidth: 140, textShadow: `0 0 14px ${c}88` }}>{(temp >= 0 ? "+" : "") + temp.toFixed(1)} °C</span>
      </div>
    </div>
  );
};

export const StepPill: React.FC<{ from: number; to: number; n: number; total: number; label: string; color?: string }> = ({ from, to, n, total, label, color = PAL.yellow }) => {
  const f = useCurrentFrame();
  const p = usePop(from, 14);
  const o = win(f, from, to, 4);
  if (o <= 0) return null;
  return (
    <div style={{ position: "absolute", top: 222, left: 50, opacity: o, transform: `translateX(${(1 - p) * -420}px)` }}>
      <div style={{ display: "flex", alignItems: "stretch", borderRadius: 14, overflow: "hidden", border: `3px solid ${color}`, boxShadow: `0 0 28px ${color}55`, background: PAL.panel }}>
        <div style={{ background: color, color: PAL.ink, fontFamily: MONO, fontWeight: 700, fontSize: 30, padding: "12px 18px", display: "flex", alignItems: "center" }}>
          КРОК {n}/{total}
        </div>
        <div style={{ color: PAL.text, fontFamily: SANS, fontWeight: 900, fontSize: 42, padding: "8px 22px", letterSpacing: 1 }}>{label}</div>
      </div>
    </div>
  );
};

const Icon: React.FC<{ kind: string; color: string }> = ({ kind, color }) => (
  <div style={{ width: 52, height: 52, borderRadius: 10, background: color, display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
    <svg width={34} height={34} viewBox="0 0 34 34" fill="none" stroke={PAL.ink} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round">
      {kind === "ok" && <path d="M 7 18 L 14 25 L 27 10" />}
      {kind === "no" && <path d="M 9 9 L 25 25 M 25 9 L 9 25" />}
      {kind === "warn" && <><path d="M 17 7 L 17 19" /><circle cx={17} cy={27} r={1.5} fill={PAL.ink} /></>}
      {kind === "bolt" && <path d="M 19 4 L 9 19 L 17 19 L 14 30 L 25 14 L 17 14 Z" fill={PAL.ink} strokeWidth={2} />}
      {kind === "pin" && <><circle cx={17} cy={13} r={6} /><path d="M 17 19 L 17 30" /></>}
      {kind === "q" && <path d="M 11 11 Q 11 5 17 5 Q 24 5 24 11 Q 24 16 17 18 L 17 22 M 17 28 L 17 28.5" />}
    </svg>
  </div>
);

/** HUD callout: box at (x,y) screen px, dashed leader to target (tx,ty) screen px */
export const Callout: React.FC<{ from: number; to: number; x: number; y: number; tx?: number; ty?: number; kind: "ok" | "no" | "warn" | "bolt" | "pin" | "q";
  title: string; sub?: string; color?: string; w?: number }> = ({ from, to, x, y, tx, ty, kind, title, sub, color, w }) => {
  const f = useCurrentFrame();
  const col = color ?? (kind === "ok" ? PAL.ok : kind === "no" ? PAL.danger : kind === "bolt" ? PAL.yellow : kind === "q" ? PAL.cold : PAL.warm);
  const p = usePop(from, 11);
  const o = win(f, from, to, 4);
  if (o <= 0) return null;
  const lineP = clamp01((f - from - 3) / 8);
  const ax = x + 40, ay = y + 70;
  return (
    <AbsoluteFill style={{ opacity: o, pointerEvents: "none" }}>
      {tx !== undefined && (
        <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
          <line x1={ax} y1={ay} x2={lerp(ax, tx, lineP)} y2={lerp(ay, ty!, lineP)} stroke={col} strokeWidth={3} strokeDasharray="8 8" />
          {lineP >= 1 && <circle cx={tx} cy={ty} r={9} fill={col} />}
          {lineP >= 1 && <circle cx={tx} cy={ty} r={9 + 10 * ((f % 30) / 30)} fill="none" stroke={col} strokeWidth={3} opacity={1 - (f % 30) / 30} />}
        </svg>
      )}
      <div style={{ position: "absolute", left: x, top: y, transform: `scale(${0.6 + 0.4 * p})`, transformOrigin: "left center", width: w,
        display: "flex", gap: 16, alignItems: "center", padding: "14px 22px 14px 14px", borderRadius: 14, background: PAL.panel,
        border: `3px solid ${col}`, boxShadow: `0 0 26px ${col}55` }}>
        <Icon kind={kind} color={col} />
        <div>
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 38, color: PAL.text, lineHeight: 1.05, textTransform: "uppercase" }}>{title}</div>
          {sub && <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 24, color: col, marginTop: 4, letterSpacing: 1 }}>{sub}</div>}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** karaoke captions: pages [{f0,f1,fs,words:[{w,f,style}]}]; words light up when spoken */
export const Captions: React.FC<{ pages: readonly any[]; top?: number; hideFrom?: number }> = ({ pages, top = 1290, hideFrom = 1e9 }) => {
  const f = useCurrentFrame();
  if (f >= hideFrom) return null;
  const pg = pages.find((p) => f >= p.f0 && f < p.f1);
  if (!pg) return null;
  const local = f - pg.f0;
  const pop = Easing.out(Easing.back(2))(clamp01(local / 5));
  return (
    <div style={{ position: "absolute", top, left: 40, right: 40, height: 230, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 22, rowGap: 0, transform: `scale(${0.88 + 0.12 * pop})`,
        fontFamily: SANS, fontWeight: 900, fontSize: pg.fs, lineHeight: 1.06, textTransform: "uppercase", textAlign: "center" }}>
        {pg.words.map((w: any, i: number) => {
          const on = local >= w.f;
          const col = on ? STYLE_COLOR[w.style] ?? PAL.text : PAL.dim;
          return (
            <span key={i} style={{ color: col, textShadow: on && w.style ? `0 0 24px ${col}66, 0 5px 0 rgba(0,0,0,0.55)` : "0 5px 0 rgba(0,0,0,0.55), 0 0 18px rgba(0,0,0,0.6)" }}>{w.w}</span>
          );
        })}
      </div>
    </div>
  );
};

/** white flash (scene cut accent) */
export const Flash: React.FC<{ at: number; len?: number; color?: string }> = ({ at, len = 8, color = "#fff" }) => {
  const f = useCurrentFrame();
  const o = f < at || f > at + len ? 0 : 1 - (f - at) / len;
  return o > 0 ? <AbsoluteFill style={{ background: color, opacity: o * 0.85 }} /> : null;
};

// ══════════════════════════ DIAGRAM / INFOGRAPHIC ══════════════════════════
const pipePts: [number, number][] = [[410, 820], [450, 820], [450, 520], [700, 520]];
const along = (t: number): [number, number] => {
  const segs = pipePts.slice(1).map((p, i) => [pipePts[i], p, Math.hypot(p[0] - pipePts[i][0], p[1] - pipePts[i][1])] as const);
  const total = segs.reduce((s, x) => s + x[2], 0);
  let d = clamp01(t) * total;
  for (const [a, b, l] of segs) { if (d <= l) return [a[0] + (b[0] - a[0]) * d / l, a[1] + (b[1] - a[1]) * d / l]; d -= l; }
  return pipePts[pipePts.length - 1];
};

/** cross-section: street (snow, outdoor unit) | wall | flat (indoor unit). a = collect from air, b = through pipe, c = into room */
export const HeatPumpDiagram: React.FC<{ a: number; b: number; c: number }> = ({ a, b, c }) => {
  const f = useCurrentFrame();
  const fan = f * 18;
  return (
    <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
      <defs>
        <linearGradient id="outsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0A1430" /><stop offset="1" stopColor="#1E3366" /></linearGradient>
        <linearGradient id="insky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3A2826" /><stop offset="1" stopColor="#4A302A" /></linearGradient>
      </defs>
      <rect x={0} y={0} width={480} height={1920} fill="url(#outsky)" />
      <rect x={540} y={0} width={540} height={1920} fill="url(#insky)" />
      <Snow x={0} y={260} w={480} h={830} n={60} />
      <rect x={0} y={1060} width={480} height={60} rx={0} fill="#E6EEF8" />
      <rect x={0} y={1120} width={480} height={800} fill="#0F1628" />
      <rect x={540} y={1060} width={540} height={860} fill="#22181A" />
      {/* wall */}
      <rect x={480} y={0} width={60} height={1920} fill="#7C7F8C" />
      {Array.from({ length: 24 }).map((_, i) => <rect key={i} x={480 + (i % 2) * 30} y={i * 46} width={30} height={2} fill="#5E616C" />)}
      {/* outdoor unit */}
      <rect x={110} y={720} width={300} height={230} rx={14} fill="#DDE3EC" />
      <circle cx={225} cy={835} r={88} fill="#2A3142" />
      <g transform={`rotate(${fan} 225 835)`}>{[0, 120, 240].map((r) => <ellipse key={r} cx={225} cy={790} rx={22} ry={44} fill="#8C97AA" transform={`rotate(${r} 225 835)`} />)}</g>
      <circle cx={225} cy={835} r={14} fill="#C9D1DC" />
      {Array.from({ length: 7 }).map((_, i) => <rect key={i} x={330} y={748 + i * 26} width={58} height={8} rx={4} fill="#B5BECC" />)}
      <rect x={130} y={950} width={20} height={110} fill="#4A5060" /><rect x={370} y={950} width={20} height={110} fill="#4A5060" />
      {/* pipes */}
      <polyline points={pipePts.map((p) => p.join(",")).join(" ")} fill="none" stroke="#C77B3B" strokeWidth={16} strokeLinejoin="round" />
      <polyline points={pipePts.map((p) => p.join(",")).join(" ")} fill="none" stroke="#E7A066" strokeWidth={5} strokeLinejoin="round" />
      {/* indoor unit */}
      <rect x={640} y={460} width={330} height={100} rx={24} fill="#EEF2F7" />
      <rect x={656} y={536} width={298} height={10} rx={5} fill="#D7DEE8" />
      <circle cx={666} cy={500} r={6} fill={PAL.warm} />
      {/* (a) heat collected from the cold air → outdoor unit */}
      {Array.from({ length: 18 }).map((_, i) => {
        const ph = ((f * 1.2 + i * 17) % 60) / 60;
        const sx = 30 + ((i * 97) % 420), sy = 300 + ((i * 61) % 380);
        const x = lerp(sx, 225, ph * ph), y = lerp(sy, 835, ph * ph);
        return <circle key={i} cx={x} cy={y} r={7} fill={PAL.warm} opacity={a * Math.sin(ph * Math.PI) * 0.95} />;
      })}
      {/* (b) along the pipe */}
      {Array.from({ length: 9 }).map((_, i) => {
        const [x, y] = along(((f / 45) + i / 9) % 1);
        return <circle key={i} cx={x} cy={y} r={10} fill={PAL.warm} opacity={b} style={{ filter: `drop-shadow(0 0 8px ${PAL.warm})` }} />;
      })}
      {/* (c) warm air into the flat */}
      <g opacity={c} fill="none" strokeLinecap="round">
        {[0, 1, 2, 3].map((i) => {
          const x0 = 690 + i * 70;
          return <path key={i} d={`M ${x0} 575 C ${x0 + 10} 680, ${x0 + 60} 760, ${x0 + 30} 940`} stroke={PAL.warm} strokeWidth={9}
            strokeDasharray="56 44" strokeDashoffset={-(f * 5 + i * 23)} opacity={0.75} />;
        })}
      </g>
      <rect x={540} y={0} width={540} height={1060} fill="rgba(255,140,60,1)" opacity={0.10 * c} />
    </svg>
  );
};

/** label chip used on the diagram (screen px) */
export const Chip: React.FC<{ x: number; y: number; text: string; sub?: string; color: string; from: number; to?: number; align?: "left" | "right" }> = ({ x, y, text, sub, color, from, to = 1e9, align = "left" }) => {
  const f = useCurrentFrame();
  const p = usePop(from, 12);
  const o = win(f, from, to, 4);
  if (o <= 0) return null;
  return (
    <div style={{ position: "absolute", top: y, ...(align === "left" ? { left: x } : { right: 1080 - x }), opacity: o, transform: `scale(${0.6 + 0.4 * p})`,
      background: PAL.panel, border: `3px solid ${color}`, borderRadius: 12, padding: "10px 18px", boxShadow: `0 0 22px ${color}55` }}>
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 40, color: PAL.text }}>{text}</div>
      {sub && <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 24, color, letterSpacing: 1 }}>{sub}</div>}
    </div>
  );
};

export const Bolt: React.FC<{ size: number; color?: string }> = ({ size, color = PAL.yellow }) => (
  <svg width={size} height={size} viewBox="0 0 40 40"><path d="M 23 2 L 7 23 L 18 23 L 15 38 L 33 15 L 22 15 Z" fill={color} /></svg>
);
export const Flame: React.FC<{ size: number; color?: string }> = ({ size, color = PAL.warm }) => (
  <svg width={size} height={size} viewBox="0 0 40 40"><path d="M 20 2 C 24 12 33 16 33 26 C 33 34 27 38 20 38 C 13 38 7 34 7 26 C 7 19 12 16 14 9 C 16 14 18 16 20 17 C 21 12 21 7 20 2 Z" fill={color} />
    <path d="M 20 22 C 22 26 26 28 26 32 C 26 35 23 37 20 37 C 17 37 14 35 14 32 C 14 29 17 27 20 22 Z" fill="#FFE0A0" /></svg>
);
export const Snowflake: React.FC<{ size: number; color?: string }> = ({ size, color = PAL.cold }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" stroke={color} strokeWidth={3.5} strokeLinecap="round">
    {[0, 60, 120].map((r) => <g key={r} transform={`rotate(${r} 20 20)`}><line x1={20} y1={3} x2={20} y2={37} /><path d="M 15 8 L 20 12 L 25 8 M 15 32 L 20 28 L 25 32" fill="none" /></g>)}
  </svg>
);

/** remote control close-up; mode switches COOL→HEAT at `switchAt` */
export const Remote: React.FC<{ from: number; to: number; switchAt: number; x?: number; y?: number }> = ({ from, to, switchAt, x = 640, y = 560 }) => {
  const f = useCurrentFrame();
  const p = usePop(from, 13);
  const o = win(f, from, to, 5);
  if (o <= 0) return null;
  const heat = f >= switchAt;
  const press = f >= switchAt - 3 && f < switchAt + 3;
  const flashLcd = heat ? Easing.out(Easing.quad)(clamp01((f - switchAt) / 10)) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, opacity: o, transform: `translateY(${(1 - p) * 500}px) rotate(-9deg)`, transformOrigin: "center" }}>
      <div style={{ width: 300, height: 560, borderRadius: 60, background: "linear-gradient(160deg,#F7F9FC,#D4DAE4)", boxShadow: "0 30px 60px rgba(0,0,0,0.55)", padding: 26, boxSizing: "border-box" }}>
        <div style={{ height: 190, borderRadius: 22, background: heat ? "#2A1A10" : "#0F1E2E", border: "4px solid #9AA4B4", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          boxShadow: heat ? `inset 0 0 ${40 * flashLcd}px ${PAL.warm}88` : "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: MONO, fontWeight: 700, fontSize: 52, color: heat ? PAL.warm : PAL.cold }}>
            {heat ? <Flame size={50} /> : <Snowflake size={46} />}{heat ? "HEAT" : "COOL"}
          </div>
          <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 64, color: heat ? "#FFD7B0" : "#BFE3FF" }}>{heat ? "22°" : "18°"}</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginTop: 30 }}>
          {["MODE", "FAN", "▲", "▼", "SWING", "TIMER"].map((k, i) => (
            <div key={k} style={{ height: 64, borderRadius: 32, background: i === 0 ? (press ? "#C96A1E" : PAL.warm) : "#C3CAD6", transform: i === 0 && press ? "scale(0.92)" : "none",
              display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontWeight: 700, fontSize: 24, color: i === 0 ? "#fff" : "#4A5366",
              boxShadow: i === 0 ? `0 0 ${heat ? 0 : 20}px ${PAL.warm}` : "none" }}>{k}</div>
          ))}
        </div>
      </div>
    </div>
  );
};
