import { AlertCircle, AlertTriangle, RefreshCw, X } from "lucide-react";
import type { ReactNode } from "react";

export type ErrorTone = "error" | "warning";

export interface ErrorAlertProps {
  message: string;
  /** Optional machine-readable code (e.g. "auto_publish_disabled", "401"). */
  code?: string;
  /** Human hint about how to recover (one short sentence). */
  hint?: string;
  /** "Try again" callback — renders an inline retry button when present. */
  onRetry?: () => void;
  /** Dismiss callback — renders an × button when present. */
  onDismiss?: () => void;
  /** Optional custom action (e.g. "Go to Settings"). */
  action?: ReactNode;
  /** Visual tone. Defaults to "error" (rose). */
  tone?: ErrorTone;
  /** Adds margin-bottom for convenient banner placement. */
  asBanner?: boolean;
  /** Label for the retry button (i18n). Defaults to "Try again". */
  retryLabel?: string;
}

const TONE: Record<
  ErrorTone,
  {
    border: string;
    bg: string;
    iconColor: string;
    titleColor: string;
    bodyColor: string;
    btnBorder: string;
    btnText: string;
    btnHover: string;
  }
> = {
  error: {
    border: "border-rose-200",
    bg: "bg-rose-50/80",
    iconColor: "text-rose-500",
    titleColor: "text-rose-900",
    bodyColor: "text-rose-700",
    btnBorder: "border-rose-300",
    btnText: "text-rose-800",
    btnHover: "hover:bg-rose-100/60",
  },
  warning: {
    border: "border-amber-200",
    bg: "bg-amber-50/80",
    iconColor: "text-amber-600",
    titleColor: "text-amber-900",
    bodyColor: "text-amber-700",
    btnBorder: "border-amber-300",
    btnText: "text-amber-800",
    btnHover: "hover:bg-amber-100/60",
  },
};

/**
 * Surface an error or warning. Designed to be informative and actionable,
 * not a dead-end. Always prefer providing `hint`, `onRetry`, or `action` so
 * the user has a way out.
 */
export function ErrorAlert({
  message,
  code,
  hint,
  onRetry,
  onDismiss,
  action,
  tone = "error",
  asBanner,
  retryLabel = "Try again",
}: ErrorAlertProps) {
  const t = TONE[tone];
  const Icon = tone === "warning" ? AlertTriangle : AlertCircle;
  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-xl border ${t.border} ${t.bg} p-4 shadow-sm ${
        asBanner ? "mb-4" : ""
      }`}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${t.iconColor}`} strokeWidth={2.2} />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${t.titleColor}`}>{message}</p>
        {hint && <p className={`mt-1 text-sm ${t.bodyColor}`}>{hint}</p>}
        {code && (
          <p className="mt-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-400">
            {code}
          </p>
        )}
        {(action || onRetry) && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw className="h-3.5 w-3.5" strokeWidth={2.4} />
                {retryLabel}
              </button>
            )}
            {action}
          </div>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="-mr-1 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-white/60 hover:text-slate-700"
        >
          <X className="h-4 w-4" strokeWidth={2.4} />
        </button>
      )}
    </div>
  );
}
