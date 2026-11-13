import { NavLink, Outlet } from "react-router-dom";

const tabs = [
  { to: "/security", label: "Overview", end: true },
  { to: "/security/tools", label: "AI tools", end: false },
  { to: "/security/incidents", label: "Incidents", end: false },
];

/** Shared frame for the security screens: title and section tabs. */
export default function SecurityLayout() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink-900">Security</h1>
        <nav
          aria-label="Security sections"
          className="mt-3 flex flex-wrap gap-2 border-b border-ink-200 pb-3"
        >
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className={({ isActive }) =>
                `min-h-11 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-100"}`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <div className="mt-6">
        <Outlet />
      </div>
    </main>
  );
}
