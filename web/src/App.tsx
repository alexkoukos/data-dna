import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { GlassNav } from "./components/GlassNav";
import BreakItPage from "./pages/BreakItPage";
import HomePage from "./pages/HomePage";
import ExtensionPage from "./pages/ExtensionPage";
import AskPage from "./pages/security/AskPage";
import DocumentsPage from "./pages/security/DocumentsPage";
import GroupsPage from "./pages/security/GroupsPage";
import HistoryPage from "./pages/security/HistoryPage";
import ImpactPage from "./pages/security/ImpactPage";

import ChatPage from "./pages/ChatPage";
import ConnectPage from "./pages/ConnectPage";
import IncidentDetailPage from "./pages/security/IncidentDetailPage";
import IncidentsPage from "./pages/security/IncidentsPage";
import OverviewPage from "./pages/security/OverviewPage";
import PoliciesPage from "./pages/security/PoliciesPage";
import SecurityLayout from "./pages/security/SecurityLayout";
import ToolsPage from "./pages/security/ToolsPage";

const Landing = lazy(() => import("./landing/Landing"));
const DeepDive = lazy(() => import("./landing/DeepDive"));
const Trust = lazy(() => import("./landing/Trust"));
const Developers = lazy(() => import("./landing/Developers"));

const SITE_PAGES: Record<string, React.LazyExoticComponent<() => React.JSX.Element>> = {
  "/": Landing,
  "/how-it-works": DeepDive,
  "/trust": Trust,
  "/developers": Developers,
};

export default function App() {
  const { pathname } = useLocation();
  // The public site has its own header and footer, and no app chrome.
  const Page = SITE_PAGES[pathname];
  if (Page) {
    return (
      <Suspense fallback={null}>
        <Page />
      </Suspense>
    );
  }
  return (
    <div className="min-h-screen">
      <GlassNav />
      <Routes>
        <Route path="/app" element={<HomePage />} />
        <Route path="/extension" element={<ExtensionPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/chat" element={<ChatPage />} />
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
