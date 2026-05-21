import { ArrowRight, Bot, CheckCircle2, FileText, GitBranch, Globe, PenLine, Search, Target, Users } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import type { LatestReports, LatestScans, MonitoringSummary } from "../../types";
import { useI18n } from "../../i18n";
import { useNextActions } from "../../hooks/useProject";
import { utcDate } from "../../utils/time";
import type { TranslationKey } from "../../i18n";
import type { NextAction } from "../../api/projects";

type AgentCardData = {
  key: string;
  title: string;
  icon: React.ElementType;
  found: string;
  why: string;
  next: string;
  action?: ReactNode;
};

type RouteKey =
  | "changedToday"
  | "whatMattersNow"
  | "readyToShip"
  | "siteHealth"
  | "aiSearch"
  | "community"
  | "competitor"
  | "keywords"
  | "scan"
  | "report";

type PriorityItem = {
  key: string;
  title: string;
  body: string;
  label: string;
  to: string;
};

function SummaryCard({
  label,
  value,
  body,
}: {
  label: string;
  value: string | number;
  body: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
        {label}
      </p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </article>
  );
}

function OutcomeMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 truncate text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{detail}</p>
    </div>
  );
}

function AgentCard({
  title,
  icon: Icon,
  found,
  why,
  next,
  action,
  whatFoundLabel,
  whyLabel,
  nextLabel,
}: AgentCardData & {
  whatFoundLabel: string;
  whyLabel: string;
  nextLabel: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
          <Icon size={18} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {whatFoundLabel}
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{found}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {whyLabel}
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{why}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {nextLabel}
          </p>
          <p className="mt-1 rounded-2xl bg-slate-50 px-3 py-2 text-sm font-medium leading-6 text-slate-950">
            {next}
          </p>
        </div>
        {action && <div className="mt-2">{action}</div>}
      </div>
    </article>
  );
}

function getLatestSerpTimestamp(latest: LatestScans) {
  // Tolerate older/partial payloads where `serp` is missing — without this
  // fallback the optional-chained `.map` chain blows up and surfaces as a
  // blank project page.
  const timestamps = (latest.serp ?? [])
    .map((snapshot) => snapshot.checked_at)
    .filter((value): value is string => Boolean(value))
    .map((value) => utcDate(value).getTime());

  if (timestamps.length === 0) return null;
  return new Date(Math.max(...timestamps));
}

function countFreshSurfaces(latest: LatestScans) {
  const freshCutoff = Date.now() - 24 * 60 * 60 * 1000;
  const timestamps = [
    latest.seo?.scanned_at ? utcDate(latest.seo.scanned_at).getTime() : null,
    latest.geo?.scanned_at ? utcDate(latest.geo.scanned_at).getTime() : null,
    latest.community?.scanned_at ? utcDate(latest.community.scanned_at).getTime() : null,
    getLatestSerpTimestamp(latest)?.getTime() ?? null,
  ];

  return timestamps.filter((value): value is number => value != null && value >= freshCutoff).length;
}

function hasReadyReport(latestReports?: LatestReports) {
  return Boolean(
    latestReports?.strategic?.human ||
      latestReports?.strategic?.agent ||
      latestReports?.periodic?.human ||
      latestReports?.periodic?.agent,
  );
}

function hasAnyScanData(latest: LatestScans, latestMonitoring?: MonitoringSummary | null) {
  return Boolean(
    latest.seo ||
      latest.geo ||
      latest.community ||
      (latest.serp?.length ?? 0) > 0 ||
      latestMonitoring,
  );
}

