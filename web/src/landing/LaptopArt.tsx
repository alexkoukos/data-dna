import { useId } from "react";
import { HOLE } from "./geometry";

// A front-view laptop drawn as vector, in the 812 x 480 space of the hero. The display is a real
// hole (even-odd), so whatever sits behind this drawing shows through. No logo, no photo.

export function LaptopArt({ className }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  const g = (name: string) => `${name}-${id}`;
  const { x, y, w, h } = HOLE;
  const lid = { x: 94, y: 18, w: 603, h: 404, r: 17 };
  // Outer lid and display hole as one path: the hole stays see-through.
  const lidPath =
    `M${lid.x + lid.r} ${lid.y}H${lid.x + lid.w - lid.r}a${lid.r} ${lid.r} 0 0 1 ${lid.r} ${lid.r}` +
    `V${lid.y + lid.h}H${lid.x}V${lid.y + lid.r}a${lid.r} ${lid.r} 0 0 1 ${lid.r} -${lid.r}Z` +
    `M${x} ${y}H${x + w}V${y + h}H${x}Z`;

  return (
    <svg
      className={className}
      width="812"
      height="480"
      viewBox="0 0 812 480"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={g("lid")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2b2c2f" />
          <stop offset="0.5" stopColor="#151517" />
          <stop offset="1" stopColor="#0c0c0d" />
        </linearGradient>
        <linearGradient id={g("rim")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f4f5f7" />
          <stop offset="0.35" stopColor="#c9ccd1" />
          <stop offset="1" stopColor="#8d9199" />
        </linearGradient>
        <linearGradient id={g("base")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f2f3f5" />
          <stop offset="0.22" stopColor="#d6d9dd" />
          <stop offset="0.7" stopColor="#b3b7be" />
          <stop offset="1" stopColor="#8f939b" />
        </linearGradient>
        <linearGradient id={g("sheen")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.18" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.05" />
          <stop offset="0.82" stopColor="#fff" stopOpacity="0.5" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={g("endL")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0.28" />
          <stop offset="1" stopColor="#000" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={g("endR")} x1="1" y1="0" x2="0" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0.28" />
          <stop offset="1" stopColor="#000" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={g("thumb")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7d8189" />
          <stop offset="1" stopColor="#c2c5cb" />
        </linearGradient>
        <radialGradient id={g("lens")} cx="0.35" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#3b4a66" />
          <stop offset="0.5" stopColor="#141a26" />
          <stop offset="1" stopColor="#05060a" />
        </radialGradient>
        <clipPath id={g("baseClip")}>
          <path d="M34 424H757a3 3 0 0 1 3 3V428a12 12 0 0 1-12 12H43a12 12 0 0 1-12-12V427a3 3 0 0 1 3-3Z" />
        </clipPath>
      </defs>

      {/* Aluminium edge of the lid, a hair outside the glass */}
      <rect
        x={lid.x - 1}
        y={lid.y - 1}
        width={lid.w + 2}
        height={lid.h + 2}
        rx={lid.r + 1}
        fill="none"
        stroke={`url(#${g("rim")})`}
        strokeWidth="2.4"
      />
      {/* Glass and black bezel with the display cut out */}
      <path d={lidPath} fillRule="evenodd" fill={`url(#${g("lid")})`} />
      {/* Display edge: a thin dark line that sells the depth of the glass */}
      <rect
        x={x - 0.5}
        y={y - 0.5}
        width={w + 1}
        height={h + 1}
        rx="2"
        fill="none"
        stroke="#000"
        strokeOpacity="0.7"
      />

      {/* Notch with camera */}
      <path d={`M${x + 254} ${y}h70v8a5 5 0 0 1-5 5h-60a5 5 0 0 1-5-5Z`} fill="#050506" />
      <circle cx={x + 289} cy={y + 5.5} r="2.6" fill={`url(#${g("lens")})`} />
      <circle cx={x + 288.2} cy={y + 4.7} r="0.7" fill="#9db4e0" opacity="0.8" />

      {/* Hinge shadow, then the base slab (centred under the lid) */}
      <rect x="96" y="414" width="599" height="8" fill="#000" opacity="0.5" />
      <path
        d="M31 424H760V428a12 12 0 0 1-12 12H43a12 12 0 0 1-12-12Z"
        fill={`url(#${g("base")})`}
      />
      <g clipPath={`url(#${g("baseClip")})`}>
        <path d="M31 424H760" stroke="#fff" strokeOpacity="0.9" strokeWidth="1" />
        <rect x="31" y="424" width="729" height="16" fill={`url(#${g("sheen")})`} opacity="0.3" />
        <rect x="31" y="424" width="46" height="16" fill={`url(#${g("endL")})`} />
        <rect x="714" y="424" width="46" height="16" fill={`url(#${g("endR")})`} />
      </g>
      {/* Thumb notch */}
      <path
        d="M316 424h160a4 4 0 0 1-4 5a60 7 0 0 1-152 0a4 4 0 0 1-4-5Z"
        fill={`url(#${g("thumb")})`}
      />
      <path d="M43 440H748" stroke="#6d7077" strokeOpacity="0.55" strokeWidth="1" />

      {/* Light catching the top edge of the lid */}
      <path
        d={`M${lid.x + lid.r} ${lid.y + 0.5}H${lid.x + lid.w - lid.r}`}
        stroke="#fff"
        strokeOpacity="0.45"
        strokeWidth="1"
      />
    </svg>
  );
}
