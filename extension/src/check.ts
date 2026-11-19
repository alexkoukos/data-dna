import { mask, scan } from "./detect/engine";
import { decideLocal, PRECEDENCE, type Policy } from "./detect/policy";
import { reasonsFor } from "./explain";
import type { CheckResult, FindingView } from "./types";

/** How long the send waits for the company server before the browser decides alone. */
export const L2_TIMEOUT_MS = 400;

export type L2Fn = (text: string) => Promise<Partial<CheckResult> | null>;

function preview(value: string): string {
  return value.length > 6
    ? `${value.slice(0, 2)}${"•".repeat(Math.max(value.length - 6, 2))}${value.slice(-4)}`
    : "•".repeat(value.length);
}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T | null> {
  return new Promise((resolve) => {
    const t = setTimeout(() => resolve(null), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        resolve(v);
      },
      () => {
        clearTimeout(t);
        resolve(null);
      },
    );
  });
}

/**
 * L1 (this browser, no network) then L2 (company server). The stricter answer wins.
 * If the server cannot be reached, the policy's fail mode decides for each category.
 */
export async function runCheck(
  text: string,
  policy: Policy,
  l2: L2Fn | null,
): Promise<CheckResult> {
  const s = scan(text, policy.clients);
  const categories = s.findings.map((f) => f.category);
  if (s.sourceCode) categories.push("source_code");
  const hiddenFinding = s.findings.some((f) => f.hidden);
  const local = decideLocal(categories, policy, { hiddenFinding });
  const findings: FindingView[] = s.findings.map((f) => ({
    entity: f.entity,
    category: f.category,
    preview: preview(f.value),
  }));
  const masked = mask(s.text, s.findings);

  let result: CheckResult = {
    action: local.action,
    reasons: reasonsFor(local.action, categories),
    findings,
    source: "l1",
    maskedText: local.action === "mask" ? masked.text : undefined,
    placeholders: local.action === "mask" ? masked.placeholders : undefined,
    policyVersion: policy.version,
  };
  if (hiddenFinding && local.action === "warn") {
    result.reasons = [
      "Your message hides a sensitive value (spaced out, encoded or invisible characters), so it cannot be masked in place.",
      "Remove the value or send anyway and say why.",
    ];
  }

  if (l2 && text.trim().length >= 8) {
    const remote = await withTimeout(l2(text), L2_TIMEOUT_MS);
    if (remote && remote.action) {
      const stricter = PRECEDENCE[remote.action] >= PRECEDENCE[result.action];
      if (stricter) {
        const remoteCategories = (remote.findings ?? []).map((f) => f.category);
        result = {
          ...result,
          ...remote,
          findings: remote.findings?.length ? remote.findings : result.findings,
          // Our own plain wording stays on top; the server's short reasons go under it.
          reasons: reasonsFor(
            remote.action,
            remote.document ? [] : remoteCategories.length ? remoteCategories : categories,
            remote.document?.title,
          ),
          why: remote.reasons,
          source: "l2",
        } as CheckResult;
      } else {
        result.source = "l2";
      }
    } else {
      result.source = "offline";
      const closed = categories.find((c) => policy.failMode[c] === "fail_closed");
      if (closed) {
        result.action = "block";
        result.reasons = [
          "The company server could not be reached, and this kind of content may not leave without a check.",
          "Try again in a moment, or ask the company AI.",
        ];
        result.maskedText = undefined;
      }
    }
  }
  return result;
}
