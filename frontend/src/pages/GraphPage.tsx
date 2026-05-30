import { Link, useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import { useGraphData, useExpansionStatus } from "../hooks/useGraphData";
import { GraphSkeleton } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KnowledgeGraph } from "../components/charts/KnowledgeGraph";
import { CompetitorPanel } from "../components/charts/CompetitorPanel";
import { ExpansionControls } from "../components/charts/ExpansionControls";
import { useI18n } from "../i18n";
import { ArrowRight, GitBranch } from "lucide-react";

export function GraphPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: summary, isLoading } = useProjectSummary(projectId);
  const { data: expansion } = useExpansionStatus(projectId);
  const isExpanding = expansion?.runtime_state === "running";
  const { data: graph, isLoading: loadingGraph } = useGraphData(projectId, isExpanding);
  const { t } = useI18n();

  if (isLoading) return <GraphSkeleton />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;
  const nodes = graph?.nodes ?? [];
  const competitorNodes = nodes.filter((node) => node.type === "competitor").length;
  const keywordNodes = nodes.filter((node) => node.type === "keyword").length;
  const competitorKeywordNodes = nodes.filter((node) => node.type === "competitor_keyword").length;
  const frontierNodes = nodes.filter((node) => node.depth != null && node.depth > 0 && node.explored === false).length;
  const primaryAction = competitorNodes === 0
    ? { label: t("graph.discoverCompetitors"), to: `/projects/${projectId}/graph` }
    : frontierNodes > 0 || expansion?.runtime_state === "running"
      ? { label: t("graph.continueExpansion"), to: `/projects/${projectId}/graph` }
      : competitorKeywordNodes > keywordNodes
        ? { label: t("graph.openKeywordGaps"), to: `/projects/${projectId}/serp` }
        : { label: t("graph.runGeoScan"), to: `/projects/${projectId}/geo` };
  const topGap = competitorKeywordNodes > keywordNodes
    ? t("graph.briefCompetitorKeywordGap", { competitorKeywords: competitorKeywordNodes, keywords: keywordNodes })
    : competitorNodes === 0
      ? t("graph.briefNoCompetitors")
      : frontierNodes > 0
        ? t("graph.briefFrontierGap", { count: frontierNodes })
        : t("graph.briefStable");

  return (
    <div>
      <ProjectHeader project={summary.project} isPaused={summary.is_paused} />
      <ProjectTabs projectId={projectId} />
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200/80 bg-slate-50 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                <GitBranch size={14} />
                {t("graph.briefTitle")}
              </div>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{topGap}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {t("graph.briefEvidence", {
                  competitors: competitorNodes,
                  keywords: keywordNodes,
                  competitorKeywords: competitorKeywordNodes,
                  frontier: frontierNodes,
                })}
              </p>
            </div>
            <Link
              to={primaryAction.to}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              {primaryAction.label}
              <ArrowRight size={15} />
            </Link>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              [t("graph.entityCompleteness"), String(competitorNodes), t("graph.entityCompetitors")],
              [t("graph.trackedKeywords"), String(keywordNodes), t("graph.entityKeywords")],
              [t("graph.competitorGaps"), String(competitorKeywordNodes), t("graph.entityCompetitorKeywords")],
              [t("graph.frontier"), String(frontierNodes), t("graph.entityFrontier")],
            ].map(([label, value, detail]) => (
              <div key={label} className="rounded-2xl border border-slate-200/80 bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</p>
                <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">{detail}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Expansion controls */}
        <ExpansionControls projectId={projectId} />

        {/* Graph */}
        {loadingGraph ? (
          <div className="rounded-2xl bg-slate-100 animate-pulse" style={{ height: "min(640px, calc(100vh - 16rem))" }} />
        ) : !graph || graph.nodes.length === 0 ? (
          <EmptyState
            title={t("graph.noData")}
            description={t("graph.noDataDesc")}
          />
        ) : (
          <KnowledgeGraph data={graph} />
        )}

        {/* Competitor management */}
        <CompetitorPanel projectId={projectId} />
      </div>
    </div>
  );
}
