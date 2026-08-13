import { useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import { useDiscussions, useCommunityChart } from "../hooks/useCommunityData";
import { ProjectSubpageSkeleton } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KpiCard } from "../components/common/KpiCard";
import { ChartCard } from "../components/common/ChartCard";
import { CommunityBarChart } from "../components/charts/CommunityBarChart";
import { PlatformBreakdownChart } from "../components/charts/PlatformBreakdownChart";
import { ExternalLink, Users, MessageCircle, Flame, Layers } from "lucide-react";
import { useI18n } from "../i18n";
import { ActionTip } from "../components/common/ActionTip";
import type { Discussion } from "../types";

type Translate = ReturnType<typeof useI18n>["t"];

const PLATFORM_BADGE: Record<string, string> = {
  reddit: "bg-orange-100 text-orange-700",
  hackernews: "bg-orange-50 text-orange-600",
  twitter: "bg-sky-100 text-sky-700",
  stackoverflow: "bg-yellow-100 text-yellow-700",
  github: "bg-indigo-100 text-indigo-700",
};

const INTENT_BADGE: Record<string, string> = {
  direct_mention: "bg-emerald-100 text-emerald-700",
  competitor_mention: "bg-violet-100 text-violet-700",
  opportunity: "bg-amber-100 text-amber-700",
};

const INTENT_ORDER: Record<string, number> = {
  direct_mention: 0,
  competitor_mention: 1,
  opportunity: 2,
};

function sortDiscussions(items: Discussion[]): Discussion[] {
  return [...items].sort((a, b) => {
    const intentDiff =
      (INTENT_ORDER[a.intent_type ?? "opportunity"] ?? 9) -
      (INTENT_ORDER[b.intent_type ?? "opportunity"] ?? 9);
    if (intentDiff !== 0) return intentDiff;

    const confidenceDiff = (b.confidence ?? 0) - (a.confidence ?? 0);
    if (confidenceDiff !== 0) return confidenceDiff;

    const engagementDiff = (b.engagement_score ?? 0) - (a.engagement_score ?? 0);
    if (engagementDiff !== 0) return engagementDiff;

    return (b.comments_count ?? 0) - (a.comments_count ?? 0);
  });
}

function getIntentLabel(t: Translate, intent: Discussion["intent_type"]) {
  switch (intent) {
    case "direct_mention":
      return t("community.intent.direct_mention");
    case "competitor_mention":
      return t("community.intent.competitor_mention");
    default:
      return t("community.intent.opportunity");
  }
}

function getSourceLabel(t: Translate, sourceKind: Discussion["source_kind"]) {
  switch (sourceKind) {
    case "post":
      return t("community.source.post");
    case "comment":
      return t("community.source.comment");
    case "external_search":
      return t("community.source.externalSearch");
    default:
      return t("community.source.unknown");
  }
}

