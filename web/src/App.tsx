import { lazy, Suspense } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import BreakItPage from "./pages/BreakItPage";
import HomePage from "./pages/HomePage";
import ChatPage from "./pages/ChatPage";
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
import ReviewPage from "./pages/security/ReviewPage";
import DigestPage from "./pages/security/DigestPage";
import SecurityLayout from "./pages/security/SecurityLayout";
import ToolsPage from "./pages/security/ToolsPage";
import { Companion } from "./components/Companion";
import { AppFooter } from "./components/AppFooter";
import { useGateHealth } from "./lib/healthApi";
import NotFoundPage from "./pages/NotFoundPage";

const Landing = lazy(() => import("./landing/Landing"));

const links = [
  { to: "/chat", label: "Company Chat" },
  { to: "/break-it", label: "Try to break it" },
  { to: "/security", label: "Security" },
  { to: "/connect", label: "Connect a tool" },
];

export default function App() {
  const { pathname } = useLocation();
  // The landing page has its own header and no app chrome.
  if (pathname === "/") {
    return (
      <Suspense fallback={null}>
        <Landing />
      </Suspense>
    );
  }
  return <AppShell />;
}

/** Nav, the current screen, and a footer that sits at the bottom even on short screens. */
function AppShell() {
  const health = useGateHealth();
  return (
    <div className="flex min-h-screen flex-col">
      <nav
        aria-label="Main"
        className="flex flex-wrap gap-2 border-b border-ink-200 bg-white px-4 py-2"
      >
        <Link
          to="/app"
          aria-label="Pyli home"
          className="mr-4 flex min-h-11 min-w-11 items-center self-center"
        >
          <img src="/pyli-logo.svg" alt="Pyli" className="h-8" />
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
      <div className="flex-1">
        <Routes>
          <Route path="/app" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
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
            <Route path="review" element={<ReviewPage />} />
            <Route path="digest" element={<DigestPage />} />
            <Route path="ask" element={<AskPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
      <AppFooter status={health} />
      <Companion />
    </div>
  );
}
