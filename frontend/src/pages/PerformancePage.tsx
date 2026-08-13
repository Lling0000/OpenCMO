import { useState } from "react";
import { useParams } from "react-router";
import {
  BarChart3, ThumbsUp, MessageCircle, Repeat2, Eye,
  RefreshCw, Plus, Trash2, ExternalLink, Globe,
} from "lucide-react";
import { usePerformance, useRefreshMetrics, useAddManualTracking, useDeleteManualTracking } from "../hooks/usePerformance";
import { useProjectSummary } from "../hooks/useProject";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { useI18n } from "../i18n";
import type { TranslationKey } from "../i18n";
import { utcDate } from "../utils/time";

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-900">{value.toLocaleString()}</p>
          <p className="text-xs text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

const PLATFORM_COLORS: Record<string, string> = {
  reddit: "bg-orange-500",
  twitter: "bg-sky-500",
  blog: "bg-violet-500",
  other: "bg-slate-500",
};

const PLATFORM_LABEL_KEYS: Record<string, TranslationKey> = {
  reddit: "perf.platformReddit",
  twitter: "perf.platformTwitter",
  blog: "perf.platformBlog",
  other: "perf.platformOther",
};

function enumFallback(value: string) {
  return value.replace(/_/g, " ");
}

export function PerformancePage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data: projectSummary, isLoading: loadingProject } = useProjectSummary(projectId);
  const { data, isLoading, error } = usePerformance(projectId);
  const refreshMutation = useRefreshMetrics();
  const addManual = useAddManualTracking(projectId);
  const deleteManual = useDeleteManualTracking(projectId);
  const { t } = useI18n();

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ platform: "other", url: "", title: "", notes: "" });

  if (loadingProject || isLoading) return <LoadingSpinner />;
  if (!projectSummary) return <ErrorAlert message={t("common.projectNotFound")} />;
  if (error) return <ErrorAlert message={error.message} />;
  if (!data) return null;

  const { summary, approvals, manual } = data;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <ProjectHeader project={projectSummary.project} />
      <ProjectTabs projectId={projectId} />
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
            {t("perf.title")}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {t("perf.subtitle")}
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:bg-slate-800 active:scale-95"
        >
          <Plus size={16} />
          {t("perf.trackUrl")}
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4 mb-8 sm:grid-cols-4">
        <StatCard icon={BarChart3} label={t("perf.totalPublished")} value={summary.total_published} color="bg-violet-500" />
        <StatCard icon={ThumbsUp} label={t("perf.totalLikes")} value={summary.total_likes} color="bg-rose-500" />
        <StatCard icon={MessageCircle} label={t("perf.totalComments")} value={summary.total_comments} color="bg-blue-500" />
        <StatCard icon={Repeat2} label={t("perf.totalShares")} value={summary.total_retweets} color="bg-emerald-500" />
      </div>

      {/* Manual tracking form */}
      {showForm && (
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">{t("perf.trackExternal")}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <select
              value={formData.platform}
              onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="reddit">{t("perf.platformReddit")}</option>
              <option value="twitter">{t("perf.platformTwitter")}</option>
              <option value="blog">{t("perf.platformBlog")}</option>
              <option value="other">{t("perf.platformOther")}</option>
            </select>
            <input
              type="url"
              placeholder="https://..."
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder={t("perf.titleOptional")}
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder={t("perf.notesOptional")}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="mt-3 flex gap-2 justify-end">
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              {t("common.cancel")}
            </button>
            <button
              disabled={!formData.url || addManual.isPending}
              onClick={() => {
                addManual.mutate(formData, {
                  onSuccess: () => {
                    setShowForm(false);
                    setFormData({ platform: "other", url: "", title: "", notes: "" });
                  },
                });
              }}
              className="rounded-lg bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {addManual.isPending ? t("perf.adding") : t("perf.add")}
            </button>
          </div>
        </div>
      )}

      {/* Published Content */}
      {approvals.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-4">
            {t("perf.publishedVia")}
          </h2>
          <div className="space-y-3">
            {approvals.map((item) => {
              const m = item.post_metrics || {};
              const hasMetrics = Object.keys(m).length > 0;
              return (
                <div
                  key={item.id}
                  className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm transition hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`inline-flex h-5 items-center rounded-md px-2 text-[10px] font-bold uppercase text-white ${PLATFORM_COLORS[item.channel] || "bg-slate-500"}`}>
                          {PLATFORM_LABEL_KEYS[item.channel] ? t(PLATFORM_LABEL_KEYS[item.channel]!) : enumFallback(item.channel)}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {item.decided_at ? utcDate(item.decided_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                      <h3 className="text-sm font-semibold text-slate-800 truncate">
                        {item.title || t("perf.untitled")}
                      </h3>
                      {hasMetrics && (
                        <div className="mt-2 flex gap-4">
                          {m.score != null && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <ThumbsUp size={12} /> {m.score}
                            </span>
                          )}
                          {m.like_count != null && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <ThumbsUp size={12} /> {m.like_count}
                            </span>
                          )}
                          {(m.num_comments != null || m.reply_count != null) && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <MessageCircle size={12} /> {m.num_comments ?? m.reply_count ?? 0}
                            </span>
                          )}
                          {m.retweet_count != null && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <Repeat2 size={12} /> {m.retweet_count}
                            </span>
                          )}
                          {m.impression_count != null && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <Eye size={12} /> {m.impression_count}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {Boolean(item.publish_result?.url) && (
                        <a
                          href={item.publish_result?.url as string}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        >
                          <ExternalLink size={14} />
                        </a>
                      )}
                      <button
                        onClick={() => refreshMutation.mutate(item.id)}
                        disabled={refreshMutation.isPending}
                        className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        title={t("perf.refreshMetrics")}
                      >
                        <RefreshCw size={14} className={refreshMutation.isPending ? "animate-spin" : ""} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Manual Tracking */}
      {manual.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-4">
            {t("perf.manuallyTracked")}
          </h2>
          <div className="space-y-3">
            {manual.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-flex h-5 items-center rounded-md px-2 text-[10px] font-bold uppercase text-white ${PLATFORM_COLORS[item.platform] || "bg-slate-500"}`}>
                        {item.platform}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-800 truncate">
                      {item.title || item.url}
                    </h3>
                    {item.notes && (
                      <p className="text-xs text-slate-500 mt-1">{item.notes}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    >
                      <ExternalLink size={14} />
                    </a>
                    <button
                      onClick={() => deleteManual.mutate(item.id)}
                      className="rounded-lg p-2 text-red-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {approvals.length === 0 && manual.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center">
          <Globe className="mx-auto h-12 w-12 text-slate-300" />
          <h3 className="mt-4 text-sm font-semibold text-slate-700">{t("perf.emptyTitle")}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {t("perf.emptyDesc")}
          </p>
        </div>
      )}
    </div>
  );
}
