import { useCallback, useEffect, useState } from "react";

export type Remote<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

/** Loads once on mount and again when `reload` is called. Components that need a fresh load for a
 * new input should be given a new `key`, so they start from the loading state. */
export function useFetch<T>(load: () => Promise<T>): [Remote<T>, () => void] {
  const [state, setState] = useState<Remote<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load().then(
      (data) => !cancelled && setState({ status: "ready", data }),
      () => !cancelled && setState({ status: "error" }),
    );
    return () => {
      cancelled = true;
    };
    // `load` is a stable module function in every caller; `attempt` re-runs it on retry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  const reload = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);
  return [state, reload];
}
