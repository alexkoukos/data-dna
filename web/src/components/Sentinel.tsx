import { SENTINEL_SVG } from "./sentinelSvg";

/** The sentinel. It hovers and its eye scans; both stop for people who ask for reduced motion. */
export function Sentinel({ size = 96, className = "" }: { size?: number; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`sentinel inline-block shrink-0 ${className}`}
      style={{ width: size }}
      dangerouslySetInnerHTML={{ __html: SENTINEL_SVG }}
    />
  );
}
