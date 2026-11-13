# Pyli brand

Pyli (πύλη, "gate") is the company AI gateway. The brand is a gatekeeper: calm, exact, and always ready to say why.

One-page overview: [`docs/brand/brand-sheet.png`](brand/brand-sheet.png) (source: `brand-sheet.html`).

## Name

The product is **Pyli** (πύλη), and in plain words it is **the gate**. Say it that way everywhere: in the UI, the README, the pitch and the video.

| Say | Not |
|---|---|
| Pyli, the gate | Data DNA, the gateway |
| Every prompt passes the gate. | Every request goes through the gateway. |
| The gate masked 2 card numbers. | The system sanitized the data. |
| Gate address | Gateway URL |

"Gateway" stays only inside code and API paths (`gateway/`, `/gateway/v1`). Anything a person reads says "the gate". The repo and some internal names still say Data DNA; they are being renamed as files are touched.

## Idea

**A closed gate with a lit lamp.** Two stone pillars, an arched iron gate between them, one lamp on top. The gate is shut by default; the lamp shows someone is on duty. The lamp is the only brand-colored part of the mark, and it returns as the dot on the wordmark's *i* and as the mascot's light.

Material palette: verdigris (the green patina old bronze gates get after years outside), marble and iron ink. Nothing glows, nothing has a gradient.

## Logo

| File | Use |
|---|---|
| `brand/logo/pyli-logo.svg` / `-dark.svg` | Primary lockup, light / dark backgrounds |
| `brand/logo/pyli-mark.svg` / `-dark.svg` | Mark alone (nav, avatars, slides) |
| `brand/logo/pyli-mark-mono.svg` | One color, uses `currentColor` |
| `brand/logo/pyli-wordmark.svg` / `-dark.svg` | Wordmark alone |
| `brand/logo/pyli-app-icon.svg` | Mark on a verdigris tile (OS icons, social) |
| `brand/favicon/favicon.svg`, `.ico`, `favicon-16/32/48.png`, `apple-touch-icon.png`, `icon-512.png` | Browser and device icons |

All text is converted to outlines. PNGs are exported at 256 px and 512 px height (`@2x`).

The wordmark is Commissioner SemiBold with the flair axis at 100, tracked -2%. The dot of the *i* is replaced by the lamp.

**Favicon.** Below 24 px the full mark turns to mush, so the favicon is drawn separately on a 16 px pixel grid: two bars instead of three, no finials. It sits on a verdigris tile, so it works on light and dark browser chrome.

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

**Clear space:** at least 1/4 of the mark height on every side (roughly one pillar width).
**Minimum size:** lockup 96 px wide; mark 24 px; below that, the favicon drawing.

Do
- Use ink on light, marble on dark. Keep the lamp verdigris.
- Use the app icon tile when the background is busy or mid-tone.

Don't
- Recolor the gate with outcome colors. The lamp shows decisions in the mascot, not in the logo.
- Stretch, rotate, outline, add shadows or gradients.
- Rebuild the wordmark from a live font. Use the outlined file.

## Mascot: Thyro

Thyro is the gate itself: two stone pillars with verdigris finials, an arched iron gate, a round marble medallion with his face, and the lamp on top. Named after the θυρωρός, the doorman Athenian apartment blocks used to have. He knows who lives there, lets the right people in, and never raises his voice.

He shows a decision three ways at once, so it never depends on color: the gate leaves (open, ajar, shut), his face, and the lamp color. The outcome label always sits next to him.

| File | Gate | Face | Lamp |
|---|---|---|---|
| `brand/mascot/thyro-master.svg` | Shut | Calm smile | brand-400 |
| `thyro-allow.svg` | Wide open, path dots | Happy eyes, grin | allow |
| `thyro-warn.svg` | Ajar | One brow up, "hmm" | warn |
| `thyro-mask.svg` | Ajar | Wink | mask, taped over |
| `thyro-local.svg` | Shut | Looks up at the lamp | local, circling home |
| `thyro-block.svg` | Shut and latched | Calm, level brows, flat mouth | block |
| `thyro-empty.svg` | Shut | Glances to the side, waiting | Unlit (ink-300) |
| `thyro-avatar.svg` | Crop | Medallion and lamp | brand-400 |

PNG exports (720 px) are in `brand/mascot/png/`.

