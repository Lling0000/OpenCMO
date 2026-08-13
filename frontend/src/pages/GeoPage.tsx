import { Link, useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import { useGeoChart } from "../hooks/useGeoData";
import { ProjectSubpageSkeleton, ChartCardSkeleton, KpiRowSkeleton } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KpiCard } from "../components/common/KpiCard";
import { ChartCard } from "../components/common/ChartCard";
import { GeoScoreChart } from "../components/charts/GeoScoreChart";
import { GeoAskPanel } from "../components/geo/GeoAskPanel";
import { useI18n } from "../i18n";
import { ActionTip } from "../components/common/ActionTip";
import { ArrowRight, Gauge, Globe, Eye, MapPin, Heart, Info } from "lucide-react";

interface SovRow {
  name: string;
  mentions: number;
  share: number;
}

interface ShareOfVoice {
  brand: SovRow;
  competitors: SovRow[];
  total_mentions: number;
}

function getDelta(arr: (number | null)[] | undefined): number | null {
  if (!arr || arr.length < 2) return null;
  const curr = arr[arr.length - 1];
  const prev = arr[arr.length - 2];
  if (curr == null || prev == null || prev === 0) return null;
  return ((curr - prev) / Math.abs(prev)) * 100;
}

function latest(arr: (number | null)[] | undefined): number | null {
  if (!arr || !arr.length) return null;
  return arr[arr.length - 1] ?? null;
}

const SNAPSHOT_SERIES = [
  { key: "geo_score", labelKey: "geo.geoScore", color: "bg-emerald-500" },
  { key: "visibility", labelKey: "geo.visibility", color: "bg-violet-500" },
  { key: "position", labelKey: "geo.position", color: "bg-sky-500" },
  { key: "sentiment", labelKey: "geo.sentiment", color: "bg-amber-500" },
];

function InsightCard({
  label,
  value,
  why,
  next,
}: {
  label: string;
  value: string;
  why: string;
  next: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{why}</p>
      <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm font-medium leading-6 text-slate-800">{next}</p>
    </div>
  );
}

