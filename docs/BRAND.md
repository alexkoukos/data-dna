# Pyli brand guide

The one-page sheet is [brand/brand-sheet.png](brand/brand-sheet.png). This file is the text version, with the values to copy into code.

Pyli (Greek: πύλη, "gate") is the brand name of Data DNA, the company AI gateway.
Tagline: **Every prompt passes the gate.**

## Brand idea

A closed gate with a lit lamp. The gate is shut by default, which means protected. The lamp means someone is on duty. Pyli is the calm gatekeeper between the company and the AI tools outside.

Personality: calm, precise, trustworthy, a little witty. It explains itself and never shouts. It is not a scary fortress and not a cute toy.

Three materials, no glow effects:
- **Verdigris**: the blue-green patina of old bronze gates. Built to last, not to flash.
- **Marble**: warm off-white stone, the pillars.
- **Iron ink**: near-black warm iron, the bars and outlines.

Cultural story: the **θυρωρός**, the doorman of every Athenian πολυκατοικία. He knows who lives there, lets the right people in, keeps strangers out, and never raises his voice.

Visual style: flat shapes, one ink outline, rounded corners, no gradients, no 3D, no gloss. No lock, shield or padlock clichés, no circuit boards, no robots.

## Logo

- **Mark:** front-facing iron gate between two stone pillars, drawn on a 32 × 32 grid. Pillars have a capital slab and an onion-shaped finial. Between them an arched gate with three bars and one rail. The **lamp** (solid circle on a short stem at the arch apex) is the only part in brand color.
- **Wordmark:** "Pyli" in Commissioner SemiBold 600, flair axis 100, tracking -2%. The dot of the **i** is the lamp circle in verdigris. Text converted to outlines.
- **Lockup:** mark left, wordmark right, gate bottom on the text baseline, finials rise above the letters.
- **App icon:** mark on a brand-700 tile, radius about 22%.
- **Favicon:** drawn by hand on a 16 px grid, not scaled down. brand-700 tile, marble gate, two bars, no finials, 2 × 2 px lamp in brand-300.

Usage:
- Clear space: at least 1/4 of the mark height on every side.
- Minimum size: 96 px wide for the lockup, 24 px for the mark. Below that, use the favicon drawing.
- Never recolor the gate with outcome colors, stretch, rotate, outline it, or add shadows or gradients. Do not place the dark logo on mid-tone photos.

## Mascot: Thyro

Thyro is the gate itself, the logo come alive. Named after the θυρωρός. No arms, no legs, no body. Two marble pillars with verdigris finials, an iron arch, a marble medallion face, the lamp with a soft halo, two gate leaves, a faint ground shadow. One ink outline weight (5 px at 240 px), flat fills only.

He shows each decision three ways at once (gate leaves, face, lamp color), and the text label always sits next to him.

| Pose | Gate leaves | Face | Lamp |
|---|---|---|---|
| Master | Shut | Calm small smile | brand-400 |
| Allow | Fully open, dotted path through | Closed-arc eyes, open grin | allow solid |
| Warn | Ajar | One brow raised, wavy mouth | warn solid |
| Mask | Ajar | Winks, smile | mask solid, ink tape across lamp |
| Local | Shut | Looks up at lamp, smile | local solid, dotted arrow circling |
| Block | Shut, red latch bar | Half-lidded eyes, level brows, flat mouth | block solid |
| Empty state | Shut | Glances aside, no mouth | Unlit (ink-300, no halo) |
| Avatar | Square crop of medallion and lamp | Calm smile | brand-400 |

Rules: never childish, never scary. No sweat drops, no exclamation marks, no flashing red. Block is a shut gate, not a siren. Use at 96 px or larger (avatar down to 48 px). Empty states get the pose, one sentence and one action.

## Color

Page background ink-50, cards white, borders ink-200. Text: ink-900 primary, ink-600 secondary, ink-500 tertiary. Primary button: brand-600 with white text (6.67:1), hover brand-700. On dark surfaces (ink-900): ink-50 text, brand-300 for lamp and accents.

brand-50 to 400 and ink-50 to 400 are never used for text on white. Text needs 4.5:1, so brand-500+ and ink-500+ only.

| Step | brand (verdigris) | ratio on white | ink (warm marble) | ratio on white |
|---|---|---|---|---|
| 50 | #ecfaf8 | 1.07 | #faf7f4 | 1.07 |
| 100 | #d6f4f0 | 1.16 | #f1efec | 1.15 |
| 200 | #aee6df | 1.38 | #e3dfd9 | 1.33 |
| 300 | #7bd0c6 | 1.80 | #ccc8c3 | 1.66 |
| 400 | #3bada2 | 2.73 | #a5a19b | 2.57 |
| 500 | #008278 | 4.70 | #74706b | 4.92 |
| 600 | #006860 | 6.67 | #5f5c57 | 6.66 |
| 700 | #004f49 | 9.48 | #47433e | 9.81 |
| 800 | #003632 | 13.34 | #312d29 | 13.65 |
| 900 | #00201d | 17.15 | #1a1713 | 17.86 |

Outcomes. Badges use fg on bg, strong markers use white on solid. Every outcome always carries its text label and icon, never color alone.

