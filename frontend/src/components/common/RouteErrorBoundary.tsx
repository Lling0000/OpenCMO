import { Component, type ReactNode } from "react";
import { useLocation } from "react-router";
import { useI18n } from "../../i18n";

class RouteBoundary extends Component<
  { children: ReactNode; fallback: ReactNode; resetKey: string },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(previous: Readonly<{ resetKey: string }>) {
    // Reset only after a failure. A pathname key on the boundary itself would
    // remount healthy pages and the console shell on every navigation.
    if (this.state.failed && previous.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function RouteErrorBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const { t } = useI18n();
  return (
    <RouteBoundary
      resetKey={pathname}
      fallback={(
        <div role="alert" className="flex min-h-64 flex-col items-center justify-center gap-4 p-8 text-center">
          <h1 className="text-lg font-semibold">{t("route.loadError")}</h1>
          <p className="text-sm text-slate-500">{t("route.loadErrorHint")}</p>
          <button
            type="button"
            className="rounded-lg bg-slate-950 px-4 py-2 text-sm text-white"
            onClick={() => window.location.reload()}
          >
            {t("route.reload")}
          </button>
        </div>
      )}
    >
      {children}
    </RouteBoundary>
  );
}
