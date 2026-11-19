#!/usr/bin/env python3
"""Draws the Sentry mascot (an arch-shaped gate guardian) in every pose the web app uses.

Usage: python3 scripts/make_mascot.py [out_dir ...]
Default output: web/public/mascot and docs/brand/mascot. Files keep the names thyro-<pose>.svg so the
app needs no change. Edit the constants or the POSES table, run again, commit the SVGs.
Animation is plain CSS inside each SVG and stops for prefers-reduced-motion.
"""

import sys
from pathlib import Path

INK = "#1a1713"
BODY, BODY_DK, BELLY = "#008278", "#004f49", "#d6f4f0"
OUTCOME = {
    "allow": "#30752a",
    "warn": "#915b00",
    "mask": "#764aa2",
    "local": "#1666aa",
    "block": "#b02a2d",
}
LAMP = {"default": "#f5b83d", **OUTCOME}
SW = 7  # outline width

GLYPH = {
    "allow": '<path d="M286 97 L296 107 L316 84"/>',
    "warn": '<path d="M300 80 V98"/><circle cx="300" cy="109" r="2" fill="#fff"/>',
    "mask": '<circle cx="287" cy="96" r="2.5" fill="#fff"/><circle cx="300" cy="96" r="2.5" fill="#fff"/><circle cx="313" cy="96" r="2.5" fill="#fff"/>',
    "local": '<path d="M284 98 L300 82 L316 98 M288 96 V112 H312 V96"/>',
    "block": '<path d="M289 84 L311 106 M311 84 L289 106"/>',
    "error": '<path d="M291 88 Q291 79 300 79 Q309 79 309 88 Q309 94 300 98 V102"/><circle cx="300" cy="111" r="2" fill="#fff"/>',
}


def eyes(kind: str, dx: float = 0, dy: float = 0) -> str:
    out = ""
    for cx in (165, 235):
        if kind == "happy":  # closed, smiling arcs
            out += f'<path d="M{cx-18} 142 Q{cx} 120 {cx+18} 142" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        elif kind == "sleepy":
            out += f'<path d="M{cx-17} 140 Q{cx} 152 {cx+17} 140" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        else:
            r = 28 if kind == "wide" else 25
            pr = 8 if kind == "wide" else 11
            out += (
                f'<circle cx="{cx}" cy="140" r="{r}" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                f'<circle cx="{cx+dx}" cy="{140+dy}" r="{pr}" fill="{INK}"/>'
                f'<circle cx="{cx+dx+4}" cy="{140+dy-4}" r="3" fill="#fff"/>'
            )
    return out


def brows(kind: str) -> str:
    if kind == "stern":
        return f'<path d="M140 108 L185 122 M260 108 L215 122" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
    if kind == "worried":
        return f'<path d="M142 118 L184 106 M258 118 L216 106" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "raised":
        return f'<path d="M145 105 Q165 92 185 105 M215 105 Q235 92 255 105" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    return ""


MOUTH = {
    "smile": f'<path d="M178 188 Q200 208 222 188" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>',
    "grin": f'<path d="M172 184 Q200 218 228 184 Z" fill="#fff" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>',
    "flat": f'<path d="M182 196 H218" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>',
    "frown": f'<path d="M180 202 Q200 184 220 202" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>',
    "o": f'<ellipse cx="200" cy="196" rx="9" ry="11" fill="{INK}"/>',
}


def arm(side: str, up: str = "down") -> str:
    out = 1 if side == "r" else -1  # +1 points away from the body on the right
    sx = 288 if side == "r" else 112
    # (outward offset from the shoulder, end y)
    ends = {"down": (28, 272), "wave": (44, 168), "stop": (40, 160), "up": (34, 188), "chin": (-40, 206)}
    off, ey = ends[up]
    ex = sx + out * off
    line = f'<line x1="{sx}" y1="238" x2="{ex}" y2="{ey}" stroke-linecap="round"'
    hand = ""
    if up == "stop":
        hand = f'<circle cx="{ex}" cy="{ey-8}" r="22" fill="{BODY}" stroke="{INK}" stroke-width="{SW}"/>'
    return f'{line} stroke="{INK}" stroke-width="32"/>{line} stroke="{BODY}" stroke-width="18"/>{hand}'


# pose -> (eyes kind, look dx, look dy, brows, mouth, lamp, badge, right arm, left arm, extras)
POSES = {
    "master": ("open", 0, 0, "", "smile", "default", None, "wave", "down", ""),
    "allow": ("happy", 0, 0, "", "grin", "allow", "allow", "down", "down", ""),
    "warn": ("wide", 0, 0, "raised", "o", "warn", "warn", "stop", "down", ""),
    "mask": ("open", -3, 0, "", "smile", "mask", "mask", "down", "down", "MASK"),
    "local": ("open", 0, 2, "", "smile", "local", "local", "down", "down", ""),
    "block": ("open", 0, 0, "stern", "flat", "block", "block", "stop", "down", ""),
    "empty": ("sleepy", 0, 0, "", "flat", "default", None, "down", "down", "ZZZ"),
    "thinking": ("open", 8, -8, "", "flat", "default", None, "chin", "down", "THINK"),
    "error": ("wide", 0, 0, "worried", "frown", "block", "error", "up", "up", "SWEAT"),
    "avatar": ("open", 0, 0, "", "smile", "default", None, "down", "down", ""),
}

