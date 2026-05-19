import { useState } from "react";
import { useParams } from "react-router";
import { ExternalLink, FileText, Hash, PauseCircle, PlayCircle, Users } from "lucide-react";
import { useProjectSummary } from "../hooks/useProject";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { ScorePanel } from "../components/project/ScorePanel";
import { ScanHistoryTable } from "../components/project/ScanHistoryTable";
import { CampaignTimeline } from "../components/project/CampaignTimeline";
import { ActionFeed } from "../components/project/ActionFeed";
import { InsightBanner } from "../components/dashboard/InsightBanner";
import { useI18n } from "../i18n";
import { useSetProjectPause } from "../hooks/useProject";
import { BlogGenerateButton } from "../components/project/BlogGenerateButton";
import { AgentActionQueue } from "../components/project/AgentActionQueue";
import { ProjectChatPanel } from "../components/project/ProjectChatPanel";
import { ProjectConsoleStatus } from "../components/project/ProjectConsoleStatus";

function normalizeHost(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function ProjectPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data, isLoading, error } = useProjectSummary(projectId);
  const { t } = useI18n();
  const setPause = useSetProjectPause();
  const [chatPrompt, setChatPrompt] = useState<string | undefined>();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error.message} />;
  if (!data) return <ErrorAlert message={t("common.projectNotFound")} />;

  const {
    project,
    latest,
    previous,
    latest_monitoring,
    latest_reports,
    is_paused,
    keyword_count,
    competitor_count,
    pending_approvals,
    blog_drafts_count,
  } = data;
  const categoryLabel = project.category === "auto" ? t("project.categoryAuto") : project.category;
  const host = normalizeHost(project.url);
  const keywordCount = keyword_count ?? 0;
  const competitorCount = competitor_count ?? 0;
  const pendingApprovals = pending_approvals ?? 0;
  const blogDraftsCount = blog_drafts_count ?? 0;
  const handleTogglePause = () => {
    setPause.mutate({ id: project.id, pause: !is_paused });
  };

  return (
    <div className="space-y-4">
      <ProjectConsoleStatus
        project={project}
        latest={latest}
        latestMonitoring={latest_monitoring}
        isPaused={is_paused}
        pendingApprovals={pendingApprovals}
      />
      <ProjectTabs projectId={projectId} />

      <div className="grid gap-4 xl:grid-cols-[minmax(230px,0.72fr)_minmax(0,1.2fr)_minmax(340px,0.95fr)_minmax(340px,0.95fr)]">
        <aside className="min-w-0 space-y-4">
          <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              {t("commandCenter.company.title")}
            </p>
            <h1 className="mt-2 break-words text-2xl font-semibold tracking-tight text-slate-950">
              {project.brand_name}
            </h1>
            <a
              href={project.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex max-w-full items-center gap-1.5 text-sm font-medium text-slate-500 transition-colors hover:text-slate-900"
            >
              <span className="truncate">{host}</span>
              <ExternalLink size={14} className="shrink-0" />
            </a>

            <div className="mt-4 space-y-2 text-sm">
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  {t("commandCenter.company.category")}
                </p>
                <p className="mt-1 font-medium text-slate-800">{categoryLabel}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    {t("commandCenter.company.competitors")}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 font-semibold text-slate-900">
                    <Users size={14} className="text-slate-400" />
                    {competitorCount}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    {t("commandCenter.company.keywords")}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 font-semibold text-slate-900">
                    <Hash size={14} className="text-slate-400" />
                    {keywordCount}
                  </p>
                </div>
              </div>
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  {t("commandCenter.company.review")}
                </p>
                <p className="mt-1 flex items-center gap-1.5 font-semibold text-slate-900">
                  <FileText size={14} className="text-slate-400" />
                  {t("commandCenter.company.reviewValue", {
                    approvals: pendingApprovals,
                    drafts: blogDraftsCount,
                  })}
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleTogglePause}
                disabled={setPause.isPending}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                  is_paused
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                    : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                }`}
              >
                {is_paused ? <PlayCircle size={14} /> : <PauseCircle size={14} />}
                {is_paused ? t("projectHeader.resume") : t("projectHeader.pause")}
              </button>
              <BlogGenerateButton projectId={projectId} />
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              {t("commandCenter.company.workflowTitle")}
            </p>
            <div className="mt-3 space-y-2 text-sm text-slate-600">
              <p>{t("commandCenter.company.workflowObserve")}</p>
              <p>{t("commandCenter.company.workflowDecide")}</p>
              <p>{t("commandCenter.company.workflowShip")}</p>
            </div>
          </section>
        </aside>

        <section className="min-w-0 space-y-4">
          <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm">
            <div className="mb-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                {t("commandCenter.analytics.title")}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {t("commandCenter.analytics.subtitle")}
              </p>
            </div>
            <ScorePanel
              latest={latest}
              previous={previous}
              latestMonitoring={latest_monitoring}
              projectId={projectId}
              compact
            />
          </section>

          <InsightBanner projectId={projectId} />

          <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm">
            <CampaignTimeline projectId={projectId} />
          </section>
        </section>

        <section className="min-w-0 space-y-4">
          <AgentActionQueue
            projectId={projectId}
            latest={latest}
            latestMonitoring={latest_monitoring}
            latestReports={latest_reports}
            pendingApprovals={pendingApprovals}
            blogDraftsCount={blogDraftsCount}
            competitorCount={competitorCount}
            keywordCount={keywordCount}
            onDiscuss={setChatPrompt}
          />

          <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm">
            <ActionFeed projectId={projectId} />
          </section>
        </section>

        <aside className="min-h-[640px] min-w-0 xl:sticky xl:top-20 xl:h-[calc(100vh-7rem)]">
          <ProjectChatPanel
            projectId={projectId}
            projectName={project.brand_name}
            initialPrompt={chatPrompt}
            onPromptConsumed={() => setChatPrompt(undefined)}
          />
        </aside>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.45fr)]">
        <details className="group rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm">
          <summary className="cursor-pointer text-sm font-semibold text-slate-500 transition hover:text-slate-700">
            {t("commandCenter.scanHistory")}
          </summary>
          <div className="mt-4">
            <ScanHistoryTable latest={latest} />
          </div>
        </details>

        <section className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 text-sm leading-6 text-slate-600 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {t("commandCenter.reviewGuardrail.title")}
          </p>
          <p className="mt-2">{t("commandCenter.reviewGuardrail.body")}</p>
        </section>
      </div>
    </div>
  );
}