export function CommunityPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: summary, isLoading } = useProjectSummary(projectId);
  const { data: discussions } = useDiscussions(projectId);
  const { data: chart } = useCommunityChart(projectId);
  const { t } = useI18n();

  if (isLoading) return <ProjectSubpageSkeleton />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;

  const latestHits = chart?.scan_hits?.[chart.scan_hits.length - 1] ?? 0;
  const prevHits = chart?.scan_hits?.[chart.scan_hits.length - 2];
  const hitsDelta =
    prevHits != null && prevHits > 0
      ? ((latestHits - prevHits) / prevHits) * 100
      : null;

  const avgEngagement =
    discussions?.length
      ? discussions.reduce((s, d) => s + (d.engagement_score ?? 0), 0) / discussions.length
      : null;

  const platformCount = discussions?.length
    ? new Set(discussions.map((d) => d.platform)).size
    : 0;

  const maxEngagement = discussions?.length
    ? Math.max(...discussions.map((d) => d.engagement_score ?? 0), 1)
    : 1;

  const sorted = sortDiscussions(discussions ?? []);
  const directMentions = sorted.filter((d) => d.intent_type !== "opportunity");
  const opportunityThreads = sorted.filter((d) => d.intent_type === "opportunity");

  const renderDiscussionList = (items: Discussion[]) => (
    <div className="space-y-2">
      {items.map((d) => {
        const badgeClass =
          PLATFORM_BADGE[d.platform.toLowerCase()] ?? "bg-zinc-100 text-zinc-600";
        const intentClass =
          INTENT_BADGE[d.intent_type ?? "opportunity"] ?? "bg-zinc-100 text-zinc-600";
        const engRatio = (d.engagement_score ?? 0) / maxEngagement;
        const barColor =
          engRatio > 0.7
            ? "bg-emerald-500"
            : engRatio > 0.4
              ? "bg-amber-400"
              : "bg-zinc-300";
        const confidence = d.confidence != null ? `${Math.round(d.confidence * 100)}%` : "n/a";
        return (
          <div
            key={d.id}
            className="rounded-lg border border-zinc-100 px-3 py-3 transition-colors hover:bg-zinc-50"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}`}>
                {d.platform}
              </span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${intentClass}`}>
                {getIntentLabel(t, d.intent_type)}
              </span>
              <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600">
                {t("community.confidence")}: {confidence}
              </span>
              <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600">
                {getSourceLabel(t, d.source_kind)}
              </span>
            </div>

            <div className="mt-2 min-w-0">
              <a
                href={d.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
              >
                <span className="truncate">{d.title}</span>
                <ExternalLink size={12} className="shrink-0" />
              </a>
              {d.match_reason ? (
                <p className="mt-1 text-xs text-zinc-500">{d.match_reason}</p>
              ) : null}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-3">
              {d.source_kind === "external_search" ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                  {t("community.externalSearchNoMetrics")}
                </span>
              ) : (
                <>
                  <div className="flex w-24 items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
                      <div
                        className={`h-full rounded-full ${barColor} transition-all duration-500`}
                        style={{ width: `${engRatio * 100}%` }}
                      />
                    </div>
                    <span className="w-8 text-right font-mono text-xs text-zinc-500">
                      {d.engagement_score ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-zinc-400">
                    <MessageCircle size={12} />
                    {d.comments_count ?? 0}
                  </div>
                </>
              )}
              {d.matched_query ? (
                <code className="rounded bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-600">
                  {d.matched_query}
                </code>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ProjectHeader project={summary.project} />
      <ProjectTabs projectId={projectId} />
      <div className="space-y-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          <KpiCard
            icon={Users}
            label={t("community.trackedDiscussions")}
            value={discussions?.length ?? 0}
            accentBg="bg-amber-50"
            accentText="text-amber-600"
          />
          <KpiCard
            icon={MessageCircle}
            label={t("community.latestHits")}
            value={latestHits}
            delta={hitsDelta}
            accentBg="bg-amber-50"
            accentText="text-amber-600"
          />
          <KpiCard
            icon={Flame}
            label={t("community.avgEngagement")}
            value={avgEngagement != null ? avgEngagement.toFixed(1) : null}
            accentBg="bg-amber-50"
            accentText="text-amber-600"
          />
          <KpiCard
            icon={Layers}
            label={t("community.platforms")}
            value={platformCount}
            accentBg="bg-amber-50"
            accentText="text-amber-600"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {chart?.scan_labels?.length ? (
            <ChartCard title={t("community.scanHistory")} accentBorder="border-l-amber-500">
              <CommunityBarChart data={chart} />
            </ChartCard>
          ) : null}
          {chart?.platform_labels?.length ? (
            <ChartCard title={t("community.platformBreakdown")} accentBorder="border-l-amber-500">
              <PlatformBreakdownChart
                labels={chart.platform_labels}
                counts={chart.platform_counts}
              />
            </ChartCard>
          ) : null}
        </div>

        {/* Enhanced Discussion List */}
        <ChartCard
          title={t("community.trackedDiscussions")}
          subtitle={discussions?.length ? `${discussions.length} discussions` : undefined}
          accentBorder="border-l-amber-500"
        >
          {!sorted.length ? (
            <EmptyState
              title={t("community.noDiscussions")}
              description={t("community.noDiscussionsDesc")}
            />
          ) : (
            <div className="space-y-6">
              {directMentions.length ? (
                <section className="space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900">
                      {t("community.directMentions")}
                    </h3>
                    <p className="text-xs text-zinc-500">
                      {t("community.directMentionsDesc")}
                    </p>
                  </div>
                  {renderDiscussionList(directMentions)}
                </section>
              ) : null}
              {opportunityThreads.length ? (
                <section className="space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900">
                      {t("community.opportunityThreads")}
                    </h3>
                    <p className="text-xs text-zinc-500">
                      {t("community.opportunityThreadsDesc")}
                    </p>
                  </div>
                  {renderDiscussionList(opportunityThreads)}
                </section>
              ) : null}
            </div>
          )}
        </ChartCard>
      </div>

        {/* Action Tips */}
        {!discussions?.length ? (
          <ActionTip title={t("actionTip.communityNone")} severity="warning" actionLabel={t("chat.title")} actionTo="/chat" />
        ) : discussions.length >= 5 ? (
          <ActionTip title={t("actionTip.communityActive")} severity="success" actionLabel={t("nav.approvals")} actionTo="/approvals" />
        ) : null}
    </div>
  );
}
