import { NavLink, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import AskPage from "./pages/security/AskPage";
import DocumentsPage from "./pages/security/DocumentsPage";

import ConnectPage from "./pages/ConnectPage";
import IncidentDetailPage from "./pages/security/IncidentDetailPage";
import IncidentsPage from "./pages/security/IncidentsPage";
import OverviewPage from "./pages/security/OverviewPage";
import PoliciesPage from "./pages/security/PoliciesPage";
import SecurityLayout from "./pages/security/SecurityLayout";
import ToolsPage from "./pages/security/ToolsPage";
import { Placeholder } from "./pages/Placeholder";
import { Companion } from "./components/Companion";

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
        <img src="/pyli-logo.svg" alt="Pyli" className="mr-4 h-8 self-center" />
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
        <Route
          path="/"
          element={
            <Placeholder title="Every prompt passes the gate." note="Pick a screen above." />
          }
        />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/security" element={<SecurityLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="policies" element={<PoliciesPage />} />
          <Route path="ask" element={<AskPage />} />
        </Route>
      </Routes>
      <Companion />
    </div>
  );
}
