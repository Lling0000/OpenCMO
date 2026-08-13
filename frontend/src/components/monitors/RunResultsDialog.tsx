import { useState } from "react";
import {
  X,
  TriangleAlert,
  Lightbulb,
  Loader2,
  CheckCircle,
  XCircle,
  Pencil,
  Check,
} from "lucide-react";
import { useTaskArtifacts, useTaskFindings, useTaskRecommendations } from "../../hooks/useTasks";
import { useI18n } from "../../i18n";
import type { TranslationKey } from "../../i18n";
import { apiJson } from "../../api/client";
import type { MonitorRun } from "../../types";
import { getSeverityLabelKey } from "../../utils/severity";
import { utcDate } from "../../utils/time";

const SEVERITY_STYLE: Record<string, string> = {
  critical: "bg-rose-50 text-rose-700 ring-rose-200",
  high: "bg-orange-50 text-orange-700 ring-orange-200",
  medium: "bg-amber-50 text-amber-700 ring-amber-200",
  low: "bg-slate-50 text-slate-600 ring-slate-200",
};

const PRIORITY_STYLE: Record<string, string> = {
  high: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  medium: "bg-sky-50 text-sky-700 ring-sky-200",
  low: "bg-slate-50 text-slate-600 ring-slate-200",
};

const QUALITY_STYLE: Record<string, string> = {
  reliable: "border-emerald-200 bg-emerald-50/80 text-emerald-900",
  partial: "border-amber-200 bg-amber-50/80 text-amber-900",
  limited: "border-rose-200 bg-rose-50/80 text-rose-900",
};

const KIND_STYLE: Record<string, string> = {
  source_limit: "bg-amber-100 text-amber-700 ring-amber-200",
  fallback: "bg-sky-100 text-sky-700 ring-sky-200",
  coverage_gap: "bg-rose-100 text-rose-700 ring-rose-200",
  task_error: "bg-rose-100 text-rose-700 ring-rose-200",
};

const STAGE_LABEL_KEYS: Record<string, TranslationKey> = {
  context_build: "analysis.stageContextBuild",
  signal_collect: "analysis.stageSignalCollect",
  signal_normalize: "analysis.stageSignalNormalize",
  domain_review: "analysis.stageDomainReview",
  strategy_synthesis: "analysis.stageStrategySynthesis",
  persist_publish: "analysis.stagePersistPublish",
};