export function ProjectCommandCenter({
  projectId,
  latest,
  latestMonitoring,
  latestReports,
  competitorCount,
  keywordCount,
  pendingApprovals = 0,
  blogDraftsCount = 0,
  actionsOverride,
  routeOverrides,
  contentAction,
}: {
  projectId: number;
  latest: LatestScans;
  latestMonitoring?: MonitoringSummary | null;
  latestReports?: LatestReports;
  competitorCount?: number;
  keywordCount?: number;
  pendingApprovals?: number;
  blogDraftsCount?: number;
  actionsOverride?: NextAction[];
  contentAction?: ReactNode;
  routeOverrides?: Partial<Record<RouteKey, string>>;
}) {
  const { data } = useNextActions(projectId, !actionsOverride);
  const { t } = useI18n();
  const actions = actionsOverride ?? data?.actions ?? [];
  const surfaceUpdates = countFreshSurfaces(latest);
  const findingsCount = latestMonitoring?.findings_count ?? 0;
  const recommendationsCount = latestMonitoring?.recommendations_count ?? 0;
  const reportReady = hasReadyReport(latestReports);
  const hasScanData = hasAnyScanData(latest, latestMonitoring);
  const competitorTotal = competitorCount ?? 0;
  const missingCompetitors = competitorCount != null && competitorCount === 0;
  const missingKeywords = keywordCount != null && keywordCount === 0;
  const needsSetup = !hasScanData || missingCompetitors || missingKeywords;
  const routes = {
    changedToday: routeOverrides?.changedToday ?? `/projects/${projectId}/seo`,
    whatMattersNow: routeOverrides?.whatMattersNow ?? (pendingApprovals > 0 ? "/approvals" : `/projects/${projectId}/community`),
    readyToShip: routeOverrides?.readyToShip ?? (pendingApprovals > 0 ? "/approvals" : `/projects/${projectId}/reports`),
    siteHealth: routeOverrides?.siteHealth ?? `/projects/${projectId}/seo`,
    aiSearch: routeOverrides?.aiSearch ?? `/projects/${projectId}/geo`,
    community: routeOverrides?.community ?? `/projects/${projectId}/community`,
    competitor: routeOverrides?.competitor ?? `/projects/${projectId}/graph`,
    keywords: routeOverrides?.keywords ?? `/projects/${projectId}/serp`,
    scan: routeOverrides?.scan ?? `/projects/${projectId}/monitors`,
    report: routeOverrides?.report ?? `/projects/${projectId}/reports`,
  };

  const getActionTitle = (domain: string, fallbackKey: TranslationKey) =>
    actions.find((item) => item.domain === domain)?.title ?? t(fallbackKey);
  const routeByDomain = {
    seo: routes.siteHealth,
    geo: routes.aiSearch,
    community: routes.community,
    graph: routes.competitor,
    report: routes.report,
  } satisfies Partial<Record<string, string>>;

  const siteHealthFound =
    latest.seo?.score != null
      ? t("agents.siteHealthFound", { score: Math.round(latest.seo.score * 100) })
      : t("agents.siteHealthPending");
  const aiSearchFound =
    latest.geo?.score != null
      ? t("agents.aiSearchFound", { score: latest.geo.score })
      : t("agents.aiSearchPending");
  const communityFound =
    latest.community?.total_hits != null
      ? t("agents.communityFound", { count: latest.community.total_hits })
      : t("agents.communityPending");
  const competitorFound =
    competitorTotal > 0
      ? t("agents.competitorFound", { count: competitorTotal })
      : t("agents.competitorPending");
  const reportFound =
    latestMonitoring != null
      ? t("agents.reportFound", { findings: findingsCount, actions: recommendationsCount })
      : t("agents.reportPending");
  const contentFound =
    blogDraftsCount > 0
      ? t("agents.contentFound", { count: blogDraftsCount })
      : t("agents.contentPending");
  const seoValue =
    latest.seo?.score != null ? `${Math.round(latest.seo.score * 100)}/100` : t("score.dataUnavailable");
  const geoValue =
    latest.geo?.score != null ? `${Math.round(latest.geo.score)}/100` : t("score.dataUnavailable");
  const communityValue =
    latest.community?.total_hits != null ? String(latest.community.total_hits) : t("score.dataUnavailable");
  const graphValue =
    competitorTotal > 0 ? String(competitorTotal) : t("score.dataUnavailable");

  const primaryAction =
    needsSetup
      ? {
          label: !hasScanData
            ? t("command.runFirstScan")
            : missingCompetitors
              ? t("command.addCompetitors")
              : t("command.addKeywords"),
          to: !hasScanData
            ? routes.scan
            : missingCompetitors
              ? routes.competitor
              : routes.keywords,
          summary: t("command.emptyChecklistTitle"),
        }
      : pendingApprovals > 0
      ? {
          label: t("command.reviewDraft"),
          to: routes.readyToShip,
          summary: t("project.commandMattersText", { count: findingsCount, approvals: pendingApprovals }),
        }
      : reportReady
        ? {
            label: t("command.exportReport"),
            to: routes.report,
            summary: reportFound,
          }
        : actions[0]
          ? {
              label: t("command.openOpportunities"),
              to: routeByDomain[actions[0].domain as keyof typeof routeByDomain] ?? routes.whatMattersNow,
              summary: actions[0].title,
            }
          : {
              label: t("command.reviewFixes"),
              to: routes.changedToday,
              summary: t("project.commandChangedEmpty"),
          };
  const topOpportunity = actions[0]?.title ?? primaryAction.summary;
  const evidenceLine = latestMonitoring
    ? t("outcome.evidenceMonitoring", {
        findings: findingsCount,
        actions: recommendationsCount,
      })
    : surfaceUpdates > 0
      ? t("outcome.evidenceSurfaces", { count: surfaceUpdates })
      : needsSetup
        ? t("outcome.evidenceNeedsBaseline")
        : t("outcome.evidenceNoNewSignals");

  const setupItems: PriorityItem[] = [
    missingCompetitors || !hasScanData
      ? {
          key: "setup-competitors",
          title: t("command.addCompetitors"),
          body: t("command.addCompetitorsDesc"),
          label: t("command.compareCompetitors"),
          to: routes.competitor,
        }
      : null,
    missingKeywords || !hasScanData
      ? {
          key: "setup-keywords",
          title: t("command.addKeywords"),
          body: t("command.addKeywordsDesc"),
          label: t("command.openSearchKeywords"),
          to: routes.keywords,
        }
      : null,
    !hasScanData
      ? {
          key: "setup-scan",
          title: t("command.runFirstScan"),
          body: t("command.runFirstScanDesc"),
          label: t("command.openMonitoring"),
          to: routes.scan,
        }
      : null,
  ].filter((item): item is PriorityItem => item != null);

  const workflowItems: PriorityItem[] = [
    pendingApprovals > 0
      ? {
          key: "review",
          title: t("command.priorityReviewTitle"),
          body: t("command.priorityReviewBody", { count: pendingApprovals }),
          label: t("command.reviewDraft"),
          to: routes.readyToShip,
        }
      : null,
    actions[0]
      ? {
          key: "next-action",
          title: actions[0].title,
          body: actions[0].description,
          label: t("command.openOpportunities"),
          to: routeByDomain[actions[0].domain as keyof typeof routeByDomain] ?? routes.whatMattersNow,
        }
      : null,
    findingsCount > 0
      ? {
          key: "findings",
          title: t("command.priorityFindingsTitle"),
          body: t("command.priorityFindingsBody", { count: findingsCount }),
          label: t("command.reviewFixes"),
          to: routes.changedToday,
        }
      : null,
    reportReady
      ? {
          key: "report",
          title: t("command.priorityReportTitle"),
          body: t("command.priorityReportBody"),
          label: t("command.exportReport"),
          to: routes.report,
        }
      : null,
  ].filter((item): item is PriorityItem => item != null);

  const fallbackItems: PriorityItem[] = [
    {
      key: "monitoring",
      title: t("command.reviewFixes"),
      body: t("project.commandChangedEmpty"),
      label: t("command.reviewFixes"),
      to: routes.changedToday,
    },
  ];
  const prioritySource = needsSetup
    ? [...setupItems, ...workflowItems]
    : workflowItems.length > 0
      ? workflowItems
      : fallbackItems;
  const priorityItems = prioritySource.slice(0, 3);

  const agentCards: AgentCardData[] = [
    {
      key: "site-health",
      title: t("agents.siteHealth"),
      icon: Search,
      found: siteHealthFound,
      why: t("agents.siteHealthWhy"),
      next: getActionTitle("seo", "agents.defaultNext"),
    },
    {
      key: "ai-search",
      title: t("agents.aiSearch"),
      icon: Globe,
      found: aiSearchFound,
      why: t("agents.aiSearchWhy"),
      next: getActionTitle("geo", "agents.defaultNext"),
    },
    {
      key: "community",
      title: t("agents.community"),
      icon: Users,
      found: communityFound,
      why: t("agents.communityWhy"),
      next: getActionTitle("community", "agents.defaultNext"),
    },
    {
      key: "competitor",
      title: t("agents.competitor"),
      icon: GitBranch,
      found: competitorFound,
      why: t("agents.competitorWhy"),
      next: getActionTitle("graph", "agents.defaultNext"),
    },
    {
      key: "report",
      title: t("agents.report"),
      icon: FileText,
      found: reportFound,
      why: t("agents.reportWhy"),
      next: reportReady ? t("agents.reportNext") : t("agents.defaultNext"),
    },
    {
      key: "content",
      title: t("agents.content"),
      icon: PenLine,
      found: contentFound,
      why: t("agents.contentWhy"),
      next: t("agents.contentNext"),
      action: contentAction,
    },
  ];

  return (
    <section className="space-y-5">
      <div className="rounded-3xl border border-slate-200/80 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.08),_transparent_40%),linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-6 shadow-sm">
        <div className="mb-6 rounded-2xl border border-slate-900/10 bg-white/80 p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                <Target size={14} />
                {t("outcome.title")}
              </div>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {topOpportunity}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{evidenceLine}</p>
            </div>
            <Link
              to={primaryAction.to}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
            >
              {primaryAction.label}
              <ArrowRight size={15} />
            </Link>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <OutcomeMetric
              label={t("outcome.seo")}
              value={seoValue}
              detail={latest.seo ? t("outcome.seoEvidence") : t("outcome.missingScan")}
            />
            <OutcomeMetric
              label={t("outcome.geo")}
              value={geoValue}
              detail={latest.geo ? t("outcome.geoEvidence") : t("outcome.missingScan")}
            />
            <OutcomeMetric
              label={t("outcome.community")}
              value={communityValue}
              detail={latest.community ? t("outcome.communityEvidence") : t("outcome.missingScan")}
            />
            <OutcomeMetric
              label={t("outcome.graph")}
              value={graphValue}
              detail={competitorTotal > 0 ? t("outcome.graphEvidence") : t("outcome.graphMissing")}
            />
          </div>
        </div>

        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
              <Bot size={18} />
            </div>
            <div className="max-w-3xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                {t("project.commandTitle")}
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {t("project.commandSubtitle")}
              </h2>
            </div>
          </div>

          <div className="max-w-md rounded-2xl border border-slate-200/80 bg-white/92 p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
              {t("command.readyToShip")}
            </p>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-950">
              {primaryAction.summary}
            </p>
            <Link
              to={primaryAction.to}
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-800"
            >
              {primaryAction.label}
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <SummaryCard
            label={t("command.changedToday")}
            value={surfaceUpdates}
            body={
              surfaceUpdates > 0
                ? t("project.commandChangedText", { count: surfaceUpdates })
                : t("project.commandChangedEmpty")
            }
          />
          <SummaryCard
            label={t("command.whatMattersNow")}
            value={findingsCount}
            body={t("project.commandMattersText", { count: findingsCount, approvals: pendingApprovals })}
          />
          <SummaryCard
            label={t("command.readyToShip")}
            value={recommendationsCount}
            body={
              reportReady
                ? t("project.commandReportReady", { count: recommendationsCount, approvals: pendingApprovals })
                : t("project.commandReportPending", { count: recommendationsCount, approvals: pendingApprovals })
            }
          />
        </div>

        <div className="mt-5 rounded-2xl border border-slate-200/80 bg-white/88 p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                {t("command.priorityTitle")}
              </p>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                {needsSetup ? t("command.prioritySetupSubtitle") : t("command.prioritySubtitle")}
              </p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {priorityItems.map((item) => (
              <Link
                key={item.key}
                to={item.to}
                className="group flex min-w-0 flex-col justify-between rounded-2xl border border-slate-200/80 bg-slate-50/80 p-4 transition hover:border-slate-300 hover:bg-white hover:shadow-sm"
              >
                <div className="min-w-0">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    <p className="min-w-0 text-sm font-semibold leading-6 text-slate-950">
                      {item.title}
                    </p>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
                </div>
                <span className="mt-4 inline-flex w-fit items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition group-hover:text-slate-950">
                  {item.label}
                  <ArrowRight size={13} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm">
        <div className="mb-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
            {t("agents.title")}
          </p>
          <p className="mt-2 text-sm text-slate-600">{t("agents.subtitle")}</p>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {agentCards.map(({ key, ...card }) => (
            <AgentCard
              key={key}
              {...card}
              whatFoundLabel={t("agents.whatFound")}
              whyLabel={t("agents.whyMatters")}
              nextLabel={t("agents.nextStep")}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
