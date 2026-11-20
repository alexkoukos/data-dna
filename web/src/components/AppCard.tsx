import { Link } from "react-router-dom";

interface Props {
  to: string;
  name: string;
  text: string;
  points: string[];
  cta: string;
}

/**
 * Presentational: one card on the app home. The title is the only link and covers the whole card,
 * so the card is one large target with one name; the pill at the foot only looks like a button.
 */
export function AppCard({ to, name, text, points, cta }: Props) {
  return (
    <div className="app-card h-full">
      <div className="app-card__body">
        <div>
          <h3 className="text-base font-semibold text-ink-900">
            <Link
              to={to}
              className="outline-none after:absolute after:inset-0 after:rounded-2xl after:content-[''] focus-visible:after:outline-2 focus-visible:after:outline-offset-[-3px] focus-visible:after:outline-brand-600"
            >
              {name}
            </Link>
          </h3>
          <p className="mt-1 text-sm text-ink-600">{text}</p>
        </div>
        <hr className="h-px border-0 bg-ink-300" />
        <ul className="flex flex-1 flex-col gap-2">
          {points.map((p) => (
            <li key={p} className="flex items-center gap-2 text-sm text-ink-900">
              <span className="grid size-4 shrink-0 place-items-center rounded-full bg-brand-600">
                <svg
                  className="size-3 text-[#1a1000]"
                  fill="currentColor"
                  viewBox="0 0 16 16"
                  aria-hidden="true"
                >
                  <path
                    clipRule="evenodd"
                    fillRule="evenodd"
                    d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
                  />
                </svg>
              </span>
              {p}
            </li>
          ))}
        </ul>
        <span
          aria-hidden="true"
          className="app-card__button flex min-h-11 items-center justify-center px-4 text-sm font-semibold"
        >
          {cta}
        </span>
      </div>
    </div>
  );
}