| Outcome | bg | fg | solid | fg/bg | white/solid |
|---|---|---|---|---|---|
| Allow | #e5f6e3 | #245420 | #30752a | 7.9 | 5.7 |
| Warn | #f9efda | #704500 | #915b00 | 7.2 | 5.7 |
| Mask | #f4ecff | #553674 | #764aa2 | 8.4 | 6.4 |
| Local | #e5f2ff | #154a7a | #1666aa | 8.1 | 6.0 |
| Block | #ffebe9 | #7e2122 | #b02a2d | 8.6 | 6.5 |

## Typography

Both fonts are free (OFL), self-hostable via Fontsource, and support Greek.

- **Commissioner** (variable) for UI and display. Flair axis `FLAR` 0 for UI text, 100 for display (30 px and up) and the wordmark. Display tracking -2%.
- **JetBrains Mono** (variable) for code, IDs and redacted values.

| Size (px) | 12 | 14 | 16 | 18 | 20 | 24 | 30 | 36 | 48 | 60 | 72 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Line height | 16 | 20 | 24 | 28 | 28 | 32 | 36 | 44 | 52 | 64 | 76 |
| Weight | 500 | 400/600 | 400 | 500 | 600 | 600 | 600 | 600 | 600 | 600 | 700 |

Weights: 400 body, 500 labels, 600 headings and buttons, 700 for one hero only. Eyebrows: 12 px ALL CAPS, +8% tracking, brand-700. Body lines 45 to 75 characters.

## Shape

Corners are always rounded: 6 px (badges, chips), 10 px (buttons, inputs), 14 px (cards), 20 px (dialogs), about 22% for the app icon tile. Touch targets at least 44 px. Depth comes from spacing and white cards on ink-50 first, then soft low shadows.

## Voice

Calm, precise, explains itself. Short sentences, strong verbs. Say what happened, then why, then the next step. Name the real thing ("2 card numbers", "customer records", "ChatGPT"). No buzzwords, no exclamation marks, no "Oops", no fear-mongering.

| Say | Not |
|---|---|
| Masked 2 card numbers. The rest went through. | Sensitive data detected and sanitized! |
| Blocked. This prompt holds customer records, and ChatGPT is not approved for them. | THREAT BLOCKED 🚨 |
| Answered locally. Nothing left the building. | Leveraging on-prem AI for enhanced privacy. |
| Heads up: this looks like source code. Sent anyway. | Warning: potential policy violation. |
| Found 3 AI tools nobody told us about. | Shadow AI risk surface identified. |

Greek:
- Έκρυψα 2 αριθμούς κάρτας. Τα υπόλοιπα στάλθηκαν.
- Απαντήθηκε τοπικά. Τίποτα δεν βγήκε έξω.

## Brand stories (pitch and About page)

1. **Why a gate.** Every AI tool an employee uses is a door out of the company. Pyli puts one calm gatekeeper at all of them.
2. **The doorman.** The θυρωρός didn't stop life in the building, he made it safe. Thyro is that doorman for your prompts.
3. **The lamp.** A lit lamp means someone is on duty. Pyli's lamp takes the color of each decision, and it always comes with words.
4. **Verdigris.** Bronze turns green after years of standing guard. The color says this was built to last.
5. **The five decisions.** Most prompts aren't good or bad. They are mostly fine, with one line that shouldn't leave. So Pyli has five answers.

## Tokens for `web/src/index.css`

Not applied yet. The app still uses the old indigo tokens. When a task adopts the brand, replace the `@theme` block with this one and add Commissioner and JetBrains Mono through Fontsource (`npm install`, commit the lock file).

```css
@theme static {
  --font-sans: Commissioner, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, Menlo, monospace;

  --color-brand-50: #ecfaf8;
  --color-brand-100: #d6f4f0;
  --color-brand-200: #aee6df;
  --color-brand-300: #7bd0c6;
  --color-brand-400: #3bada2;
  --color-brand-500: #008278;
  --color-brand-600: #006860;
  --color-brand-700: #004f49;
  --color-brand-800: #003632;
  --color-brand-900: #00201d;

  --color-ink-50: #faf7f4;
  --color-ink-100: #f1efec;
  --color-ink-200: #e3dfd9;
  --color-ink-300: #ccc8c3;
  --color-ink-400: #a5a19b;
  --color-ink-500: #74706b;
  --color-ink-600: #5f5c57;
  --color-ink-700: #47433e;
  --color-ink-800: #312d29;
  --color-ink-900: #1a1713;

  --color-allow-bg: #e5f6e3;
  --color-allow-fg: #245420;
  --color-allow-solid: #30752a;
  --color-warn-bg: #f9efda;
  --color-warn-fg: #704500;
  --color-warn-solid: #915b00;
  --color-mask-bg: #f4ecff;
  --color-mask-fg: #553674;
  --color-mask-solid: #764aa2;
  --color-local-bg: #e5f2ff;
  --color-local-fg: #154a7a;
  --color-local-solid: #1666aa;
  --color-block-bg: #ffebe9;
  --color-block-fg: #7e2122;
  --color-block-solid: #b02a2d;
}
```

## Still missing

The sheet shows the design. These files from the original brief are not in the repo yet: `docs/brand/logo/`, `docs/brand/favicon/`, `docs/brand/mascot/` (SVG and PNG exports of the mark, wordmark, Thyro poses and favicon).
