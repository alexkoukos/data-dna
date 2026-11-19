/**
 * A looping demonstration of the extension, in plain HTML and CSS: someone types a message with an
 * IBAN in an AI chat, the card appears, the AI receives the safe version. With reduced motion it
 * shows the finished state.
 */
export function ExtensionDemo() {
  return (
    <div
      className="xd"
      role="img"
      aria-label="Demonstration: a message with an IBAN is typed into an AI chat. Sentry's card says one item was masked, and the AI receives [IBAN_1] instead."
    >
      <div className="xd-bar" aria-hidden="true">
        <span className="xd-dots">
          <i />
          <i />
          <i />
        </span>
        <span className="xd-url">claude.ai</span>
        <span className="xd-ext">
          <svg viewBox="0 0 64 74" width="16" height="18">
            <path d="M32 4 L58 14 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V14 Z" fill="#f59e0b" />
            <circle cx="32" cy="36" r="7" fill="#1a1000" />
          </svg>
        </span>
      </div>
      <div className="xd-body" aria-hidden="true">
        <div className="xd-sent">
          <span className="xd-bubble">
            Please wire 12,400 EUR to <mark>[IBAN_1]</mark> for <mark>[PERSON_1]</mark>
          </span>
        </div>
        <div className="xd-card">
          <svg viewBox="0 0 64 74" width="22" height="25">
            <path d="M32 4 L58 14 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V14 Z" fill="#f59e0b" />
            <circle cx="32" cy="36" r="7" fill="#1a1000" />
          </svg>
          <span>2 items masked before sending. Real values come back in the answer.</span>
        </div>
        <div className="xd-composer">
          <span className="xd-typed">
            <span className="xd-t1">
              Please wire 12,400 EUR to GR1601101250000000012300695 for Maria Papadopoulou
            </span>
          </span>
          <span className="xd-send">Send</span>
        </div>
      </div>
    </div>
  );
}