CSS = """
.bob{animation:bob 3.2s ease-in-out infinite;transform-origin:200px 372px}
.glow{animation:glow 2.4s ease-in-out infinite;transform-origin:200px 32px}
.blink{animation:blink 5s infinite;transform-origin:200px 140px}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes glow{0%,100%{opacity:.25}50%{opacity:.5}}
@keyframes blink{0%,94%,100%{transform:scaleY(1)}97%{transform:scaleY(.1)}}
@media (prefers-reduced-motion:reduce){.bob,.glow,.blink{animation:none}}
"""


def extras(tag: str) -> str:
    if tag == "MASK":
        return (
            f'<rect x="124" y="112" width="152" height="56" rx="28" fill="{OUTCOME["mask"]}" stroke="{INK}" stroke-width="{SW}"/>'
            '<circle cx="165" cy="140" r="15" fill="#fff"/><circle cx="235" cy="140" r="15" fill="#fff"/>'
            f'<circle cx="162" cy="140" r="7" fill="{INK}"/><circle cx="232" cy="140" r="7" fill="{INK}"/>'
        )
    if tag == "ZZZ":
        return f'<g fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"><path d="M290 90 h22 l-22 24 h22"/><path d="M322 56 h15 l-15 17 h15"/></g>'
    if tag == "THINK":
        return (
            f'<g fill="{BELLY}" stroke="{INK}" stroke-width="5"><circle cx="300" cy="100" r="6"/>'
            '<circle cx="322" cy="76" r="9"/><circle cx="352" cy="44" r="15"/></g>'
        )
    if tag == "SWEAT":
        return '<path d="M262 106 Q272 124 262 132 Q252 124 262 106 Z" fill="#7bd0c6" stroke="#1a1713" stroke-width="4"/>'
    return ""


def svg(pose: str) -> str:
    ek, dx, dy, bk, mk, lamp, badge, ra, la, ex = POSES[pose]
    lamp_c = LAMP[lamp]
    body = (
        f'<path d="M110 358 V190 C110 108 150 70 200 70 C250 70 290 108 290 190 V358 Q290 372 276 372 H124 Q110 372 110 358 Z" fill="{BODY}" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
        f'<path d="M140 360 V232 Q140 196 200 196 Q260 196 260 232 V360 Z" fill="{BELLY}"/>'
        f'<circle cx="200" cy="262" r="15" fill="{BODY_DK}"/><path d="M192 268 H208 L213 316 H187 Z" fill="{BODY_DK}"/>'
    )
    glyph = ""
    if badge:
        glyph = (
            f'<circle cx="300" cy="95" r="30" fill="{OUTCOME[badge] if badge in OUTCOME else OUTCOME["block"]}" stroke="{INK}" stroke-width="6"/>'
            f'<g fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">{GLYPH[badge]}</g>'
        )
    cheeks = '<ellipse cx="136" cy="176" rx="14" ry="9" fill="#f7b8b0"/><ellipse cx="264" cy="176" rx="14" ry="9" fill="#f7b8b0"/>'
    head_eyes = ex == "MASK"
    lantern = (
        f'<line x1="200" y1="70" x2="200" y2="44" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        f'<circle class="glow" cx="200" cy="36" r="27" fill="{lamp_c}" opacity=".3"/>'
        f'<circle cx="200" cy="32" r="16" fill="{lamp_c}" stroke="{INK}" stroke-width="6"/>'
        '<circle cx="195" cy="27" r="4" fill="#fff" opacity=".8"/>'
    )
    vb = "90 6 220 250" if pose == "avatar" else "0 0 400 400"
    feet = f'<ellipse cx="160" cy="374" rx="26" ry="9" fill="{INK}"/><ellipse cx="240" cy="374" rx="26" ry="9" fill="{INK}"/>'
    face = eyes(ek, dx, dy) + brows(bk)
    if head_eyes:
        face = eyes(ek, dx, dy) + extras("MASK")
    inner = (
        ("" if pose == "avatar" else '<ellipse cx="200" cy="378" rx="120" ry="12" fill="#e3dfd9"/>')
        + f'<g class="bob">{"" if pose == "avatar" else arm("l", la) + (arm("r", ra) if ra != "chin" else "") + feet}{body}{arm("r", ra) if ra == "chin" else ""}{lantern}{cheeks}'
        f'<g class="blink">{face}</g>{MOUTH[mk]}{"" if head_eyes else extras(ex)}{glyph}</g>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="400" height="400" role="img" aria-label="Sentry, the gate guardian">'
        f"<style>{CSS}</style>{inner}</svg>\n"
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    outs = [Path(a) for a in sys.argv[1:]] or [root / "web/public/mascot", root / "docs/brand/mascot"]
    for out in outs:
        out.mkdir(parents=True, exist_ok=True)
        for pose in POSES:
            (out / f"thyro-{pose}.svg").write_text(svg(pose))
        print(f"wrote {len(POSES)} poses to {out}")


if __name__ == "__main__":
    main()
