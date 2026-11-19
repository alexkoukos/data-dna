/**
 * Sentry buttons as plain CSS, so they work on the extension pages and inside the overlay's shadow DOM.
 * Simple on purpose: a flat fill, one border, a clear hover, a visible focus ring. Any <button> gets
 * the look with no markup change. `.primary` is Sentry amber, `.danger` is red, the rest is neutral.
 */
export const TEXTURE_CSS = `
button {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 0 20px;
  border-radius: 10px; border: 1px solid var(--b-border, #332d26); background: var(--b-bg, #1f1b16); color: var(--b-fg, #f5f1ea);
  font: 600 14px/20px "Poppins", system-ui, sans-serif; cursor: pointer; transition: background-color .15s ease, border-color .15s ease;
}
button:hover:not(:disabled) { background: var(--b-hover, #2a251e); }
button:active:not(:disabled) { background: var(--b-active, #14110e); }
button:disabled { opacity: .5; cursor: default; }
button.primary { --b-bg: #f59e0b; --b-hover: #fbbf24; --b-active: #e9a516; --b-border: #fbbf24; --b-fg: #1a1000; }
button.danger { --b-bg: #c2272d; --b-hover: #d63339; --b-active: #a31f25; --b-border: #ef5b5b; --b-fg: #fff; }
button:focus-visible { outline: 2px solid #fbbf24; outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { button { transition: none; } }
`;
