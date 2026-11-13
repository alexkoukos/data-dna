export type ThyroPose =
  | "master"
  | "allow"
  | "warn"
  | "mask"
  | "local"
  | "block"
  | "empty"
  | "avatar"
  | "thinking"
  | "error";

/** Presentational: the Pyli mascot, animated (the animation lives inside the SVG and stops when the
 * person asks for reduced motion). Decorative: the outcome label always sits next to it. Use him big. */
export function Thyro({ pose, size = 160 }: { pose: ThyroPose; size?: number }) {
  return (
    <img
      src={`${window.location.origin}/mascot/thyro-${pose}.svg`}
      alt=""
      width={size}
      height={size}
      style={{ maxWidth: "100%", height: "auto" }}
      className="thyro-img shrink-0 select-none"
    />
  );
}
