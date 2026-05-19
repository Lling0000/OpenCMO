import { useState } from "react";
import { Info } from "lucide-react";
import type { LatestScans, MonitoringSummary, ProjectSummary } from "../../types";
import { useGeoChart } from "../../hooks/useGeoData";
import { useSeoChart } from "../../hooks/useSeoData";
import { useI18n } from "../../i18n";
import {
  ScoreExplanationDrawer,
  type ScoreExplanationKind,
} from "./ScoreExplanationDrawer";

const TONES = {
  green: "border-emerald-200 bg-emerald-50/60 text-emerald-700",
  blue: "border-sky-200 bg-sky-50/60 text-sky-700",
  purple: "border-violet-200 bg-violet-50/60 text-violet-700",
  amber: "border-amber-200 bg-amber-50/60 text-amber-700",
  red: "border-rose-200 bg-rose-50/60 text-rose-700",
  gray: "border-slate-200 bg-slate-50/80 text-slate-500",
};

function normalizePercent(value: number | null | undefined): number | null {
  if (value == null) return null;
  return Math.round(value <= 1 ? value * 100 : value);
}

function getPointDelta(current: number | null, previous: number | null): number | null {
  if (current == null || previous == null) return null;
  return current - previous;
}

function signed(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

function ScoreMetricCard({
  label,
  value,
  tone,
  subtext,
  onExplain,
  explainLabel,
}: {
  label: string;
  value: string;
  tone: keyof typeof TONES;
  subtext?: string;
  onExplain?: () => void;
  explainLabel?: string;
}) {
  return (
    <article className={`min-w-0 rounded-2xl border p-4 ${TONES[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {label}
        </p>
        {onExplain ? (
          <button
            type="button"
            title={explainLabel}
            aria-label={explainLabel}
            onClick={onExplain}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-current/20 bg-white/70 transition hover:bg-white"
          >
            <Info size={14} />
          </button>
        ) : null}
      </div>
      <p className="mt-3 break-words text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      {subtext ? <p className="mt-2 text-xs leading-5 text-slate-600">{subtext}</p> : null}
    </article>
  );
}

export function ScorePanel({
  latest,
  previous,
  latestMonitoring,
  projectId,
  compact = false,
}: {
  latest: LatestScans;
  previous?: ProjectSummary["previous"];
  latestMonitoring?: MonitoringSummary | null;
  projectId?: number;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const [selectedKind, setSelectedKind] = useState<ScoreExplanationKind | null>(null);
  const hasProjectId = projectId != null && Number.isFinite(projectId);
  const { data: seoChart } = useSeoChart(projectId ?? 0, hasProjectId);
  const { data: geoChart } = useGeoChart(projectId ?? 0, hasProjectId);

  const seoScore = normalizePercent(latest.seo?.score);
  const previousSeoScore = normalizePercent(previous?.seo?.score);
  const seoDelta = getPointDelta(seoScore, previousSeoScore);
  const geoScore = latest.geo?.score ?? null;
  const previousGeoScore = previous?.geo?.score ?? null;
  const geoDelta = getPointDelta(geoScore, previousGeoScore);

  const deltaText = (delta: number | null, fallback: string) =>
    delta != null ? t("score.vsPrevious", { value: signed(delta) }) : fallback;

  const explainLabel = t("score.explain");

  return (
    <>
      <div className={compact ? "grid gap-3" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"}>
        <ScoreMetricCard
          label={t("score.seoScore")}
          value={seoScore != null ? `${seoScore}%` : t("common.noData")}
          tone={seoScore != null && seoScore >= 80 ? "green" : seoScore != null ? "amber" : "gray"}
          subtext={seoScore != null ? deltaText(seoDelta, t("score.seoFormulaShort")) : t("score.dataUnavailable")}
          onExplain={() => setSelectedKind("seo")}
          explainLabel={explainLabel}
        />
        <ScoreMetricCard
          label={t("score.geoScore")}
          value={geoScore != null ? `${geoScore}/100` : t("common.noData")}
          tone={geoScore != null && geoScore >= 60 ? "green" : geoScore != null ? "amber" : "gray"}
          subtext={geoScore != null ? deltaText(geoDelta, t("score.geoFormulaShort")) : t("score.dataUnavailable")}
          onExplain={() => setSelectedKind("geo")}
          explainLabel={explainLabel}
        />
        <ScoreMetricCard
          label={t("score.communityHits")}
          value={latest.community?.total_hits != null ? String(latest.community.total_hits) : t("common.noData")}
          tone={latest.community?.total_hits ? "blue" : "gray"}
        />
        <ScoreMetricCard
          label={t("score.serpKeywords")}
          value={latest.serp?.length ? t("score.tracked", { count: latest.serp.length }) : t("common.noData")}
          tone={latest.serp?.length ? "purple" : "gray"}
        />
        <ScoreMetricCard
          label={t("score.findings")}
          value={latestMonitoring?.findings_count != null ? String(latestMonitoring.findings_count) : t("common.noData")}
          tone={(latestMonitoring?.findings_count ?? 0) > 0 ? "red" : "gray"}
        />
        <ScoreMetricCard
          label={t("score.recommendations")}
          value={
            latestMonitoring?.recommendations_count != null
              ? String(latestMonitoring.recommendations_count)
              : t("common.noData")
          }
          tone={(latestMonitoring?.recommendations_count ?? 0) > 0 ? "blue" : "gray"}
        />
      </div>

      <ScoreExplanationDrawer
        open={selectedKind != null}
        kind={selectedKind}
        latest={latest}
        previous={previous}
        seoChart={seoChart}
        geoChart={geoChart}
        onClose={() => setSelectedKind(null)}
      />
    </>
  );
}
