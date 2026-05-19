import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  PauseCircle,
  Radar,
  TerminalSquare,
} from "lucide-react";
import type { TranslationKey } from "../../i18n";
import { useI18n } from "../../i18n";
import type { LatestScans, MonitoringSummary, Project } from "../../types";
import { utcDate } from "../../utils/time";

type ConsoleStatus = "completed" | "running" | "paused" | "needsReview";
type CommandCenterKey = `commandCenter.${string}`;

type ProjectConsoleStatusProps = {
  project: Project;
  latestMonitoring?: MonitoringSummary | null;
  isPaused?: boolean;
  pendingApprovals?: number;
  latest: LatestScans;
};

const STATUS_STYLES: Record<
  ConsoleStatus,
  {
    badge: string;
    dot: string;
    icon: typeof CheckCircle2;
  }
> = {
  completed: {
    badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
    dot: "bg-emerald-500",
    icon: CheckCircle2,
  },
  running: {
    badge: "border-blue-200 bg-blue-50 text-blue-700",
    dot: "bg-blue-500",
    icon: Radar,
  },
  paused: {
    badge: "border-amber-200 bg-amber-50 text-amber-700",
    dot: "bg-amber-500",
    icon: PauseCircle,
  },
  needsReview: {
    badge: "border-rose-200 bg-rose-50 text-rose-700",
    dot: "bg-rose-500",
    icon: AlertCircle,
  },
};

function asTranslationKey(key: CommandCenterKey): TranslationKey {
  return key as TranslationKey;
}

function getConsoleStatus({
  latestMonitoring,
  isPaused,
  pendingApprovals,
}: {
  latestMonitoring?: MonitoringSummary | null;
  isPaused?: boolean;
  pendingApprovals: number;
}): ConsoleStatus {
  if (isPaused) return "paused";
  if (latestMonitoring?.status === "pending" || latestMonitoring?.status === "running") return "running";
  if (pendingApprovals > 0) return "needsReview";
  return "completed";
}

function parseTimestamp(value?: string | null): number | null {
  if (!value) return null;
  const timestamp = utcDate(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

function getLatestScanDate(latest: LatestScans, latestMonitoring?: MonitoringSummary | null): Date | null {
  const timestamps = [
    parseTimestamp(latest.seo?.scanned_at),
    parseTimestamp(latest.geo?.scanned_at),
    parseTimestamp(latest.community?.scanned_at),
    parseTimestamp(latestMonitoring?.completed_at),
    parseTimestamp(latestMonitoring?.created_at),
    ...latest.serp.map((snapshot) => parseTimestamp(snapshot.checked_at)),
  ].filter((value): value is number => value != null);

  if (timestamps.length === 0) return null;
  return new Date(Math.max(...timestamps));
}

function getTargetHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function formatScanDate(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function ProjectConsoleStatus({
  project,
  latestMonitoring,
  isPaused,
  pendingApprovals = 0,
  latest,
}: ProjectConsoleStatusProps) {
  const { locale, t } = useI18n();
  const tc = (key: CommandCenterKey, params?: Record<string, string | number>) =>
    t(asTranslationKey(key), params);

  const status = getConsoleStatus({ latestMonitoring, isPaused, pendingApprovals });
  const statusStyle = STATUS_STYLES[status];
  const StatusIcon = statusStyle.icon;
  const latestScanDate = getLatestScanDate(latest, latestMonitoring);
  const targetHost = getTargetHost(project.url);
  const categoryLabel =
    project.category === "auto" ? tc("commandCenter.categoryAuto") : project.category;
  const scheduleKey = isPaused ? "commandCenter.schedule.paused" : "commandCenter.schedule.daily";
  const scanValue = latestScanDate
    ? formatScanDate(latestScanDate, locale)
    : tc("commandCenter.scan.none");

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white/95 px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-[240px] flex-1 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-700">
            <TerminalSquare size={18} />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              {tc("commandCenter.statusBarTitle")}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="truncate text-sm font-semibold text-slate-950">
                {project.brand_name}
              </span>
              <span className="max-w-[220px] truncate rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {targetHost}
              </span>
            </div>
          </div>
        </div>

        <dl className="flex flex-1 flex-wrap items-stretch gap-2 md:justify-end">
          <div className={`flex min-w-[160px] items-center gap-2 rounded-xl border px-3 py-2 ${statusStyle.badge}`}>
            <dt className="sr-only">{tc("commandCenter.status.label")}</dt>
            <dd className="flex min-w-0 items-center gap-2">
              <span className="relative flex h-2.5 w-2.5 shrink-0">
                {status === "running" && (
                  <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${statusStyle.dot} opacity-70`} />
                )}
                <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${statusStyle.dot}`} />
              </span>
              <StatusIcon size={15} className="shrink-0" />
              <span className="truncate text-sm font-semibold">
                {tc(`commandCenter.status.${status}` as CommandCenterKey)}
              </span>
            </dd>
          </div>

          <div className="min-w-[170px] rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2">
            <dt className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
              <Clock3 size={13} />
              {tc("commandCenter.schedule.label")}
            </dt>
            <dd className="mt-1 truncate text-sm font-semibold text-slate-800">
              {tc(scheduleKey as CommandCenterKey, { category: categoryLabel })}
            </dd>
          </div>

          <div className="min-w-[190px] rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
              {tc("commandCenter.scan.label")}
            </dt>
            <dd className="mt-1 truncate text-sm font-semibold text-slate-800">
              {scanValue}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
