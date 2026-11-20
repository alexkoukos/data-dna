import { lazy, Suspense } from "react";
import { SiteFooter } from "./landing/SiteFooter";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { SiteNav } from "./landing/SiteNav";
import { useScrollOnNavigate } from "./landing/useScrollOnNavigate";
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
import ReviewPage from "./pages/security/ReviewPage";
import DigestPage from "./pages/security/DigestPage";
import SecurityLayout from "./pages/security/SecurityLayout";
import ToolsPage from "./pages/security/ToolsPage";

const Landing = lazy(() => import("./landing/Landing"));
const LandingV2 = lazy(() => import("./landing/LandingV2"));
const DeepDive = lazy(() => import("./landing/DeepDive"));

const SITE_PAGES: Record<string, React.LazyExoticComponent<() => React.JSX.Element>> = {
  "/": Landing,
  "/v2": LandingV2,
  "/how-it-works": DeepDive,
};

const NotFound = lazy(() => import("./landing/NotFound"));

/** An unknown address inside the app: the same page, with the nav above it already shown. */
function NotFoundInApp() {
  return (
    <div className="sentry dark">
      <Suspense fallback={null}>
        <NotFound />
      </Suspense>
    </div>
  );
}

export default function App() {
  const { pathname } = useLocation();
  useScrollOnNavigate();
  // The public site has its own header and footer, and no app chrome.
  const Page = SITE_PAGES[pathname];
  // The Security page became a section of How it works.
  if (pathname === "/trust") return <Navigate to="/how-it-works#security" replace />;
  if (pathname === "/developers") return <Navigate to="/how-it-works#developers" replace />;
  if (Page) {
    return (
      <Suspense fallback={null}>
        <Page />
      </Suspense>
    );
  }
  return (
    <div className="flex min-h-screen flex-col *:min-w-0">
      <div className="sentry nav-shell">
        <SiteNav />
      </div>
      <Routes>
        <Route path="/app" element={<HomePage />} />
        <Route path="/extension" element={<ExtensionPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/break-it" element={<BreakItPage />} />
        <Route path="*" element={<NotFoundInApp />} />
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
      </Routes>
      <div className="sentry dark foot-shell mt-auto">
        <SiteFooter />
      </div>
    </div>
  );
}
