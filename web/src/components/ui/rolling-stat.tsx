import { useEffect, useState } from "react";

import { RollingNumber } from "@/components/ui/rolling-number";

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () =>
      typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/**
 * A number that rolls to its value, for what Hive is saving. Screen readers get the final value
 * once (the rolling digits are hidden from them), and with reduced motion it just shows the number.
 */
export function RollingStat({
  value,
  suffix = "",
  className,
}: {
  value: number;
  suffix?: string;
  className?: string;
}) {
  const reduced = usePrefersReducedMotion();
  const text = `${value.toLocaleString()}${suffix}`;
  if (reduced) return <span className={className}>{text}</span>;
  return (
    <span className={className}>
      <span aria-hidden="true">
        <RollingNumber value={value} />
        {suffix}
      </span>
      <span className="sr-only">{text}</span>
    </span>
  );
}