export function GeoPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: summary, isLoading: loadingSummary } = useProjectSummary(projectId);
  const { data: chart, isLoading: loadingChart } = useGeoChart(projectId);
  const { t } = useI18n();

  if (loadingSummary) return <ProjectSubpageSkeleton />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;

  const geoScore = chart?.geo_score as (number | null)[] | undefined;
  const visibility = chart?.visibility as (number | null)[] | undefined;
  const position = chart?.position as (number | null)[] | undefined;
  const sentiment = chart?.sentiment as (number | null)[] | undefined;
  const sentimentUnavailable = latest(sentiment) == null;
  const currentGeoScore = latest(geoScore);
  const currentVisibility = latest(visibility);
  const currentPosition = latest(position);
  const currentSentiment = latest(sentiment);
  const sov = (chart as { share_of_voice?: ShareOfVoice | null } | undefined)?.share_of_voice;
  const brandShare = sov ? sov.brand.share * 100 : null;
  const topCompetitor = sov?.competitors?.[0] ?? null;
  const sampleCount = chart?.labels?.length ?? 0;
  const confidence = sampleCount >= 3 && currentGeoScore != null
    ? t("geo.confidenceUsable", { count: sampleCount })
    : t("geo.confidenceLimited", { count: sampleCount });

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ProjectHeader project={summary.project} />
      <ProjectTabs projectId={projectId} />
      <GeoAskPanel projectId={projectId} />
      <div className="mb-4 flex items-center gap-2 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-700">
        <Info className="h-4 w-4 shrink-0" />
        <span>{t("geo.configHint")}</span>
      </div>
      {loadingChart ? (
        <div className="space-y-6">
          <KpiRowSkeleton />
          <ChartCardSkeleton />
        </div>
      ) : !chart?.labels?.length ? (
        <EmptyState title={t("geo.noData")} description={t("geo.noDataDesc")} />
      ) : (
        <div className="space-y-6">
          <section className="rounded-3xl border border-slate-200/80 bg-slate-50 p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                  <Gauge size={14} />
                  {t("geo.insightTitle")}
                </div>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                  {currentGeoScore != null
                    ? t("geo.insightHeadline", { score: Math.round(currentGeoScore) })
                    : t("geo.insightHeadlineMissing")}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{confidence}</p>
              </div>
              <Link
                to={`/projects/${projectId}/graph`}
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                {brandShare != null && topCompetitor && brandShare < topCompetitor.share * 100
                  ? t("geo.openGraphGaps")
                  : t("geo.runNextScan")}
                <ArrowRight size={15} />
              </Link>
            </div>
            <div className="mt-5 grid gap-3 lg:grid-cols-4">
              <InsightCard
                label={t("geo.coverage")}
                value={brandShare != null ? `${brandShare.toFixed(1)}%` : t("geo.notCollected")}
                why={sov ? t("geo.coverageWhy", { total: sov.total_mentions }) : t("geo.coverageMissing")}
                next={brandShare != null && brandShare < 20 ? t("geo.coverageNextLow") : t("geo.coverageNext")}
              />
              <InsightCard
                label={t("geo.shareOfVoice")}
                value={topCompetitor ? `${sov?.brand.name} vs ${topCompetitor.name}` : t("geo.notCollected")}
                why={topCompetitor ? t("geo.sovWhy", { share: (topCompetitor.share * 100).toFixed(1) }) : t("geo.sovMissing")}
                next={topCompetitor ? t("geo.sovNext") : t("geo.addCompetitorsNext")}
              />
              <InsightCard
                label={t("geo.contextAccuracy")}
                value={currentSentiment != null ? `${Math.round(currentSentiment)}/100` : t("geo.limitedSample")}
                why={currentSentiment != null ? t("geo.sentimentWhy") : t("geo.sentimentMissingWhy")}
                next={currentSentiment != null && currentSentiment < 60 ? t("geo.sentimentNextLow") : t("geo.sentimentNext")}
              />
              <InsightCard
                label={t("geo.position")}
                value={currentPosition != null ? `${Math.round(currentPosition)}/100` : t("geo.limitedSample")}
                why={currentVisibility != null ? t("geo.positionWhy", { visibility: Math.round(currentVisibility) }) : t("geo.positionMissing")}
                next={currentPosition != null && currentPosition < 50 ? t("geo.positionNextLow") : t("geo.positionNext")}
              />
            </div>
          </section>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            <KpiCard
              icon={Globe}
              label={t("geo.geoScore")}
              value={latest(geoScore) != null ? `${Math.round(latest(geoScore)!)}/100` : null}
              delta={getDelta(geoScore)}
              accentBg="bg-emerald-50"
              accentText="text-emerald-600"
            />
            <KpiCard
              icon={Eye}
              label={t("geo.visibility")}
              value={latest(visibility) != null ? `${Math.round(latest(visibility)!)}/100` : null}
              delta={getDelta(visibility)}
              accentBg="bg-emerald-50"
              accentText="text-emerald-600"
            />
            <KpiCard
              icon={MapPin}
              label={t("geo.position")}
              value={latest(position) != null ? `${Math.round(latest(position)!)}/100` : null}
              delta={getDelta(position)}
              accentBg="bg-emerald-50"
              accentText="text-emerald-600"
            />
            <KpiCard
              icon={Heart}
              label={t("geo.sentiment")}
              value={latest(sentiment) != null ? `${Math.round(latest(sentiment)!)}/100` : null}
              delta={getDelta(sentiment)}
              accentBg="bg-emerald-50"
              accentText="text-emerald-600"
            />
          </div>

          {/* AI Visibility Trends */}
          <ChartCard title={t("geo.scoreTrend")} accentBorder="border-l-emerald-500">
            <GeoScoreChart data={chart} />
          </ChartCard>

          {/* Latest Snapshot — progress bars */}
          <ChartCard title={t("geo.latestSnapshot")} accentBorder="border-l-emerald-500">
            <div className="space-y-4">
              {SNAPSHOT_SERIES.map((s) => {
                const arr = chart[s.key] as (number | null)[] | undefined;
                const val = arr?.[arr.length - 1];
                return (
                  <div key={s.key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-zinc-700">{t(s.labelKey as never)}</span>
                      <span className="font-mono text-zinc-500">
                        {val != null ? Math.round(val) : "—"}/100
                      </span>
                    </div>
                    <div className="h-3 w-full overflow-hidden rounded-full bg-zinc-100">
                      <div
                        className={`h-full rounded-full ${s.color} transition-all duration-700`}
                        style={{ width: `${val != null ? Math.min(val, 100) : 0}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </ChartCard>

          {/* Share of Voice */}
          {(() => {
            if (!sov) return null;
            const total = sov.total_mentions || 0;
            return (
              <ChartCard title={t("geo.shareOfVoice") || "Share of Voice"} accentBorder="border-l-emerald-500">
                <div className="space-y-3">
                  <div className="text-xs text-zinc-500">
                    {t("geo.shareOfVoiceTotal") || "Total mentions"}: <span className="font-mono text-zinc-700">{total}</span>
                  </div>
                  {[sov.brand, ...sov.competitors].map((row, idx) => (
                    <div key={`${row.name}-${idx}`}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className={idx === 0 ? "font-semibold text-emerald-700" : "text-zinc-700"}>
                          {row.name}
                        </span>
                        <span className="font-mono text-zinc-500">
                          {row.mentions} · {(row.share * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${idx === 0 ? "bg-emerald-500" : "bg-zinc-400"}`}
                          style={{ width: `${Math.min(row.share * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </ChartCard>
            );
          })()}

          {/* Action Tips */}
          {sentimentUnavailable ? (
            <ActionTip title={t("geo.sentimentUnavailable")} severity="warning" />
          ) : (() => {
            const score = latest(geoScore);
            if (score == null) return null;
            if (score >= 70) return <ActionTip title={t("actionTip.geoExcellent")} severity="success" />;
            if (score >= 30) return <ActionTip title={t("actionTip.geoWarning")} severity="warning" />;
            return <ActionTip title={t("actionTip.geoPoor")} severity="danger" />;
          })()}
        </div>
      )}
    </div>
  );
}
