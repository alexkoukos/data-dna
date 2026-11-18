import type { Action } from "./detect/policy";
import { TEXTURE_CSS } from "./texture";
import {
  Ban,
  Check,
  createElement,
  EyeOff,
  House,
  Pencil,
  SendHorizontal,
  ShieldCheck,
  TriangleAlert,
  type IconNode,
} from "lucide";

/**
 * Everything the person sees on top of an AI site. It lives in a Shadow DOM so the site's CSS
 * cannot break it and ours cannot leak into the site.
 */
const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; font-family: 'Poppins', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647; }
.chip, .banner, .note { pointer-events: auto; }
.cardwrap { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); width: min(540px, calc(100vw - 32px)); animation: rise .2s ease-out; pointer-events: none; }
.card::before { content: ""; display: block; height: 4px; background: var(--solid); }
.card {
  position: relative; background: linear-gradient(165deg, color-mix(in srgb, var(--bg) 55%, #fffaf0), color-mix(in srgb, var(--bg) 25%, #fff3d6)); color: #262626;
  border: 1px solid #e5e7eb; border-radius: 22px; overflow: hidden; pointer-events: auto;
  box-shadow: 0 24px 60px rgba(38,38,38,.22), 0 4px 14px rgba(38,38,38,.1);
}
/* Slow ribbons drift behind the content; they carry the outcome colour and stay subtle */
.ribbons { position: absolute; inset: 0; overflow: hidden; z-index: 0; pointer-events: none; }
.rib { position: absolute; left: 0; width: 200%; height: 120px; fill: none; stroke-width: 26; stroke-linecap: round; filter: blur(6px); }
.rib1 { top: -4%; stroke: var(--solid); opacity: .2; animation: flow 18s linear infinite; }
.rib2 { top: 34%; stroke: #f59e0b; opacity: .24; animation: flow 26s linear infinite reverse; }
.rib3 { top: 66%; stroke: #fde047; opacity: .3; animation: flow 32s linear infinite; }
@keyframes flow { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .rib { animation: none; } }
/* A second, smaller bee patrols the card's edge while the one in the header hovers and buzzes */
.patrol { position: absolute; inset: -22px; pointer-events: none; }
.pbee { position: absolute; width: 30px; offset-path: inset(0 round 34px); offset-rotate: 0deg; offset-anchor: 50% 50%; animation: orbit 11s linear infinite; }
.pbee span { display: block; animation: face 11s steps(1) infinite, bob .5s ease-in-out infinite alternate; }
@keyframes orbit { from { offset-distance: 0%; } to { offset-distance: 100%; } }
@keyframes face { 0% { transform: scaleX(1); } 50% { transform: scaleX(-1); } }
@keyframes bob { from { translate: 0 -2px; } to { translate: 0 2px; } }
/* Wings beat fast, the body drifts in a lazy figure of eight */
.bee svg path:nth-child(-n+2) { transform-box: fill-box; transform-origin: 50% 100%; animation: flap .09s ease-in-out infinite alternate; }
@keyframes flap { from { transform: rotate(-9deg) scaleY(1); } to { transform: rotate(9deg) scaleY(.4); } }
.head .bee { animation: hover 3.6s ease-in-out infinite; }
@keyframes hover { 0% { transform: translate(0,0) rotate(-4deg); } 25% { transform: translate(6px,-5px) rotate(5deg); } 50% { transform: translate(0,-1px) rotate(-3deg); } 75% { transform: translate(-6px,-6px) rotate(4deg); } 100% { transform: translate(0,0) rotate(-4deg); } }
@media (prefers-reduced-motion: reduce) { .head .bee, .pbee, .pbee span, .bee svg path:nth-child(-n+2) { animation: none; } .patrol { display: none; } }
@keyframes rise { from { opacity: 0; transform: translate(-50%, 12px); } to { opacity: 1; transform: translate(-50%, 0); } }
@media (prefers-reduced-motion: reduce) { .cardwrap { animation: none; } }
/* Header band takes the outcome's colour, so the verdict is the first thing seen */
.head { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: 22px 28px 18px; position: relative; z-index: 1; }
.bee { flex: none; width: 48px; }
.bee svg { display: block; width: 100%; height: auto; }
.head-text { min-width: 0; flex: 1; }
.chipo { flex: none; margin-left: auto; display: inline-flex; align-items: center; gap: 8px; font-family: 'Playfair Display', Georgia, serif; font-size: 20px; line-height: 26px; font-weight: 600; color: var(--fg); white-space: nowrap; }
.chipo i { display: inline-flex; }
h2 { margin: 0; font-family: 'Playfair Display', Georgia, serif; font-size: 22px; line-height: 29px; font-weight: 600; color: #262626; }
.main { position: relative; z-index: 1; padding: 4px 28px 28px; }
p { margin: 0; font-size: 15px; line-height: 23px; color: #525252; }
.found { margin: 16px 0 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }
.found li { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border: 1px solid rgba(38,38,38,.12); border-radius: 9999px; background: rgba(255,255,255,.6); font-size: 13px; line-height: 18px; color: #262626; font-weight: 600; }

.found li::before { content: ""; flex: none; width: 7px; height: 7px; border-radius: 9999px; background: var(--solid); }
code { font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace; background: #f9fafb; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 12px 14px; font-size: 13px; line-height: 20px; color: #262626; display: block; margin: 6px 0 0; white-space: pre-wrap; }
label { display: block; font-size: 13px; font-weight: 800; margin: 20px 0 6px; color: #262626; }
.tip { margin: 16px 0 0; padding: 12px 14px; border-radius: 12px; background: rgba(255,255,255,.55); font-size: 14px; line-height: 21px; color: #525252; }
textarea { width: 100%; min-height: 72px; resize: vertical; font-size: 14px; line-height: 21px; padding: 12px 14px;
  border: 1px solid rgba(38,38,38,.2); border-radius: 12px; color: inherit; background: rgba(255,255,255,.75); }
/* The action band: a quiet footer for the buttons */
.actions { position: relative; display: flex; flex-flow: row-reverse wrap; justify-content: flex-start; align-items: center; gap: 12px; margin: 26px -28px -28px; padding: 22px 28px;
  background: transparent; border-top: 1px solid rgba(38,38,38,.08); }
.hint { margin-right: auto; font-size: 12px; line-height: 16px; color: #6b7280; }
.hint kbd { font: inherit; font-weight: 700; border: 1px solid #d1d5db; border-radius: 6px; padding: 1px 6px; background: rgba(255,255,255,.7); }
@media (max-width: 480px) { .hint { display: none; } }
.chip, .note { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); display: flex; align-items: center; gap: 12px;
  max-width: min(480px, calc(100vw - 32px)); background: #fff; color: #262626; font-size: 14px; line-height: 21px;
  padding: 12px 20px 12px 14px; border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 10px 30px rgba(38,38,38,.16); }
.chip .bee, .note .bee { width: 30px; }
.banner { position: absolute; top: 0; left: 0; right: 0; background: #fffbeb; color: #262626; border-bottom: 2px solid #f59e0b;
  padding: 14px 20px; font-size: 14px; display: flex; gap: 14px; align-items: center; justify-content: center; flex-wrap: wrap; }
.banner button { min-height: 40px; }
textarea:focus-visible, a:focus-visible { outline: 2px solid #262626; outline-offset: 2px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media (prefers-color-scheme: dark) {
  .chip, .note { background: #262626; color: #fafaf9; border-color: #404040; }
  .card { color: #fafaf9; border-color: rgba(255,255,255,.14); }
  .card { background: linear-gradient(165deg, color-mix(in srgb, var(--dbg) 70%, #2b2418), color-mix(in srgb, var(--dbg) 35%, #231c10)); }
  .card::before { background: var(--dsolid); }
  h2 { color: #fafaf9; }
  .chipo { color: var(--dfg); }
  p, label { color: #d4d4d4; }
  .found li { background: rgba(255,255,255,.07); border-color: rgba(255,255,255,.14); color: #fafaf9; }
  .found li::before { background: var(--dsolid); }
  .rib1 { stroke: var(--dsolid); opacity: .3; } .rib2 { opacity: .3; } .rib3 { opacity: .2; stroke: #d97706; }
  .tip { background: rgba(255,255,255,.06); color: #d4d4d4; }
  .actions { border-top-color: rgba(255,255,255,.1); }
  .hint { color: #a3a3a3; } .hint kbd { background: rgba(255,255,255,.08); border-color: #525252; }
  .bee svg [fill="#262626"] { fill: #fafaf9; }
  code { background: #1f1f1f; border-color: #404040; color: #fafaf9; }
  textarea { background: rgba(255,255,255,.08); color: #fafaf9; border-color: rgba(255,255,255,.2); }
  .banner { background: #262626; color: #fafaf9; }
}
${TEXTURE_CSS}
`;

/** The five outcome colours from the Hive kit (light and dark), the icon, and the word shown beside it. */
const lucideEl = (node: IconNode, size = 14): SVGElement =>
  createElement(node, { width: size, height: size, "stroke-width": 2.25, "aria-hidden": "true" });

const ACCENT: Record<
  Action,
  {
    bg: string;
    fg: string;
    solid: string;
    dbg: string;
    dfg: string;
    dsolid: string;
    icon: IconNode;
    word: string;
  }
> = {
  allow: {
    bg: "#e5f6e3",
    fg: "#245420",
    solid: "#30752a",
    dbg: "#1c3a1a",
    dfg: "#a6dca0",
    dsolid: "#5bb353",
    icon: Check,
    word: "Allowed",
  },
  mask: {
    bg: "#f4ecff",
    fg: "#553674",
    solid: "#764aa2",
    dbg: "#2e2340",
    dfg: "#dcc8f5",
    dsolid: "#a67fd6",
    icon: EyeOff,
    word: "Masked",
  },
  warn: {
    bg: "#f9efda",
    fg: "#704500",
    solid: "#915b00",
    dbg: "#3d2f10",
    dfg: "#f3d28a",
    dsolid: "#d9a03a",
    icon: TriangleAlert,
    word: "Warned",
  },
  local: {
    bg: "#e5f2ff",
    fg: "#154a7a",
    solid: "#1666aa",
    dbg: "#12304a",
    dfg: "#a9d3f7",
    dsolid: "#4f9be0",
    icon: House,
    word: "Answered locally",
  },
  block: {
    bg: "#ffebe9",
    fg: "#7e2122",
    solid: "#b02a2d",
    dbg: "#45201f",
    dfg: "#ffb4ad",
    dsolid: "#e0605f",
    icon: Ban,
    word: "Blocked",
  },
};

/** An icon beside each card button, by its id. */
const BUTTON_ICON: Record<string, IconNode> = {
  edit: Pencil,
  rewrite: ShieldCheck,
  send: SendHorizontal,
};

/** Three wavy ribbons; each path repeats every 600 units, so sliding the svg by half its width loops seamlessly. */
const WAVE = "M0 60 C100 0 200 0 300 60 S500 120 600 60 S800 0 900 60 S1100 120 1200 60";
const RIBBONS = ["rib1", "rib2", "rib3"]
  .map(
    (c) =>
      `<svg class="rib ${c}" viewBox="0 0 1200 120" preserveAspectRatio="none"><path d="${WAVE}"/></svg>`,
  )
  .join("");

/** The guard bee, inline so a site's content security policy cannot block it. */
const BEE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="641.50 322.75 66.70 50.50" role="img" aria-hidden="true" focusable="false"><path d="M672.00 333.75C672.00 334.34 671.91 334.93 671.74 335.51C671.57 336.09 671.31 336.65 670.97 337.19C670.63 337.74 670.22 338.26 669.72 338.75C669.23 339.24 668.67 339.70 668.05 340.11C667.42 340.53 666.74 340.90 666.00 341.23C665.26 341.56 664.49 341.84 663.67 342.06C662.85 342.29 662.00 342.46 661.13 342.58C660.26 342.69 659.39 342.75 658.50 342.75C657.61 342.75 656.74 342.69 655.87 342.58C655.00 342.46 654.15 342.29 653.33 342.06C652.51 341.84 651.74 341.56 651.00 341.23C650.26 340.90 649.58 340.53 648.95 340.11C648.33 339.70 647.77 339.24 647.28 338.75C646.78 338.26 646.37 337.74 646.03 337.19C645.69 336.65 645.43 336.09 645.26 335.51C645.09 334.93 645.00 334.34 645.00 333.75C645.00 333.16 645.09 332.57 645.26 331.99C645.43 331.41 645.69 330.85 646.03 330.31C646.37 329.76 646.78 329.24 647.28 328.75C647.77 328.26 648.33 327.80 648.95 327.39C649.58 326.97 650.26 326.60 651.00 326.27C651.74 325.94 652.51 325.66 653.33 325.44C654.15 325.21 655.00 325.04 655.87 324.92C656.74 324.81 657.61 324.75 658.50 324.75C659.39 324.75 660.26 324.81 661.13 324.92C662.00 325.04 662.85 325.21 663.67 325.44C664.49 325.66 665.26 325.94 666.00 326.27C666.74 326.60 667.42 326.97 668.05 327.39C668.67 327.80 669.23 328.26 669.72 328.75C670.22 329.24 670.63 329.76 670.97 330.31C671.31 330.85 671.57 331.41 671.74 331.99C671.91 332.57 672.00 333.16 672.00 333.75" fill="#FFFFFF" stroke="#262626" stroke-width="3.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M693.00 333.75C693.00 334.34 692.91 334.93 692.74 335.51C692.57 336.09 692.31 336.65 691.97 337.19C691.63 337.74 691.22 338.26 690.72 338.75C690.23 339.24 689.67 339.70 689.05 340.11C688.42 340.53 687.74 340.90 687.00 341.23C686.26 341.56 685.49 341.84 684.67 342.06C683.85 342.29 683.00 342.46 682.13 342.58C681.26 342.69 680.39 342.75 679.50 342.75C678.61 342.75 677.74 342.69 676.87 342.58C676.00 342.46 675.15 342.29 674.33 342.06C673.51 341.84 672.74 341.56 672.00 341.23C671.26 340.90 670.58 340.53 669.95 340.11C669.33 339.70 668.77 339.24 668.28 338.75C667.78 338.26 667.37 337.74 667.03 337.19C666.69 336.65 666.43 336.09 666.26 335.51C666.09 334.93 666.00 334.34 666.00 333.75C666.00 333.16 666.09 332.57 666.26 331.99C666.43 331.41 666.69 330.85 667.03 330.31C667.37 329.76 667.78 329.24 668.28 328.75C668.77 328.26 669.33 327.80 669.95 327.39C670.58 326.97 671.26 326.60 672.00 326.27C672.74 325.94 673.51 325.66 674.33 325.44C675.15 325.21 676.00 325.04 676.87 324.92C677.74 324.81 678.61 324.75 679.50 324.75C680.39 324.75 681.26 324.81 682.13 324.92C683.00 325.04 683.85 325.21 684.67 325.44C685.49 325.66 686.26 325.94 687.00 326.27C687.74 326.60 688.42 326.97 689.05 327.39C689.67 327.80 690.23 328.26 690.72 328.75C691.22 329.24 691.63 329.76 691.97 330.31C692.31 330.85 692.57 331.41 692.74 331.99C692.91 332.57 693.00 333.16 693.00 333.75" fill="#FFFFFF" stroke="#262626" stroke-width="3.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M691.50 354.75C691.50 355.29 691.46 355.83 691.38 356.37C691.31 356.91 691.19 357.44 691.04 357.97C690.89 358.50 690.69 359.02 690.47 359.54C690.24 360.06 689.97 360.57 689.67 361.06C689.37 361.56 689.04 362.05 688.67 362.53C688.30 363.00 687.89 363.47 687.46 363.92C687.02 364.37 686.55 364.80 686.05 365.22C685.55 365.64 685.03 366.04 684.47 366.42C683.91 366.80 683.33 367.16 682.73 367.50C682.12 367.85 681.49 368.17 680.83 368.47C680.18 368.77 679.51 369.05 678.81 369.30C678.12 369.56 677.41 369.79 676.68 369.99C675.96 370.20 675.22 370.38 674.47 370.54C673.71 370.70 672.95 370.83 672.18 370.93C671.41 371.04 670.63 371.12 669.85 371.17C669.07 371.22 668.29 371.25 667.50 371.25C666.71 371.25 665.93 371.22 665.15 371.17C664.37 371.12 663.59 371.04 662.82 370.93C662.05 370.83 661.29 370.70 660.53 370.54C659.78 370.38 659.04 370.20 658.32 369.99C657.59 369.79 656.88 369.56 656.19 369.30C655.49 369.05 654.82 368.77 654.17 368.47C653.51 368.17 652.88 367.85 652.27 367.50C651.67 367.16 651.09 366.80 650.53 366.42C649.97 366.04 649.45 365.64 648.95 365.22C648.45 364.80 647.98 364.37 647.54 363.92C647.11 363.47 646.70 363.00 646.33 362.53C645.96 362.05 645.63 361.56 645.33 361.06C645.03 360.57 644.76 360.06 644.53 359.54C644.31 359.02 644.11 358.50 643.96 357.97C643.81 357.44 643.69 356.91 643.62 356.37C643.54 355.83 643.50 355.29 643.50 354.75C643.50 354.21 643.54 353.67 643.62 353.13C643.69 352.59 643.81 352.06 643.96 351.53C644.11 351.00 644.31 350.48 644.53 349.96C644.76 349.44 645.03 348.93 645.33 348.44C645.63 347.94 645.96 347.45 646.33 346.97C646.70 346.50 647.11 346.03 647.54 345.58C647.98 345.13 648.45 344.70 648.95 344.28C649.45 343.86 649.97 343.46 650.53 343.08C651.09 342.70 651.67 342.34 652.27 342.00C652.88 341.65 653.51 341.33 654.17 341.03C654.82 340.73 655.49 340.45 656.19 340.20C656.88 339.94 657.59 339.71 658.32 339.51C659.04 339.30 659.78 339.12 660.53 338.96C661.29 338.80 662.05 338.67 662.82 338.57C663.59 338.46 664.37 338.38 665.15 338.33C665.93 338.28 666.71 338.25 667.50 338.25C668.29 338.25 669.07 338.28 669.85 338.33C670.63 338.38 671.41 338.46 672.18 338.57C672.95 338.67 673.71 338.80 674.47 338.96C675.22 339.12 675.96 339.30 676.68 339.51C677.41 339.71 678.12 339.94 678.81 340.20C679.51 340.45 680.18 340.73 680.83 341.03C681.49 341.33 682.12 341.65 682.73 342.00C683.33 342.34 683.91 342.70 684.47 343.08C685.03 343.46 685.55 343.86 686.05 344.28C686.55 344.70 687.02 345.13 687.46 345.58C687.89 346.03 688.30 346.50 688.67 346.97C689.04 347.45 689.37 347.94 689.67 348.44C689.97 348.93 690.24 349.44 690.47 349.96C690.69 350.48 690.89 351.00 691.04 351.53C691.19 352.06 691.31 352.59 691.38 353.13C691.46 353.67 691.50 354.21 691.50 354.75" fill="#F59E0B"/><path d="M661.50 339.75L661.50 369.75M673.50 339.75L673.50 369.75" fill="none" stroke="#262626" stroke-width="6.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M706.20 354.75C706.20 355.42 706.13 356.08 706.00 356.74C705.87 357.40 705.68 358.03 705.42 358.65C705.17 359.27 704.85 359.86 704.48 360.42C704.11 360.97 703.69 361.49 703.21 361.96C702.74 362.44 702.22 362.86 701.67 363.23C701.11 363.60 700.52 363.92 699.90 364.17C699.28 364.43 698.65 364.62 697.99 364.75C697.33 364.88 696.67 364.95 696.00 364.95C695.33 364.95 694.67 364.88 694.01 364.75C693.35 364.62 692.72 364.43 692.10 364.17C691.48 363.92 690.89 363.60 690.33 363.23C689.78 362.86 689.26 362.44 688.79 361.96C688.31 361.49 687.89 360.97 687.52 360.42C687.15 359.86 686.83 359.27 686.58 358.65C686.32 358.03 686.13 357.40 686.00 356.74C685.87 356.08 685.80 355.42 685.80 354.75C685.80 354.08 685.87 353.42 686.00 352.76C686.13 352.10 686.32 351.47 686.58 350.85C686.83 350.23 687.15 349.64 687.52 349.08C687.89 348.53 688.31 348.01 688.79 347.54C689.26 347.06 689.78 346.64 690.33 346.27C690.89 345.90 691.48 345.58 692.10 345.33C692.72 345.07 693.35 344.88 694.01 344.75C694.67 344.62 695.33 344.55 696.00 344.55C696.67 344.55 697.33 344.62 697.99 344.75C698.65 344.88 699.28 345.07 699.90 345.33C700.52 345.58 701.11 345.90 701.67 346.27C702.22 346.64 702.74 347.06 703.21 347.54C703.69 348.01 704.11 348.53 704.48 349.08C704.85 349.64 705.17 350.23 705.42 350.85C705.68 351.47 705.87 352.10 706.00 352.76C706.13 353.42 706.20 354.08 706.20 354.75" fill="#262626"/></svg>`;

function beeEl(): HTMLElement {
  const el = document.createElement("span");
  el.className = "bee";
  el.innerHTML = BEE;
  return el;
}

const FONT_FILES: [family: string, weight: string, path: string][] = [
  ["Poppins", "400", "fonts/poppins-400.woff2"],
  ["Poppins", "500", "fonts/poppins-500.woff2"],
  ["Poppins", "600", "fonts/poppins-600.woff2"],
  ["Poppins", "700", "fonts/poppins-700.woff2"],
  ["Playfair Display", "600", "fonts/playfair-600.woff2"],
];
let fontsRequested = false;

/**
 * Registers Poppins and Playfair Display for the overlay. The font bytes are read by the extension
 * and handed to FontFace directly, so a site's content security policy (font-src) cannot block them,
 * which a <style> with a chrome-extension:// url would be on sites like ChatGPT.
 */
function loadFonts() {
  if (fontsRequested || typeof chrome === "undefined" || !chrome.runtime?.getURL) return;
  fontsRequested = true;
  for (const [family, weight, path] of FONT_FILES) {
    void (async () => {
      try {
        const res = await fetch(chrome.runtime.getURL(path as never));
        const face = new FontFace(family, await res.arrayBuffer(), { weight });
        document.fonts.add(await face.load());
      } catch {
        /* the system font stack takes over */
      }
    })();
  }
}

export interface CardButton {
  id: string;
  label: string;
  kind?: "primary" | "danger" | "secondary";
}

export interface CardOptions {
  action: Action;
  title: string;
  reasons: string[];
  details?: string[];
  buttons: CardButton[];
  askReason?: boolean;
  /** Placed under the details, e.g. a safer rewrite. */
  preview?: { label: string; text: string };
}

export interface CardChoice {
  id: string;
  reason: string;
}

export class Overlay {
  private host: HTMLElement;
  private root: ShadowRoot;
  private layer: HTMLElement;
  private live: HTMLElement;
  private chipTimer = 0;
  private lastFocus: Element | null = null;

  constructor() {
    loadFonts();
    this.host = document.createElement("hive-overlay");
    this.root = this.host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = STYLE;
    this.layer = document.createElement("div");
    this.layer.className = "layer";
    this.live = document.createElement("div");
    this.live.className = "sr";
    this.live.setAttribute("aria-live", "polite");
    this.root.append(style, this.layer, this.live);
    document.documentElement.append(this.host);
  }

  private announce(text: string) {
    this.live.textContent = "";
    window.setTimeout(() => (this.live.textContent = text), 30);
  }

  /** Small notice under the composer: "2 items will be masked". */
  chip(text: string, ms = 6000) {
    this.layer.querySelector(".chip")?.remove();
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.append(beeEl(), document.createTextNode(text));
    this.layer.append(chip);
    this.announce(text);
    window.clearTimeout(this.chipTimer);
    this.chipTimer = window.setTimeout(() => chip.remove(), ms);
  }

  clearChip() {
    this.layer.querySelector(".chip")?.remove();
  }

  /** Quiet confirmation after a send, bottom right. */
  note(text: string, ms = 5000) {
    this.layer.querySelector(".note")?.remove();
    const el = document.createElement("div");
    el.className = "note";
    el.append(beeEl(), document.createTextNode(text));
    this.layer.append(el);
    this.announce(text);
    window.setTimeout(() => el.remove(), ms);
  }

  banner(text: string, action?: { label: string; onClick: () => void }) {
    this.layer.querySelector(".banner")?.remove();
    const el = document.createElement("div");
    el.className = "banner";
    el.setAttribute("role", "status");
    const span = document.createElement("span");
    span.textContent = text;
    el.append(span);
    if (action) {
      const b = document.createElement("button");
      b.textContent = action.label;
      b.addEventListener("click", action.onClick);
      el.append(b);
    }
    this.layer.append(el);
  }

  /** Shows a card and resolves with the button the person chose. Esc counts as "edit". */
  card(opts: CardOptions): Promise<CardChoice> {
    this.layer.querySelector(".cardwrap")?.remove();
    this.lastFocus = document.activeElement;
    const a = ACCENT[opts.action];
    const el = document.createElement("div");
    el.className = "card";
    el.dataset.action = opts.action;
    el.setAttribute("role", "alertdialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-labelledby", "hive-title");
    el.setAttribute("aria-describedby", "hive-desc hive-tip");

    // Header band in the outcome colour: the bee, the verdict chip, then the headline in its voice.
    const head = document.createElement("div");
    head.className = "head";
    const text = document.createElement("div");
    text.className = "head-text";
    const chipo = document.createElement("span");
    chipo.className = "chipo";
    const icon = document.createElement("i");
    icon.setAttribute("aria-hidden", "true");
    icon.append(lucideEl(a.icon, 14));
    chipo.append(icon, document.createTextNode(a.word));
    const h2 = document.createElement("h2");
    h2.id = "hive-title";
    h2.textContent = opts.title;
    text.append(h2);
    head.append(beeEl(), text, chipo);
    for (const [k, v] of Object.entries({
      "--bg": a.bg,
      "--fg": a.fg,
      "--solid": a.solid,
      "--dbg": a.dbg,
      "--dfg": a.dfg,
      "--dsolid": a.dsolid,
    }))
      el.style.setProperty(k, v);

    const main = document.createElement("div");
    main.className = "main";
    const desc = document.createElement("div");
    desc.id = "hive-desc";
    const [first, ...rest] = opts.reasons;
    if (first) {
      const p = document.createElement("p");
      p.textContent = first;
      desc.append(p);
    }
    main.append(desc);
    if (opts.details?.length) {
      const ul = document.createElement("ul");
      ul.className = "found";
      for (const d of opts.details) {
        const li = document.createElement("li");
        li.textContent = d;
        ul.append(li);
      }
      main.append(ul);
    }
    if (opts.preview) {
      const lab = document.createElement("label");
      lab.textContent = opts.preview.label;
      const code = document.createElement("code");
      code.textContent = opts.preview.text;
      main.append(lab, code);
    }
    if (rest.length) {
      const tip = document.createElement("p");
      tip.id = "hive-tip";
      tip.className = "tip";
      tip.textContent = rest.join(" ");
      main.append(tip);
    }
    const rib = document.createElement("div");
    rib.className = "ribbons";
    rib.setAttribute("aria-hidden", "true");
    rib.innerHTML = RIBBONS;
    el.append(rib, head, main);
    let reasonBox: HTMLTextAreaElement | null = null;
    if (opts.askReason) {
      const lab = document.createElement("label");
      lab.htmlFor = "hive-reason";
      lab.textContent = "Why do you need to send this? (saved with the log)";
      reasonBox = document.createElement("textarea");
      reasonBox.id = "hive-reason";
      main.append(lab, reasonBox);
    }
    const actions = document.createElement("div");
    actions.className = "actions";
    const hint = document.createElement("span");
    hint.className = "hint";
    hint.innerHTML = "<kbd>Esc</kbd> to edit";
    main.append(actions);
    const wrap = document.createElement("div");
    wrap.className = "cardwrap";
    const patrol = document.createElement("div");
    patrol.className = "patrol";
    patrol.setAttribute("aria-hidden", "true");
    const pbee = document.createElement("div");
    pbee.className = "pbee";
    const pin = document.createElement("span");
    pin.className = "bee";
    pin.innerHTML = BEE;
    pbee.append(pin);
    patrol.append(pbee);
    wrap.append(el, patrol);
    this.layer.append(wrap);
    this.announce(`${opts.title}. ${opts.reasons.join(" ")}`);

    return new Promise<CardChoice>((resolve) => {
      const done = (id: string) => {
        wrap.remove();
        document.removeEventListener("keydown", onKey, true);
        if (this.lastFocus instanceof HTMLElement) this.lastFocus.focus();
        resolve({ id, reason: reasonBox?.value.trim() ?? "" });
      };
      const rank = (k?: string) => (k === "primary" ? 0 : k === "danger" ? 2 : 1);
      const ordered = [...opts.buttons].sort((x, y) => rank(x.kind) - rank(y.kind));
      for (const b of ordered) {
        const btn = document.createElement("button");
        btn.type = "button";
        const bi = BUTTON_ICON[b.id];
        if (bi) btn.append(lucideEl(bi, 16));
        btn.append(document.createTextNode(b.label));
        if (b.kind && b.kind !== "secondary") btn.className = b.kind;
        btn.addEventListener("click", () => done(b.id));
        actions.append(btn);
      }
      const focusables = () => [...el.querySelectorAll<HTMLElement>("button, textarea")];
      const onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          done(opts.buttons.find((b) => b.id === "edit")?.id ?? "edit");
        } else if (e.key === "Tab") {
          const items = focusables();
          const first = items[0];
          const last = items[items.length - 1];
          const active = this.root.activeElement;
          if (!first || !last) return;
          if (e.shiftKey && active === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && active === last) {
            e.preventDefault();
            first.focus();
          }
        } else {
          // Keep keystrokes inside the card from reaching the AI site underneath.
          e.stopPropagation();
        }
      };
      actions.append(hint);
      document.addEventListener("keydown", onKey, true);
      (el.querySelector<HTMLElement>("button.primary") ?? focusables()[0])?.focus();
    });
  }
}
