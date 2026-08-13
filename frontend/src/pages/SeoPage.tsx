import { useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import { useSeoChart } from "../hooks/useSeoData";
import { ProjectSubpageSkeleton, ChartCardSkeleton } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KpiCard } from "../components/common/KpiCard";
import { ChartCard } from "../components/common/ChartCard";
import { SeoPerformanceChart } from "../components/charts/SeoPerformanceChart";
import { CwvMiniChart } from "../components/charts/CwvMiniChart";
import { useI18n } from "../i18n";
import { ActionTip } from "../components/common/ActionTip";
import { Gauge, Timer, Move, Zap, MousePointerClick, ShieldCheck, ShieldAlert, Info } from "lucide-react";

function getCwvStatus(value: number | null | undefined, good: number, poor: number): "good" | "warning" | "poor" {
  if (value == null) return "warning";
  return value <= good ? "good" : value <= poor ? "warning" : "poor";
}

function getDelta(arr: (number | null)[] | undefined): number | null {
  if (!arr || arr.length < 2) return null;
  const curr = arr[arr.length - 1];
  const prev = arr[arr.length - 2];
  if (curr == null || prev == null || prev === 0) return null;
  return ((curr - prev) / Math.abs(prev)) * 100;
}

export function SeoPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: summary, isLoading: loadingSummary } = useProjectSummary(projectId);
  const { data: chart, isLoading: loadingChart } = useSeoChart(projectId);
  const { t } = useI18n();

  if (loadingSummary) return <ProjectSubpageSkeleton />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;

  const perf = chart?.performance as (number | null)[] | undefined;
  const lcpMs = chart?.lcp as (number | null)[] | undefined;
  const cls = chart?.cls as (number | null)[] | undefined;
  const tbt = chart?.tbt as (number | null)[] | undefined;
  const inp = chart?.inp as (number | null)[] | undefined;
  const hsts = chart?.has_hsts as (boolean | null)[] | undefined;
  const sec = chart?.has_security_headers as (boolean | null)[] | undefined;
  const pagespeedAvail = chart?.pagespeed_available as (boolean | null)[] | undefined;

  // PageSpeed returns LCP in ms; UI thresholds (2.5s/4s) and labels expect seconds.
  const lcp = lcpMs?.map((v) => (v != null ? v / 1000 : null));

  const latestPerf = perf?.[perf.length - 1];
  const latestLcp = lcp?.[lcp.length - 1];
  const latestCls = cls?.[cls.length - 1];
  const latestTbt = tbt?.[tbt.length - 1];
  const latestInp = inp?.[inp.length - 1];
  const latestHsts = hsts?.[hsts.length - 1];
  const latestSec = sec?.[sec.length - 1];
  const latestPagespeed = pagespeedAvail?.[pagespeedAvail.length - 1];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ProjectHeader project={summary.project} />
      <ProjectTabs projectId={projectId} />
      {loadingChart ? (
        <div className="space-y-6 mt-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <ChartCardSkeleton key={i} height={88} />
            ))}
          </div>
          <ChartCardSkeleton />
        </div>
      ) : !chart?.labels?.length ? (
        <EmptyState title={t("seo.noData")} description={t("seo.noDataDesc")} />
      ) : (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            <KpiCard
              icon={Gauge}
              label={t("score.seoScore")}
              value={latestPerf != null ? `${Math.round(latestPerf * 100)}%` : null}
              delta={getDelta(perf)}
              status={latestPerf != null ? (latestPerf >= 0.9 ? "good" : latestPerf >= 0.5 ? "warning" : "poor") : undefined}
              accentBg="bg-sky-50"
              accentText="text-sky-600"
            />
            <KpiCard
              icon={Timer}
              label={t("seo.metric.lcp")}
              value={latestLcp != null ? `${latestLcp.toFixed(1)}s` : null}
              delta={getDelta(lcp)}
              status={getCwvStatus(latestLcp, 2.5, 4)}
              accentBg="bg-sky-50"
              accentText="text-sky-600"
            />
            <KpiCard
              icon={Move}
              label={t("seo.metric.cls")}
              value={latestCls != null ? latestCls.toFixed(3) : null}
              delta={getDelta(cls)}
              status={getCwvStatus(latestCls, 0.1, 0.25)}
              accentBg="bg-sky-50"
              accentText="text-sky-600"
            />
            <KpiCard
              icon={Zap}
              label={t("seo.metric.tbt")}
              value={latestTbt != null ? `${Math.round(latestTbt)}ms` : null}
              delta={getDelta(tbt)}
              status={getCwvStatus(latestTbt, 200, 600)}
              accentBg="bg-sky-50"
              accentText="text-sky-600"
            />
          </div>

          {/* INP + Security headers strip (only renders when at least one signal is present) */}
          {(latestInp != null || latestHsts != null || latestSec != null) && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {latestInp != null && (
                <KpiCard
                  icon={MousePointerClick}
                  label={t("seo.metric.inp") || "INP (CrUX field)"}
                  value={`${Math.round(latestInp)}ms`}
                  delta={getDelta(inp)}
                  status={getCwvStatus(latestInp, 200, 500)}
                  accentBg="bg-indigo-50"
                  accentText="text-indigo-600"
                />
              )}
              {latestHsts != null && (
                <KpiCard
                  icon={latestHsts ? ShieldCheck : ShieldAlert}
                  label={t("seo.metric.hsts") || "HSTS"}
                  value={latestHsts ? (t("common.present") || "Present") : (t("common.missing") || "Missing")}
                  status={latestHsts ? "good" : "warning"}
                  accentBg={latestHsts ? "bg-emerald-50" : "bg-amber-50"}
                  accentText={latestHsts ? "text-emerald-600" : "text-amber-600"}
                />
              )}
              {latestSec != null && (
                <KpiCard
                  icon={latestSec ? ShieldCheck : ShieldAlert}
                  label={t("seo.metric.securityHeaders") || "X-Frame / CSP"}
                  value={latestSec ? (t("common.present") || "Present") : (t("common.missing") || "Missing")}
                  status={latestSec ? "good" : "warning"}
                  accentBg={latestSec ? "bg-emerald-50" : "bg-amber-50"}
                  accentText={latestSec ? "text-emerald-600" : "text-amber-600"}
                />
              )}
            </div>
          )}

          {latestPagespeed === false && (
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              <Info className="h-4 w-4 shrink-0" />
              <span>
                {t("seo.pagespeedUnavailable") ||
                  "PageSpeed Insights data unavailable for this scan — performance metrics use neutral fallback values. Add PAGESPEED_API_KEY to get real Core Web Vitals."}
              </span>
            </div>
          )}

          {/* Performance Score Trend */}
          <ChartCard title={t("score.seoScore")} accentBorder="border-l-sky-500">
            <SeoPerformanceChart data={chart} />
          </ChartCard>

          {/* Core Web Vitals — individual mini charts */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <ChartCard title={t("seo.metric.lcpFull")} accentBorder="border-l-sky-400">
              <CwvMiniChart
                data={chart.labels.map((label, i) => ({ date: label, value: (lcp as (number | null)[])[i] ?? null }))}
                label={t("seo.metric.lcp")}
                color="#0ea5e9"
                thresholds={[2.5, 4]}
                unit="s"
              />
            </ChartCard>
            <ChartCard title={t("seo.metric.clsFull")} accentBorder="border-l-violet-400">
              <CwvMiniChart
                data={chart.labels.map((label, i) => ({ date: label, value: (cls as (number | null)[])[i] ?? null }))}
                label={t("seo.metric.cls")}
                color="#8b5cf6"
                thresholds={[0.1, 0.25]}
                unit=""
              />
            </ChartCard>
            <ChartCard title={t("seo.metric.tbtFull")} accentBorder="border-l-amber-400">
              <CwvMiniChart
                data={chart.labels.map((label, i) => ({ date: label, value: (tbt as (number | null)[])[i] ?? null }))}
                label={t("seo.metric.tbt")}
                color="#f59e0b"
                thresholds={[200, 600]}
                unit="ms"
              />
            </ChartCard>
          </div>

          {/* Action Tips */}
          {latestPerf != null && latestPerf >= 0.9 ? (
            <ActionTip title={t("actionTip.seoExcellent")} severity="success" />
          ) : latestPerf != null && latestPerf < 0.5 ? (
            <ActionTip title={t("actionTip.seoPoor")} severity="danger" />
          ) : latestPerf != null ? (
            <ActionTip title={t("actionTip.seoWarning")} severity="warning" />
          ) : null}
          {latestLcp != null && latestLcp > 4 ? (
            <ActionTip title={t("actionTip.lcpSlow")} severity="warning" />
          ) : null}
          {latestCls != null && latestCls > 0.25 ? (
            <ActionTip title={t("actionTip.clsHigh")} severity="warning" />
          ) : null}
        </div>
      )}
    </div>
  );
}
