import { NavLink, Route, Routes } from "react-router-dom";
import { Placeholder } from "./pages/Placeholder";

const links = [
  { to: "/chat", label: "Company Chat" },
  { to: "/connect", label: "Connect a tool" },
  { to: "/security", label: "Security" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <nav
        aria-label="Main"
        className="flex flex-wrap gap-2 border-b border-ink-200 bg-white px-4 py-2"
      >
        <span className="mr-4 py-2 font-bold">Data DNA</span>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `min-h-11 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-100"}`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route path="/" element={<Placeholder title="Data DNA" note="Pick a screen above." />} />
        <Route
          path="/chat"
          element={<Placeholder title="Company Chat" note="See TASKS.md: web/chat." />}
        />
        <Route
          path="/connect"
          element={<Placeholder title="Connect a tool" note="See TASKS.md: web/connect." />}
        />
        <Route
          path="/security"
          element={<Placeholder title="Security overview" note="See TASKS.md: web/security." />}
        />
      </Routes>
    </div>
  );
}
