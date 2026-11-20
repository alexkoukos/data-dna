import { useEffect, useState } from "react";

export type GateHealth = "checking" | "online" | "degraded" | "offline";

const RECHECK_MS = 30_000;

/** Asks the brain whether it runs and can reach its database. Any failure, including a reply that
 * is not the brain's JSON (a dev server without the API), counts as offline. */
export async function fetchGateHealth(signal?: AbortSignal): Promise<GateHealth> {
  try {
    const res = await fetch("/api/healthz", { signal, headers: { Accept: "application/json" } });
    if (!res.ok) return "offline";
    const body = (await res.json()) as { status?: string; database?: string };
    if (body.status !== "ok") return "offline";
    return body.database === "unreachable" ? "degraded" : "online";
  } catch {
    return "offline";
  }
}

/** Checks gate health on mount and every 30 seconds, so the footer recovers on its own when the
 * stack comes back during a demo. */
export function useGateHealth(): GateHealth {
  const [status, setStatus] = useState<GateHealth>("checking");
  useEffect(() => {
    const ctrl = new AbortController();
    const check = () =>
      fetchGateHealth(ctrl.signal).then((s) => {
        if (!ctrl.signal.aborted) setStatus(s);
      });
    void check();
    const timer = window.setInterval(check, RECHECK_MS);
    return () => {
      ctrl.abort();
      window.clearInterval(timer);
    };
  }, []);
  return status;
}
