// Pure helpers, loaded as a plain script by the page script and the popup, and by `node --test`.
(function (root) {
  // Same limit as the brain (MAX_INSPECT_CHARS): longer text is not sent, it is refused here.
  const MAX_CHARS = 100000;

  /**
   * What to do when the gate did not give a verdict.
   * "open": nothing could be checked (offline, no key, gate down): let it through with a badge.
   * "badge": the key is not accepted: let it through with a badge that says what to do.
   * "block": the gate refused to read it (too long, malformed) or failed in another way:
   * nothing goes out unchecked.
   */
  function failMode(status) {
    if ([0, 429, 502, 503, 504].includes(status)) return "open";
    if (status === 401) return "badge";
    return "block";
  }

  function failReasons(status) {
    if (status === 413 || status === 422)
      return ["Too long: shorten it or use Company AI"];
    return ["Sentry could not check this. Try again, or use Company AI."];
  }

  /** A link is only followed when it is http or https. */
  function safeHref(url) {
    try {
      const u = new URL(String(url));
      return u.protocol === "https:" || u.protocol === "http:" ? u.href : "#";
    } catch {
      return "#";
    }
  }

  const api = { MAX_CHARS, failMode, failReasons, safeHref };
  root.SentryLogic = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
