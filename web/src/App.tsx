import { Link, NavLink, Route, Routes } from "react-router-dom";
import BreakItPage from "./pages/BreakItPage";
import HomePage from "./pages/HomePage";
import ExtensionPage from "./pages/ExtensionPage";
import AskPage from "./pages/security/AskPage";
import DocumentsPage from "./pages/security/DocumentsPage";
import GroupsPage from "./pages/security/GroupsPage";
import HistoryPage from "./pages/security/HistoryPage";
import ImpactPage from "./pages/security/ImpactPage";

import ConnectPage from "./pages/ConnectPage";
import IncidentDetailPage from "./pages/security/IncidentDetailPage";
import IncidentsPage from "./pages/security/IncidentsPage";
import OverviewPage from "./pages/security/OverviewPage";
import PoliciesPage from "./pages/security/PoliciesPage";
import SecurityLayout from "./pages/security/SecurityLayout";
import ToolsPage from "./pages/security/ToolsPage";

const links = [
  { to: "/extension", label: "Get the extension" },
  { to: "/break-it", label: "Try to break it" },
  { to: "/security", label: "Security" },
  { to: "/connect", label: "Connect a tool" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <nav
        aria-label="Main"
        className="flex flex-wrap gap-2 border-b border-ink-200 bg-white px-4 py-2"
      >
        <Link
          to="/"
          aria-label="Hive home"
          className="mr-4 flex min-h-11 min-w-11 items-center self-center"
        >
          <img src="/brand/hive-wordmark.svg" alt="Hive" className="h-8" />
        </Link>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `min-h-11 rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-100"}`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/extension" element={<ExtensionPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/break-it" element={<BreakItPage />} />
        <Route path="/security" element={<SecurityLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="policies" element={<PoliciesPage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="impact" element={<ImpactPage />} />
          <Route path="ask" element={<AskPage />} />
        </Route>
      </Routes>
    </div>
  );
}
