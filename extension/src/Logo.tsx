/** The Sentry mark with an eye that looks around, plus the name. Both stop for reduced motion. */
export function Logo({ size = 30 }: { size?: number }) {
  return (
    <span className="logo">
      <svg
        className="logo-mark"
        width={size}
        height={Math.round((size * 74) / 64)}
        viewBox="0 0 64 74"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M32 4 L58 14 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V14 Z" fill="#f59e0b" />
        <path
          d="M32 22 C41 22 47 30 47 36 C47 42 41 50 32 50 C23 50 17 42 17 36 C17 30 23 22 32 22 Z"
          fill="none"
          stroke="#1a1000"
          strokeWidth="3.5"
        />
        <circle className="logo-eye" cx="32" cy="36" r="6" fill="#1a1000" />
      </svg>
      <span className="logo-word">Sentry</span>
    </span>
  );
}
