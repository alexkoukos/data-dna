/**
 * Hive buttons as plain CSS, so they work on the extension pages and inside the overlay's shadow DOM.
 * Simple on purpose: a flat fill, one border, a clear hover, a visible focus ring. Any <button> gets
 * the look with no markup change. `.primary` is Hive amber, `.danger` is red, the rest is neutral.
 */
export const TEXTURE_CSS = `
button {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 0 20px;
  border-radius: 10px; border: 1px solid var(--b-border, #d1d5db); background: var(--b-bg, #fff); color: var(--b-fg, #262626);
  font: 600 14px/20px "Poppins", system-ui, sans-serif; cursor: pointer; transition: background-color .15s ease, border-color .15s ease;
}
button:hover:not(:disabled) { background: var(--b-hover, #f3f4f6); }
button:active:not(:disabled) { background: var(--b-active, #e5e7eb); }
button:disabled { opacity: .5; cursor: default; }
button.primary { --b-bg: #f59e0b; --b-hover: #fbab1f; --b-active: #e08e06; --b-border: #d97706; --b-fg: #262626; }
button.danger { --b-bg: #dc2626; --b-hover: #c81f1f; --b-active: #b91c1c; --b-border: #b91c1c; --b-fg: #fff; }
button:focus-visible { outline: 2px solid #262626; outline-offset: 2px; }
@media (prefers-color-scheme: dark) {
  button { --b-bg: #2b2b2b; --b-hover: #353535; --b-active: #404040; --b-border: #4a4a4a; --b-fg: #fafaf9; }
  button.primary { --b-bg: #f59e0b; --b-hover: #fbab1f; --b-active: #e08e06; --b-border: #fbbf24; --b-fg: #262626; }
  button.danger { --b-bg: #dc2626; --b-hover: #ea3a3a; --b-active: #b91c1c; --b-border: #ef4444; --b-fg: #fff; }
  button:focus-visible { outline-color: #fafaf9; }
}
@media (prefers-reduced-motion: reduce) { button { transition: none; } }
`;
