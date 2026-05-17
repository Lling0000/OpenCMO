import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Navigate, Routes, Route, useLocation } from "react-router";
import { AppShell } from "./components/layout/AppShell";
import { FloatingContactQR } from "./components/FloatingContactQR";
import { PublicLocaleSync } from "./components/marketing/PublicLocaleSync";
import { isPublicRoutePath } from "./utils/publicRoutes";
import { LandingPage } from "./pages/LandingPage";
import { PublicServicePage, type PublicServicePageKind } from "./pages/PublicServicePage";
import { ServicesPage } from "./pages/ServicesPage";
import { HostedWaitlistPage } from "./pages/HostedWaitlistPage";
import { SignupPage } from "./pages/SignupPage";
import { LoginPage } from "./pages/LoginPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { AdminPage } from "./pages/AdminPage";
import { BlogPage } from "./pages/BlogPage";
import { BlogArticlePage } from "./pages/BlogArticlePage";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectPage } from "./pages/ProjectPage";
import { SampleAuditPage } from "./pages/SampleAuditPage";
import { SeoPage } from "./pages/SeoPage";
import { GeoPage } from "./pages/GeoPage";
import { SerpPage } from "./pages/SerpPage";
import { CommunityPage } from "./pages/CommunityPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { BrandKitPage } from "./pages/BrandKitPage";
import { ProjectMonitorsPage } from "./pages/ProjectMonitorsPage";
import { GitHubLeadsPage } from "./pages/GitHubLeadsPage";
import { ContentPage } from "./pages/ContentPage";
import { useAuth } from "./components/auth/useAuth";

// Heavy pages lazy-loaded: Three.js graph, react-markdown reports/chat, recharts performance
const GraphPage = lazy(() =>
  import("./pages/GraphPage").then((m) => ({ default: m.GraphPage }))
);
const ReportsPage = lazy(() =>
  import("./pages/ReportsPage").then((m) => ({ default: m.ReportsPage }))
);
const ChatPage = lazy(() =>
  import("./pages/ChatPage").then((m) => ({ default: m.ChatPage }))
);
const PerformancePage = lazy(() =>
  import("./pages/PerformancePage").then((m) => ({
    default: m.PerformancePage,
  }))
);

function LazyFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
    </div>
  );
}

function LocalizedPublicPage({
  locale,
  children,
}: {
  locale: "en" | "zh";
  children: ReactNode;
}) {
  return (
    <PublicLocaleSync locale={locale}>
      {children}
    </PublicLocaleSync>
  );
}

function LegacyWorkspaceRedirect() {
  const location = useLocation();
  return <Navigate to={`/console${location.search}${location.hash}`} replace />;
}

function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-950" />
    </div>
  );
}

function RequireAuth({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.isLoading) return <AuthLoading />;
  if (!auth.isAuthenticated) {
    const params = new URLSearchParams();
    const url = new URLSearchParams(location.search).get("url");
    if (url) params.set("url", url);
    params.set("next", `${location.pathname}${location.search}`);
    return <Navigate to={`/signup?${params.toString()}`} replace />;
  }
  if (adminOnly && !auth.isAdmin) {
    return <Navigate to="/console" replace />;
  }
  return children;
}

function PublicFloatingWidgets() {
  const location = useLocation();
  if (!isPublicRoutePath(location.pathname)) return null;
  return <FloatingContactQR />;
}

function AppRoutes() {
  const localizedService = (locale: "en" | "zh", kind: PublicServicePageKind) => (
    <LocalizedPublicPage locale={locale}>
      <PublicServicePage kind={kind} />
    </LocalizedPublicPage>
  );

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/en" element={<LocalizedPublicPage locale="en"><LandingPage /></LocalizedPublicPage>} />
      <Route path="/zh" element={<LocalizedPublicPage locale="zh"><LandingPage /></LocalizedPublicPage>} />
      <Route path="/services" element={<ServicesPage />} />
      <Route path="/en/services" element={<LocalizedPublicPage locale="en"><ServicesPage /></LocalizedPublicPage>} />
      <Route path="/zh/services" element={<LocalizedPublicPage locale="zh"><ServicesPage /></LocalizedPublicPage>} />
      <Route path="/hosted" element={<HostedWaitlistPage />} />
      <Route path="/en/hosted" element={<LocalizedPublicPage locale="en"><HostedWaitlistPage /></LocalizedPublicPage>} />
      <Route path="/zh/hosted" element={<LocalizedPublicPage locale="zh"><HostedWaitlistPage /></LocalizedPublicPage>} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/open-source" element={<PublicServicePage kind="open-source" />} />
      <Route path="/en/open-source" element={localizedService("en", "open-source")} />
      <Route path="/zh/open-source" element={localizedService("zh", "open-source")} />
      <Route path="/contact" element={<PublicServicePage kind="contact" />} />
      <Route path="/en/contact" element={localizedService("en", "contact")} />
      <Route path="/zh/contact" element={localizedService("zh", "contact")} />
      <Route path="/sample-audit" element={<SampleAuditPage />} />
      <Route path="/en/sample-audit" element={<LocalizedPublicPage locale="en"><SampleAuditPage /></LocalizedPublicPage>} />
      <Route path="/zh/sample-audit" element={<LocalizedPublicPage locale="zh"><SampleAuditPage /></LocalizedPublicPage>} />
      <Route path="/blog" element={<BlogPage />} />
      <Route path="/en/blog" element={<LocalizedPublicPage locale="en"><BlogPage /></LocalizedPublicPage>} />
      <Route path="/zh/blog" element={<LocalizedPublicPage locale="zh"><BlogPage /></LocalizedPublicPage>} />
      <Route path="/blog/:slug" element={<BlogArticlePage />} />
      <Route path="/en/blog/:slug" element={<LocalizedPublicPage locale="en"><BlogArticlePage /></LocalizedPublicPage>} />
      <Route path="/zh/blog/:slug" element={<LocalizedPublicPage locale="zh"><BlogArticlePage /></LocalizedPublicPage>} />
      <Route
        path="*"
        element={(
          <RequireAuth>
            <AppShell>
              <Suspense fallback={<LazyFallback />}>
                <Routes>
                  <Route path="/console" element={<DashboardPage />} />
                  <Route path="/admin" element={<RequireAuth adminOnly><AdminPage /></RequireAuth>} />
                  <Route path="/workspace" element={<LegacyWorkspaceRedirect />} />
                  <Route path="/approvals" element={<ApprovalsPage />} />
                  <Route path="/projects/:id" element={<ProjectPage />} />
                  <Route path="/projects/:id/reports" element={<ReportsPage />} />
                  <Route path="/projects/:id/content" element={<ContentPage />} />
                  <Route path="/projects/:id/brand-kit" element={<BrandKitPage />} />
                  <Route
                    path="/projects/:id/performance"
                    element={<PerformancePage />}
                  />
                  <Route path="/projects/:id/seo" element={<SeoPage />} />
                  <Route path="/projects/:id/geo" element={<GeoPage />} />
                  <Route path="/projects/:id/serp" element={<SerpPage />} />
                  <Route path="/projects/:id/community" element={<CommunityPage />} />
                  <Route path="/projects/:id/graph" element={<GraphPage />} />
                  <Route path="/projects/:id/monitors" element={<ProjectMonitorsPage />} />
                  <Route path="/projects/:id/github-leads" element={<GitHubLeadsPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                </Routes>
              </Suspense>
            </AppShell>
          </RequireAuth>
        )}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/">
      <AppRoutes />
      <PublicFloatingWidgets />
    </BrowserRouter>
  );
}