Rules
- Never show an outcome with Thyro alone. The badge with its label goes next to him.
- **Make him big.** He is the face of the product: 160 px at the very least, 200 to 360 px on empty states, errors, the home screen and decision cards. The avatar is the only small version (48 px minimum).
- **He always moves** (see Motion). The SVG files are animated; use them as `<img>`, no script needed.
- No alarm: no sweat drops, no shouting, no flashing. Block is a shut gate, not a siren.
- Empty states: pose, one sentence, one action. "Nothing has come through the gate yet. Connect a tool to start."
- Same line weight everywhere (5 px at 240 px). Don't add arms, shading or gradients.

## Motion

Animation is part of the brand, everywhere: calm, purposeful, and it always answers something (a decision, a touch, a state change).

**Thyro (inside each SVG).** On load he pops in, the gate leaves swing to their pose (open, ajar or shut) and then he idles: a slow float, the lamp breathing with its halo, the finials flickering, a blink every few seconds.

| Pose | What he does |
|---|---|
| master | Smiles wider now and then |
| allow | Gate swings open, path dots flow through, he hops with a grin |
| warn | Gate half open, eyebrow rises, eyes glance, head tilts: "hmm" |
| mask | Tape slides over the lamp, he winks |
| local | Lamp circled by a dotted ring that keeps orbiting, eyes look up at it |
| block | Latch drops across the gate, a tiny firm shake, never a siren |
| empty | Glances left and right, waiting; the lamp stays unlit |

**Interface.** Pages and list items fade up, staggered. Outcome chips pop in when a decision lands. Skeletons shimmer. Buttons lift on hover and press in on click. The nav slides in and the logo sways.

Timing: 0.2 to 0.55 s for interface, 3 to 6 s for idle loops. Easing is a soft ease-out (`cubic-bezier(0.2, 0.8, 0.2, 1)`); one gentle overshoot is allowed on pop-ins.

**Reduced motion.** Everything stops under `prefers-reduced-motion: reduce` and the final frame stays. Never rely on motion alone to carry meaning: the label is always there.

## Color

Tokens live in `web/src/index.css` under `@theme static`. Names are unchanged; paste the values from `web/src/pyli-tokens.css`.

**brand** (verdigris)

| 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 |
|---|---|---|---|---|---|---|---|---|---|
| `#ecfaf8` | `#d6f4f0` | `#aee6df` | `#7bd0c6` | `#3bada2` | `#008278` | `#006860` | `#004f49` | `#003632` | `#00201d` |

**ink** (cool stone greys)

| 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 |
|---|---|---|---|---|---|---|---|---|---|
| `#f7f8fa` | `#eef0f3` | `#e1e4e9` | `#c9ced6` | `#9aa1ad` | `#6b7280` | `#555c69` | `#3f4551` | `#2a2f38` | `#161a21` |

**Outcomes**

| Outcome | bg | fg | solid | Meaning |
|---|---|---|---|---|
| allow | `#e5f6e3` | `#245420` | `#30752a` | Nothing sensitive, sent as is |
| warn | `#f9efda` | `#704500` | `#915b00` | Sent, with a note to the user |
| mask | `#f4ecff` | `#553674` | `#764aa2` | Sensitive parts replaced, rest sent |
| local | `#e5f2ff` | `#154a7a` | `#1666aa` | Answered by a local model, nothing left |
| block | `#ffebe9` | `#7e2122` | `#b02a2d` | Not sent, reason shown |

Rules
- Every outcome carries its label (and ideally the dot or icon). Color is never the only signal.
- Badge on tint: `fg` on `bg`. Strong badge or row marker: white on `solid`.
- Primary button: `brand-600` (hover `brand-700`), white text. One per screen.
- Body text `ink-900`, secondary `ink-600`, tertiary `ink-500`. Page `ink-50`, cards white, borders `ink-200`.
- Brand and outcome hues are spaced apart on purpose (verdigris 186°, allow 142°, local 250°), so a brand button never reads as a decision.

### Contrast (WCAG 2.1)

Normal text needs 4.5:1, large text and UI graphics 3:1.

