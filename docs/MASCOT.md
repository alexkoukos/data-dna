# Thyro, the Pyli mascot: states, speech and where he lives

Thyro is the gate itself (see `docs/BRAND.md`). The label (Allowed, Masked, Warned, Answered locally, Blocked) always carries the meaning; he is decoration and is hidden from screen readers.

## States

| State | File | What he does |
|---|---|---|
| idle | `thyro-master.svg` | Blinks every few seconds, lamp breathes, floats |
| allow | `thyro-allow.svg` | Gate swings open, path dots flow, he hops |
| warn | `thyro-warn.svg` | Gate half open, brow up, head tilts |
| mask | `thyro-mask.svg` | Tape slides over the lamp, he winks |
| local | `thyro-local.svg` | Lamp circled by a dotted ring, looks up |
| block | `thyro-block.svg` | Latch drops, tiny firm shake |
| thinking | `thyro-thinking.svg` | Eyes scan left and right, a ring spins around the lamp |
| empty | `thyro-empty.svg` | Looks around, lamp unlit |
| error | `thyro-error.svg` | Shrugs, lamp flickers |
| avatar | `thyro-avatar.svg` | Face crop, 48 px minimum |

SVGs live in `docs/brand/mascot/` (source of truth) and `web/public/mascot/` (served). Animation is inside each SVG (CSS keyframes plus one SMIL gate swing), no library, no script. Under `prefers-reduced-motion` the keyframes stop and the final pose stays. Layer ids: `left-arm` and `right-arm` (the gate leaves), `lintel` (arch), `body` (pillars), `head`, `eye`, `brow`, `prop-mask` (tape), `prop-house` (the "stays home" ring), `prop-door` (latch).

## Speech

Fixed lines, English and Greek, 80 characters at most, no exclamation marks: `web/src/mascot/mascot.copy.json`. Look them up with `line(state, lang)` from `web/src/mascot/copy.ts`. The language follows `localStorage["pyli.lang"]`, else the browser. A Vitest test checks every state has both languages and stays within 80 characters.

## Where he lives

- **Everywhere:** `<Thyro pose size />` (`web/src/components/Thyro.tsx`) in chat replies (the pose of each decision), the home screen, empty states, error screens (`error`), loading (`thinking`), the incident list and detail, Connect.
- **Companion:** `web/src/components/Companion.tsx`, mounted once in `App.tsx`. Bottom right by default; the arrow button moves him to the bottom left (remembered in `localStorage["pyli.companion"]`), the cross hides him. He reacts to every decision made in chat (`announce(outcome)` from `web/src/lib/companion.ts`) and to every new incident from any other tool (polls every 5 s). On the chat screen he sits above the message box so he never covers it.
- **Picture in picture:** the square button floats him on top of other windows. Chrome and Edge 116+ use Document Picture-in-Picture (a real window rendered by React, same styles). Browsers without it but with video PiP (Safari) get a canvas video fallback. Others show no button. It needs a click and a secure context (`localhost` or https). "Bring him back" returns him to the page.

## Add a state

1. Add the pose to `thyro_gen.py`-style source or draw an SVG in `docs/brand/mascot/`; keep the ids above and the reduced-motion rule.
2. Copy it to `web/public/mascot/`, add the name to `ThyroPose` in `Thyro.tsx`.
3. Add its line (en and el) to `mascot.copy.json`.
4. Use it where the state happens.

## Run

`npm run dev` in `web` (or `make up`), open `/chat`, send "Can you check if this IBAN looks right? GR1601101250000000012300695" and watch the mask pose; click the PiP button to float him. Tests: `npm test`, `make e2e` (e2e runs with reduced motion so axe sees final colors).

## Not built yet

Storyboard player and exported WebM/MP4/GIF, transparent WebM per state, the desktop companion (Electron or Tauri), a "Try to break it" page, speech bubbles per chat reply, arms and hand/house/mask props (Thyro has no arms by brand rule), crossfade between poses.
