import type { ReactNode } from "react";

/** Small stroke icons. Decorative: always paired with text, so hidden from screen readers. */
function Svg({ children }: { children: ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export const CheckIcon = () => (
  <Svg>
    <path d="M20 6 9 17l-5-5" />
  </Svg>
);
export const EyeOffIcon = () => (
  <Svg>
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22" />
  </Svg>
);
export const HomeIcon = () => (
  <Svg>
    <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
    <path d="M9 21V12h6v9" />
  </Svg>
);
export const AlertIcon = () => (
  <Svg>
    <path d="m10.29 3.86-8.18 14.14A2 2 0 0 0 3.82 21h16.36a2 2 0 0 0 1.71-3l-8.18-14.14a2 2 0 0 0-3.42 0z" />
    <path d="M12 9v4M12 17h.01" />
  </Svg>
);
export const BanIcon = () => (
  <Svg>
    <circle cx="12" cy="12" r="10" />
    <path d="m4.9 4.9 14.2 14.2" />
  </Svg>
);