| Pair | Ratio | Use |
|---|---:|---|
| white on brand-500 | 4.70 | min for text |
| white on brand-600 | 6.67 | buttons, links |
| white on brand-700 | 9.48 | buttons, links |
| white on brand-800 | 13.34 | headings, dark surfaces |
| white on brand-900 | 17.15 | headings, dark surfaces |
| ink-500 on white | 4.92 | tertiary text, placeholders |
| ink-600 on white | 6.66 | secondary text |
| ink-700 on white | 9.81 | body on tinted |
| ink-900 on white | 17.86 | primary text |
| ink-500 on ink-50 | 4.61 | page background |
| ink-600 on ink-50 | 6.24 | page background |
| ink-900 on ink-50 | 16.73 | page background |
| ink-50 on ink-900 | 16.73 | dark surfaces |
| brand-300 on ink-900 | 9.93 | dark-mode accent |
| allow: fg on bg / fg on white / white on solid / solid vs bg | 7.88 / 8.88 / 5.67 / 5.03 | badges, rows, banners |
| warn: fg on bg / fg on white / white on solid / solid vs bg | 7.24 / 8.27 / 5.68 / 4.97 | badges, rows, banners |
| mask: fg on bg / fg on white / white on solid / solid vs bg | 8.44 / 9.69 / 6.42 / 5.59 | badges, rows, banners |
| local: fg on bg / fg on white / white on solid / solid vs bg | 8.06 / 9.16 / 5.97 / 5.26 | badges, rows, banners |
| block: fg on bg / fg on white / white on solid / solid vs bg | 8.61 / 9.87 / 6.53 / 5.70 | badges, rows, banners |

Avoid as text: `brand-50..400` and `ink-50..400` on white (all under 3:1). Use them for fills, borders and disabled states.

## Type

| Role | Font | Notes |
|---|---|---|
| UI and display | **Commissioner** (variable, OFL) | By Greek type designer Kostas Bartsokas. Full Greek. Flair axis `FLAR` 0 for UI, 100 for display (30 px and up) |
| Code, IDs, redactions | **JetBrains Mono** (variable, OFL) | Full Greek |

Self-hosted through npm and bundled by Vite. No runtime network calls.

```bash
npm i @fontsource-variable/commissioner @fontsource-variable/jetbrains-mono
```
```ts
// web/src/main.tsx
import '@fontsource-variable/commissioner/flar.css'; // weight + flair, Latin + Greek
import '@fontsource-variable/jetbrains-mono';
```

Scale (px, size / line height / weight)

| Token | Size | Line height | Weight | Use |
|---|---|---|---|---|
| text-xs | 12 | 16 | 500 | Labels, captions, ALL CAPS eyebrows (+8% tracking) |
| text-sm | 14 | 20 | 400 / 600 | Table cells, badges, secondary text |
| text-base | 16 | 24 | 400 | Body |
| text-lg | 18 | 28 | 500 | Lead text, card titles |
| text-xl | 20 | 28 | 600 | Section titles in the app |
| text-2xl | 24 | 32 | 600 | Page titles in the app |
| text-3xl | 30 | 36 | 600 | Display starts here, flair 100 |
| text-4xl | 36 | 44 | 600 | |
| text-5xl | 48 | 52 | 600 | Slide titles |
| text-6xl | 60 | 64 | 600 | Hero |
| text-7xl | 72 | 76 | 700 | One per page at most |

Weights: 400 body, 500 labels, 600 headings and buttons, 700 only for one hero. Display sizes get -2% tracking. Body stays at 45 to 75 characters per line.

## Shape

- Radius: 6 px (badges, chips), 10 px (buttons, inputs), 14 px (cards), 20 px (dialogs). Never mix with square corners.
- Touch targets at least 44 px tall. Default button height 44 px, padding 16 px horizontal.
- Shadows stay soft and low; separate with spacing and white cards on `ink-50` before adding borders.

## Voice

Calm, precise, a guardian that explains itself and never shouts.

- Short sentences. Strong verbs. Say what happened, then why.
- Name the thing: "2 card numbers", "customer records", "ChatGPT".
- Offer the next step when the user is stuck.
- No buzzwords, no exclamation marks, no "Oops".

| Say | Not |
|---|---|
| Masked 2 card numbers. The rest went through. | Sensitive data detected and sanitized! |
| Blocked. This prompt holds customer records, and ChatGPT is not approved for them. | THREAT BLOCKED 🚨 |
| Answered locally. Nothing left the building. | Leveraging on-prem AI for enhanced privacy. |
| Heads up: this looks like source code. Sent anyway. | Warning: potential policy violation. |
| Found 3 AI tools nobody told us about. | Shadow AI risk surface identified. |

Tagline: **Every prompt passes the gate.**
