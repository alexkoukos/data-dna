import { BEE_SVG } from "./beeSvg";

/** The guard bee. It hovers and its wings beat; both stop for people who ask for reduced motion. */
export function Bee({ size = 96, className = "" }: { size?: number; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`bee inline-block shrink-0 ${className}`}
      style={{ width: size }}
      dangerouslySetInnerHTML={{ __html: BEE_SVG }}
    />
  );
}
