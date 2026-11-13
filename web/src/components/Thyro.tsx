export type ThyroPose =
  "master" | "allow" | "warn" | "mask" | "local" | "block" | "empty" | "avatar";

/** Presentational: the Pyli mascot. Decorative: the outcome label always sits next to it. Use at 96 px or larger (avatar 48 px). */
export function Thyro({ pose, size = 96 }: { pose: ThyroPose; size?: number }) {
  return (
    <img
      src={`/mascot/thyro-${pose}.svg`}
      alt=""
      width={size}
      height={size}
      className="shrink-0 select-none"
    />
  );
}
