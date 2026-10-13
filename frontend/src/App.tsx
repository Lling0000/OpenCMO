import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Navigate, Routes, Route, useLocation } from "react-router";
import { RouteErrorBoundary } from "./components/common/RouteErrorBoundary";
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
import { BlogPage } from "./pages/BlogPage";
import { BlogArticlePage } from "./pages/BlogArticlePage";
import { SampleAuditPage } from "./pages/SampleAuditPage";
import { useAuth } from "./components/auth/useAuth";

// Keep public pages eager for their metadata and locale effects. Console modules
// are imported only after RequireAuth permits rendering; declarations stay at
// module scope so navigation never creates new lazy component identities.
const AppShell = lazy(() =>
  import("./components/layout/AppShell").then((m) => ({ default: m.AppShell }))
);
const AdminPage = lazy(() =>
  import("./pages/AdminPage").then((m) => ({ default: m.AdminPage }))
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const ProjectPage = lazy(() =>
  import("./pages/ProjectPage").then((m) => ({ default: m.ProjectPage }))
);
const SeoPage = lazy(() =>
  import("./pages/SeoPage").then((m) => ({ default: m.SeoPage }))
);
const GeoPage = lazy(() =>
  import("./pages/GeoPage").then((m) => ({ default: m.GeoPage }))
);
const SerpPage = lazy(() =>
  import("./pages/SerpPage").then((m) => ({ default: m.SerpPage }))
);
const CommunityPage = lazy(() =>
  import("./pages/CommunityPage").then((m) => ({ default: m.CommunityPage }))
);
const ApprovalsPage = lazy(() =>
  import("./pages/ApprovalsPage").then((m) => ({ default: m.ApprovalsPage }))
);
const BrandKitPage = lazy(() =>
  import("./pages/BrandKitPage").then((m) => ({ default: m.BrandKitPage }))
);
const ProjectMonitorsPage = lazy(() =>
  import("./pages/ProjectMonitorsPage").then((m) => ({ default: m.ProjectMonitorsPage }))
);
const GitHubLeadsPage = lazy(() =>
  import("./pages/GitHubLeadsPage").then((m) => ({ default: m.GitHubLeadsPage }))
);
const ContentPage = lazy(() =>
  import("./pages/ContentPage").then((m) => ({ default: m.ContentPage }))
);
const KnowledgePage = lazy(() =>
  import("./pages/KnowledgePage").then((m) => ({ default: m.KnowledgePage }))
);
// Heavy graph, markdown and chart pages retain their own chunks.
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
            <Suspense fallback={<AuthLoading />}>
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
                    <Route path="/projects/:id/knowledge" element={<KnowledgePage />} />
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
            </Suspense>
          </RequireAuth>
        )}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/">
      <RouteErrorBoundary>
        <AppRoutes />
      </RouteErrorBoundary>
      <PublicFloatingWidgets />
    </BrowserRouter>
  );
}
