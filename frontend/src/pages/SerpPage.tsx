import { useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import { useSerpLatest, useSerpChart } from "../hooks/useSerpData";
import { useKeywords, useAddKeyword, useDeleteKeyword } from "../hooks/useKeywords";
import { useToast } from "../components/common/Toast";
import { ProjectSubpageSkeleton } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KpiCard } from "../components/common/KpiCard";
import { ChartCard } from "../components/common/ChartCard";
import { AddKeywordForm } from "../components/keywords/AddKeywordForm";
import { SerpRankingChart } from "../components/charts/SerpRankingChart";
import { SerpDistributionBar } from "../components/charts/SerpDistributionBar";
import { useI18n } from "../i18n";
import { ActionTip } from "../components/common/ActionTip";
import { Hash, Target, Trophy, TrendingUp, Trash2 } from "lucide-react";
import type { TrackedKeyword, SerpSnapshot } from "../types";

function positionBucket(pos: number | null): { border: string; bg: string; badge: string } {
  if (pos == null) return { border: "border-l-zinc-300", bg: "", badge: "bg-zinc-100 text-zinc-500" };
  if (pos <= 3) return { border: "border-l-emerald-500", bg: "bg-emerald-50/30", badge: "bg-emerald-100 text-emerald-700" };
  if (pos <= 10) return { border: "border-l-sky-500", bg: "", badge: "bg-sky-100 text-sky-700" };
  if (pos <= 20) return { border: "border-l-amber-500", bg: "", badge: "bg-amber-100 text-amber-700" };
  return { border: "border-l-rose-500", bg: "", badge: "bg-rose-100 text-rose-700" };
}

function EnhancedKeywordList({
  keywords,
  serpData,
  onDelete,
}: {
  keywords: TrackedKeyword[];
  serpData: SerpSnapshot[];
  onDelete: (id: number) => void;
}) {
  const serpMap = Object.fromEntries(serpData.map((s) => [s.keyword, s]));
  const { t } = useI18n();

  if (!keywords.length) {
    return <p className="py-3 text-sm text-gray-500">{t("keywords.noKeywords")}</p>;
  }

  // Sort: ranked first (ascending), then unranked
  const sorted = [...keywords].sort((a, b) => {
    const pa = serpMap[a.keyword]?.position ?? Infinity;
    const pb = serpMap[b.keyword]?.position ?? Infinity;
    return pa - pb;
  });

  return (
    <div className="mt-3 space-y-0.5">
      {sorted.map((kw) => {
        const serp = serpMap[kw.keyword];
        const bucket = positionBucket(serp?.position ?? null);
        return (
          <div
            key={kw.id}
            className={`flex items-center justify-between border-l-4 ${bucket.border} ${bucket.bg} rounded-r-lg px-4 py-2.5 transition-colors hover:bg-zinc-50`}
          >
            <div className="min-w-0 flex-1">
              <span className="text-sm font-medium text-zinc-800">{kw.keyword}</span>
            </div>
            <div className="flex items-center gap-3">
              {serp?.position ? (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${bucket.badge}`}>
                  #{serp.position}
                </span>
              ) : serp?.error ? (
                <span className="text-xs text-rose-500">{t("common.error")}</span>
              ) : (
                <span className="text-xs text-zinc-400">—</span>
              )}
              <span className="text-xs text-zinc-400">
                {serp?.checked_at?.slice(0, 10) ?? ""}
              </span>
              <button
                onClick={() => onDelete(kw.id)}
                className="rounded p-1 text-zinc-400 hover:bg-red-50 hover:text-red-500"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function SerpPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: summary, isLoading } = useProjectSummary(projectId);
  const { data: serpLatest } = useSerpLatest(projectId);
  const { data: serpChart } = useSerpChart(projectId);
  const { data: keywords } = useKeywords(projectId);
  const addKeyword = useAddKeyword(projectId);
  const deleteKeyword = useDeleteKeyword(projectId);
  const { t } = useI18n();
  const toast = useToast();

  if (isLoading) return <ProjectSubpageSkeleton />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;

  const ranked = (serpLatest ?? []).filter((s) => s.position != null);
  const avgPos = ranked.length
    ? ranked.reduce((sum, s) => sum + s.position!, 0) / ranked.length
    : null;
  const top3 = ranked.filter((s) => s.position! <= 3).length;
  const top10 = ranked.filter((s) => s.position! <= 10).length;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ProjectHeader project={summary.project} />
      <ProjectTabs projectId={projectId} />
      <div className="space-y-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          <KpiCard
            icon={Hash}
            label={t("serp.trackedKeywords")}
            value={keywords?.length ?? 0}
            accentBg="bg-indigo-50"
            accentText="text-indigo-600"
          />
          <KpiCard
            icon={Target}
            label={t("serp.avgPosition")}
            value={avgPos != null ? avgPos.toFixed(1) : null}
            status={avgPos != null ? (avgPos <= 3 ? "good" : avgPos <= 10 ? "warning" : "poor") : undefined}
            accentBg="bg-indigo-50"
            accentText="text-indigo-600"
          />
          <KpiCard
            icon={Trophy}
            label={t("serp.inTop3")}
            value={top3}
            accentBg="bg-indigo-50"
            accentText="text-indigo-600"
          />
          <KpiCard
            icon={TrendingUp}
            label={t("serp.inTop10")}
            value={top10}
            accentBg="bg-indigo-50"
            accentText="text-indigo-600"
          />
        </div>

        {/* Position Distribution */}
        {ranked.length > 0 && (
          <ChartCard title={t("serp.positionDistribution")} accentBorder="border-l-indigo-500">
            <SerpDistributionBar data={serpLatest ?? []} />
          </ChartCard>
        )}

        {/* Keyword Management */}
        <ChartCard title={t("serp.trackedKeywords")} accentBorder="border-l-indigo-500">
          <AddKeywordForm
            onAdd={(kw) =>
              addKeyword.mutate(kw, {
                onSuccess: () => toast.success(t("toast.keywordAdded")),
                onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
              })
            }
            isLoading={addKeyword.isPending}
          />
          <EnhancedKeywordList
            keywords={keywords ?? []}
            serpData={serpLatest ?? []}
            onDelete={(kwId) =>
              deleteKeyword.mutate(kwId, {
                onSuccess: () => toast.info(t("toast.keywordRemoved")),
                onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
              })
            }
          />
        </ChartCard>

        {/* Ranking History */}
        {serpChart?.labels?.length ? (
          <ChartCard title={t("serp.rankingHistory")} subtitle="Top 5 keywords shown" accentBorder="border-l-indigo-500">
            <SerpRankingChart data={serpChart} />
          </ChartCard>
        ) : null}

        {/* Action Tips */}
        {!keywords?.length ? (
          <ActionTip title={t("actionTip.serpNoKeywords")} severity="warning" />
        ) : avgPos != null && avgPos > 20 ? (
          <ActionTip title={t("actionTip.serpPoor")} severity="danger" />
        ) : top3 > 0 ? (
          <ActionTip title={t("actionTip.serpGood", { count: top3 })} severity="success" />
        ) : null}
      </div>
    </div>
  );
}