export function RunResultsDialog({
  run,
  url,
  onClose,
}: {
  run: MonitorRun;
  url: string;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const isDone = run.status === "completed" || run.status === "failed";
  const { data: artifacts } = useTaskArtifacts(run.task_id, isDone);
  const { data: findings = [], isLoading: loadingFindings } = useTaskFindings(run.task_id, isDone);
  const { data: recommendations = [], isLoading: loadingRecs } = useTaskRecommendations(run.task_id, isDone);

  const [notes, setNotes] = useState(run.summary ?? "");
  const [editingNotes, setEditingNotes] = useState(false);
  const [savingNotes, setSavingNotes] = useState(false);

  const saveNotes = async () => {
    setSavingNotes(true);
    try {
      await apiJson(`/tasks/${run.task_id}/notes`, {
        method: "PATCH",
        body: JSON.stringify({ notes }),
        headers: { "Content-Type": "application/json" },
      });
      setEditingNotes(false);
    } finally {
      setSavingNotes(false);
    }
  };

  const isLoading = loadingFindings || loadingRecs;
  const quality = artifacts?.quality;
  const watchouts = artifacts?.watchouts ?? [];
  const topAction = quality?.blocking ? watchouts.find((item) => item.blocking)?.resolution : artifacts?.brief?.top_recommendations?.[0]?.summary;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
      <div className="flex h-[82vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {t("analysis.title")}
            </h2>
            <p className="mt-0.5 max-w-xl truncate text-xs text-slate-400">{url}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-4">
          {/* Status + time */}
          <div className="flex items-center gap-3 text-sm">
            {run.status === "completed" ? (
              <CheckCircle size={16} className="text-emerald-500" />
            ) : run.status === "failed" ? (
              <XCircle size={16} className="text-rose-500" />
            ) : (
              <Loader2 size={16} className="animate-spin text-indigo-400" />
            )}
            <span className="text-slate-600">
              {run.completed_at
                ? utcDate(run.completed_at).toLocaleString()
                : utcDate(run.created_at).toLocaleString()}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase text-slate-500">
              {run.job_type}
            </span>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 py-8 text-slate-400 text-sm justify-center">
              <Loader2 size={18} className="animate-spin" />
              Loading results…
            </div>
          ) : (
            <>
              {quality ? (
                <section className={`rounded-2xl border p-4 ${QUALITY_STYLE[quality.level] ?? QUALITY_STYLE.reliable}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold">{quality.headline}</p>
                    <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold uppercase ring-1 ring-inset ring-slate-200">
                      {quality.level === "reliable" ? t("analysis.qualityReliable") : quality.level === "partial" ? t("analysis.qualityPartial") : t("analysis.qualityLimited")}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed">{quality.summary}</p>
                  {topAction ? (
                    <p className="mt-3 text-sm leading-relaxed">
                      <span className="font-semibold">{t("analysis.nextBestAction")}: </span>
                      {topAction}
                    </p>
                  ) : null}
                </section>
              ) : null}

              {watchouts.length > 0 ? (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <TriangleAlert size={14} className="text-amber-500" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      {t("analysis.coverageWatchouts")}
                    </h3>
                  </div>
                  <div className="space-y-3">
                    {watchouts.map((watchout, index) => (
                      <div
                        key={`${watchout.stage}-${watchout.code}-${index}`}
                        className="rounded-xl border border-slate-200 bg-white p-4"
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            {(() => {
                              const stageLabelKey = STAGE_LABEL_KEYS[watchout.stage];
                              return stageLabelKey ? t(stageLabelKey) : watchout.stage;
                            })()}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ring-1 ring-inset ${
                              KIND_STYLE[watchout.kind] ?? KIND_STYLE.coverage_gap
                            }`}
                          >
                            {watchout.kind === "source_limit"
                              ? t("analysis.watchoutSourceLimit")
                              : watchout.kind === "fallback"
                                ? t("analysis.watchoutFallback")
                                : watchout.kind === "coverage_gap"
                                  ? t("analysis.watchoutCoverageGap")
                                  : t("analysis.watchoutTaskError")}
                          </span>
                          {watchout.blocking ? (
                            <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-rose-700 ring-1 ring-inset ring-rose-200">
                              {t("analysis.blocking")}
                            </span>
                          ) : null}
                        </div>
                        <p className="text-sm font-semibold text-slate-900">{watchout.title}</p>
                        <p className="mt-1 text-sm leading-relaxed text-slate-600">{watchout.summary}</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-700">{watchout.resolution}</p>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              {/* Findings */}
              {findings.length > 0 && (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <TriangleAlert size={14} className="text-rose-500" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      {t("analysis.keyFindings")} ({findings.length})
                    </h3>
                  </div>
                  {quality && quality.level !== "reliable" ? (
                    <p className="mb-3 text-sm leading-relaxed text-slate-600">
                      {t("analysis.resultConfidenceNote")}
                    </p>
                  ) : null}
                  <div className="space-y-3">
                    {findings.map((f, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-slate-200 bg-white p-4"
                      >
                        <div className="mb-2 flex items-center gap-2">
                          <span className="text-xs font-semibold uppercase text-slate-400">
                            {f.domain}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ring-1 ring-inset ${
                              SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.low
                            }`}
                          >
                            {t(getSeverityLabelKey(f.severity))}
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-slate-900">{f.title}</p>
                        <p className="mt-1 text-sm leading-relaxed text-slate-600">{f.summary}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Recommendations */}
              {recommendations.length > 0 && (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <Lightbulb size={14} className="text-amber-500" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      {t("analysis.recommendedActions")} ({recommendations.length})
                    </h3>
                  </div>
                  {quality && quality.level !== "reliable" ? (
                    <p className="mb-3 text-sm leading-relaxed text-slate-600">
                      {t("analysis.resultConfidenceNote")}
                    </p>
                  ) : null}
                  <div className="space-y-3">
                    {recommendations.map((r, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4"
                      >
                        <div className="mb-2 flex items-center gap-2">
                          <span className="text-xs font-semibold uppercase text-indigo-400">
                            {r.owner_type}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ring-1 ring-inset ${
                              PRIORITY_STYLE[r.priority] ?? PRIORITY_STYLE.low
                            }`}
                          >
                            {r.priority}
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-slate-900">{r.title}</p>
                        <p className="mt-1 text-sm leading-relaxed text-slate-600">{r.summary}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {findings.length === 0 && recommendations.length === 0 && (
                <p className="py-8 text-center text-sm text-slate-400">
                  No findings recorded for this run.
                </p>
              )}

              {/* Editable notes */}
              <section>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">Notes</h3>
                  {!editingNotes ? (
                    <button
                      onClick={() => setEditingNotes(true)}
                      className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    >
                      <Pencil size={12} />
                      Edit
                    </button>
                  ) : (
                    <button
                      onClick={saveNotes}
                      disabled={savingNotes}
                      className="flex items-center gap-1 rounded-lg bg-indigo-50 px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {savingNotes ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                      Save
                    </button>
                  )}
                </div>
                {editingNotes ? (
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={4}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
                    placeholder="Add notes about this scan run…"
                  />
                ) : (
                  <div className="min-h-[60px] rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                    {notes || <span className="text-slate-400 italic">No notes yet. Click Edit to add.</span>}
                  </div>
                )}
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-slate-100 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
          >
            {t("analysis.close")}
          </button>
        </div>
      </div>
    </div>
  );
}
