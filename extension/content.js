// Hive on chatgpt.com and claude.ai: check paste and send in the composer, and every file attached
// (picker, drag and drop, paste), before it leaves the page.
// Fails open: if the gate cannot be reached nothing is blocked, and a small badge says so.
(() => {
  const COMPOSER = '#prompt-textarea, div.ProseMirror[contenteditable="true"]';
  const SEND =
    '[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label="Send message"]';
  const COMPANY_AI = "Company AI";
  let passing = false; // set while we re-send a message we already checked
  let busy = false;

  const composer = () => document.querySelector(COMPOSER);
  const isField = (el) => el && el.tagName === "TEXTAREA";
  const textOf = (el) =>
    isField(el) ? el.value : el.innerText.replace(/\n$/, "");

  function setText(el, text) {
    el.focus();
    if (isField(el)) {
      Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value",
      ).set.call(el, text);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    if (!document.execCommand("insertText", false, text)) {
      el.textContent = text;
      el.dispatchEvent(new InputEvent("input", { bubbles: true }));
    }
  }

  function insertText(el, text) {
    el.focus();
    if (isField(el)) {
      el.setRangeText(text, el.selectionStart, el.selectionEnd, "end");
      el.dispatchEvent(new Event("input", { bubbles: true }));
    } else if (!document.execCommand("insertText", false, text)) {
      el.textContent += text;
      el.dispatchEvent(new InputEvent("input", { bubbles: true }));
    }
  }

  function send() {
    const btn = document.querySelector(SEND);
    passing = true;
    try {
      if (btn) btn.click();
      else composer()?.closest("form")?.requestSubmit();
    } finally {
      setTimeout(() => (passing = false), 0);
    }
  }

  function ask(message) {
    return chrome.runtime
      .sendMessage(message)
      .catch(() => ({ ok: false, error: "offline" }));
  }

  // ---- the card -------------------------------------------------------------------------
  const STYLE = `
    :host { all: initial; }
    .card { box-sizing: border-box; width: 100%; display: flex; gap: 12px; align-items: flex-start;
      flex-wrap: wrap; padding: 12px; border: 1px solid var(--pyli-border, #e5e7eb);
      border-left: 4px solid var(--accent); border-radius: 12px; background: var(--pyli-tint, #fffbeb);
      color: var(--pyli-text, #262626); font: 14px/1.45 var(--pyli-font, system-ui, sans-serif);
      overflow-wrap: anywhere; }
    .card.mask { --accent: var(--pyli-mask, #1d4ed8); }
    .card.warn { --accent: var(--pyli-warn, #b45309); }
    .card.block { --accent: var(--pyli-block, #b91c1c); }
    .card.local { --accent: var(--pyli-local, #0f766e); }
    img { width: 44px; height: auto; flex: none; }
    .body { flex: 1 1 200px; min-width: 0; }
    .title { font-weight: 600; margin: 0 0 2px; }
    p { margin: 0 0 6px; }
    details { margin: 4px 0 8px; }
    summary { cursor: pointer; min-height: 24px; }
    ul { margin: 4px 0 0; padding-left: 18px; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    button, a.btn { box-sizing: border-box; min-height: 44px; min-width: 44px; padding: 0 14px;
      display: inline-flex; align-items: center; justify-content: center; border-radius: 8px;
      font: inherit; font-weight: 600; cursor: pointer; text-decoration: none;
      border: 1px solid var(--pyli-border, #e5e7eb); background: var(--pyli-bg, #fff);
      color: var(--pyli-text, #262626); }
    .primary { background: var(--pyli-primary, #f59e0b); border-color: var(--pyli-primary, #f59e0b);
      color: var(--pyli-on-primary, #262626); }
    :is(button, a, summary):focus-visible { outline: 3px solid var(--pyli-focus, #b45309);
      outline-offset: 2px; }
    .badge { display: inline-flex; align-items: center; gap: 6px; min-height: 28px; padding: 2px 10px;
      border-radius: 999px; background: var(--pyli-muted, #f3f4f6); border: 1px solid var(--pyli-border, #e5e7eb);
      color: var(--pyli-text, #262626); font: 13px var(--pyli-font, system-ui, sans-serif); }
    .badge img { width: 22px; height: auto; }
    @media (max-width: 480px) { .row > * { flex: 1 1 100%; } }
  `;

  let host = null;
  function ensureHost() {
    const field = composer();
    if (!host) {
      host = document.createElement("pyli-host");
      host.attachShadow({ mode: "open" });
    }
    if (!field) {
      // Sites whose composer we do not know (claude.ai): float the card above the page.
      host.style.cssText =
        "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);width:min(560px,92vw);z-index:2147483647";
      if (!host.isConnected) document.body.append(host);
      return host.shadowRoot;
    }
    host.style.cssText = "";
    const anchor = field.closest("form") || field.parentElement;
    if (
      host.parentElement !== anchor.parentElement ||
      host.previousElementSibling !== anchor
    ) {
      anchor.insertAdjacentElement("afterend", host);
    }
    return host.shadowRoot;
  }

  function h(tag, attrs = {}, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    for (const kid of kids) el.append(kid);
    return el;
  }

  // The Hive guard bee. The state is carried by the card colour and the words, not by the picture.
  function mascot() {
    return h("img", {
      src: chrome.runtime.getURL("brand/hive-guard-bee.svg"),
      alt: "",
      "aria-hidden": "true",
    });
  }

  function show(kind, title, lines, reasons, buttons = []) {
    const root = ensureHost();
    if (!root) return;
    const body = h("div", { class: "body" }, h("p", { class: "title" }, title));
    for (const line of lines) body.append(h("p", {}, line));
    if (reasons && reasons.length) {
      const list = h("ul");
      for (const r of reasons) list.append(h("li", {}, r));
      body.append(h("details", {}, h("summary", {}, "Why?"), list));
    }
    if (buttons.length) body.append(h("div", { class: "row" }, ...buttons));
    const card = h(
      "div",
      { class: `card ${kind}`, role: kind === "block" ? "alert" : "status" },
      mascot(),
      body,
    );
    root.replaceChildren(h("style", {}, STYLE), card);
  }

  function showBadge(text) {
    const root = ensureHost();
    if (!root) return;
    root.replaceChildren(
      h("style", {}, STYLE),
      h("span", { class: "badge", role: "status" }, mascot(), text),
    );
  }

  function clear() {
    host?.shadowRoot?.replaceChildren();
  }

  function button(label, onClick, primary = false) {
    const b = h(
      "button",
      { type: "button", class: primary ? "primary" : "" },
      label,
    );
    b.addEventListener("click", onClick);
    return b;
  }

  function companyAiLink(url) {
    const a = h(
      "a",
      {
        class: "btn primary",
        href: url || "#",
        target: "_blank",
        rel: "noopener noreferrer",
      },
      `Use ${COMPANY_AI}`,
    );
    return a;
  }

  // ---- the decision ---------------------------------------------------------------------
  /** Ask the gate. Returns the verdict, or null when it should fail open. */
  async function check(text, attachments = []) {
    const out = await ask({ type: "inspect", text, attachments, site: location.hostname });
    if (out.ok) {
      clear();
      const v = out.body;
      // Shadow mode: record only. Never change or stop anything.
      return v.shadow ? { ...v, decision: "allow" } : v;
    }
    if (out.error === "no-key")
      showBadge("Hive: add your key in the extension options");
    else if (out.status === 401)
      showBadge("Hive: key not accepted, copy it again from Connect");
    else showBadge("Hive offline");
    return null;
  }

  function maskedNote(v) {
    const types = v.entity_types.length
      ? v.entity_types.join(", ")
      : "sensitive data";
    show(
      "mask",
      "Masked before sending",
      [`Replaced: ${types}. Check the text, then send.`],
      v.reasons,
    );
  }

  function blockCard(v) {
    const local = v.decision === "local";
    show(
      "block",
      "Not sent",
      [
        local
          ? "This is confidential and must stay inside the company."
          : "This message contains protected data.",
        `Use ${v.alternative || COMPANY_AI} instead.`,
      ],
      v.reasons,
      [companyAiLink(v.alternative_url)],
    );
  }

  function warnCard(v, onSend) {
    show(
      "warn",
      "Check before sending",
      ["This may contain sensitive data."],
      v.reasons,
      [
        button("Edit message", clear, true),
        button("Send anyway", async () => {
          await ask({ type: "ack", reason: "sent anyway from the browser" });
          clear();
          onSend();
        }),
      ],
    );
  }

  // ---- paste ----------------------------------------------------------------------------
  document.addEventListener(
    "paste",
    async (e) => {
      const field = composer();
      if (!field || !field.contains(e.target) || passing) return;
      const text = e.clipboardData?.getData("text/plain");
      if (!text) return; // images and files are not checked here
      e.preventDefault();
      e.stopImmediatePropagation();
      const v = await check(text);
      if (!v || v.decision === "allow") return insertText(field, text);
      if (v.decision === "mask" && v.masked_text) {
        insertText(field, v.masked_text);
        return maskedNote(v);
      }
      if (v.decision === "warn") {
        insertText(field, text);
        return show(
          "warn",
          "Check before sending",
          [
            "This may contain sensitive data. You will be asked again when you send.",
          ],
          v.reasons,
        );
      }
      blockCard(v); // block and local: the text is not pasted
    },
    true,
  );

  // ---- files ----------------------------------------------------------------------------
  const READABLE = /\.(pdf|docx|txt|md|csv|json|log|png|jpe?g)$/i;
  const MAX_BYTES = 10 * 1024 * 1024;

  async function toAttachment(file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000)
      bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return { filename: file.name, content_base64: btoa(bin) };
  }

  /** Check files before the page sees them. Calls release() to let them through, drop() when not. */
  async function guardFiles(files, release, drop) {
    const list = files.filter((f) => READABLE.test(f.name) && f.size <= MAX_BYTES);
    if (!list.length) return release();
    const v = await check("", await Promise.all(list.map(toAttachment)));
    if (!v || v.decision === "allow") return release();
    if (v.decision === "warn" || v.decision === "mask") {
      return show(
        "warn",
        "Check before attaching",
        ["This file may contain sensitive data."],
        v.reasons,
        [
          button("Remove file", () => {
            clear();
            drop();
          }, true),
          button("Attach anyway", async () => {
            await ask({ type: "ack", reason: "attached anyway from the browser" });
            clear();
            release();
          }),
        ],
      );
    }
    drop();
    show(
      "block",
      "File not attached",
      [
        "This file is confidential and must stay inside the company.",
        `Use ${v.alternative || COMPANY_AI} instead.`,
      ],
      v.reasons,
      [companyAiLink(v.alternative_url)],
    );
  }

  function transfer(files) {
    const dt = new DataTransfer();
    for (const f of files) dt.items.add(f);
    return dt;
  }

  // File picker. The files are held back until the gate has answered.
  document.addEventListener(
    "change",
    (e) => {
      const input = e.target;
      if (passing || !(input instanceof HTMLInputElement) || input.type !== "file") return;
      const files = [...(input.files || [])];
      if (!files.length) return;
      e.stopImmediatePropagation();
      guardFiles(
        files,
        () => {
          passing = true;
          try {
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } finally {
            passing = false;
          }
        },
        () => {
          input.value = "";
        },
      );
    },
    true,
  );

  // Drag and drop.
  document.addEventListener(
    "drop",
    (e) => {
      const files = [...(e.dataTransfer?.files || [])];
      if (passing || !files.length) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      const target = e.target;
      guardFiles(
        files,
        () => {
          passing = true;
          try {
            target.dispatchEvent(
              new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: transfer(files) }),
            );
          } finally {
            passing = false;
          }
        },
        () => {},
      );
    },
    true,
  );

  // Paste of a file (a copied PDF). Text paste is handled above.
  document.addEventListener(
    "paste",
    (e) => {
      const files = [...(e.clipboardData?.files || [])];
      if (passing || !files.length || e.clipboardData?.getData("text/plain")) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      const target = e.target;
      guardFiles(
        files,
        () => {
          passing = true;
          try {
            target.dispatchEvent(
              new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: transfer(files) }),
            );
          } finally {
            passing = false;
          }
        },
        () => {},
      );
    },
    true,
  );

  // ---- send -----------------------------------------------------------------------------
  async function onSend() {
    const field = composer();
    if (!field || busy) return;
    busy = true;
    try {
      const text = textOf(field);
      const v = await check(text);
      if (!v || v.decision === "allow") return send();
      if (v.decision === "mask" && v.masked_text) {
        setText(field, v.masked_text);
        return maskedNote(v);
      }
      if (v.decision === "warn") return warnCard(v, send);
      blockCard(v);
    } finally {
      busy = false;
    }
  }

  function intercept(e) {
    const field = composer();
    if (passing || !field || !textOf(field).trim()) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    onSend();
  }

  document.addEventListener(
    "keydown",
    (e) => {
      const field = composer();
      if (
        e.key !== "Enter" ||
        e.shiftKey ||
        e.isComposing ||
        !field ||
        !field.contains(e.target)
      )
        return;
      intercept(e);
    },
    true,
  );

  document.addEventListener(
    "click",
    (e) => {
      if (e.target instanceof Element && e.target.closest(SEND)) intercept(e);
    },
    true,
  );
})();
