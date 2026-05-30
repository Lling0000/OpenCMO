import { useEffect, useState } from "react";
import { Eye, Loader2, PlusCircle } from "lucide-react";
import { useParams } from "react-router";
import { useMonitors, useDeleteMonitor, useCreateMonitor } from "../hooks/useMonitors";
import { useProjectSummary } from "../hooks/useProject";
import { useTaskPoll } from "../hooks/useTasks";
import { MonitorList } from "../components/monitors/MonitorList";
import { MonitorForm } from "../components/monitors/MonitorForm";
import { AnalysisDialog } from "../components/monitors/AnalysisDialog";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { ProjectHeaderSkeleton, ListRowSkeleton, SkeletonFrame } from "../components/common/Skeleton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { useToast } from "../components/common/Toast";
import { useI18n } from "../i18n";

export function ProjectMonitorsPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { data, isLoading: projectLoading, error } = useProjectSummary(projectId);
  const { data: allMonitors, isLoading: monitorsLoading } = useMonitors();
  const deleteMonitor = useDeleteMonitor();
  const createMonitor = useCreateMonitor();
  const { t } = useI18n();
  const toast = useToast();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTaskUrl, setSelectedTaskUrl] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: taskData } = useTaskPoll(selectedTaskId);
  const taskDone = taskData?.status === "completed" || taskData?.status === "failed";

  const monitors = allMonitors?.filter((m) => m.project_id === projectId) ?? [];

  useEffect(() => {
    if (!taskDone || !selectedTaskId || dialogOpen) return;
    const timeoutId = window.setTimeout(() => {
      setSelectedTaskId(null);
      setSelectedTaskUrl(null);
    }, 3000);
    return () => window.clearTimeout(timeoutId);
  }, [dialogOpen, selectedTaskId, taskDone]);

  if (projectLoading || monitorsLoading) {
    return (
      <SkeletonFrame className="space-y-5">
        <ProjectHeaderSkeleton />
        <ListRowSkeleton rows={3} />
      </SkeletonFrame>
    );
  }
  if (error || !data) return <ErrorAlert message={t("common.projectNotFound")} />;

  const handleTaskCreated = (taskId: string, url: string) => {
    setSelectedTaskId(taskId);
    setSelectedTaskUrl(url);
    setDialogOpen(true);
  };

  const handleCreateMonitor = async (payload: { url: string; cron_expr: string }) => {
    try {
      const result = await createMonitor.mutateAsync({
        ...payload,
        locale: monitors[0]?.locale,
      });
      toast.success(t("toast.monitorAdded"));
      if (result.task_id) {
        toast.info(t("toast.scanStarted"));
        handleTaskCreated(result.task_id, payload.url);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
      throw err;
    }
  };

  return (
    <div>
      <ProjectHeader project={data.project} isPaused={data.is_paused} />
      <ProjectTabs projectId={projectId} />

      <div className="space-y-4">
        {monitors.length > 0 ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-900">{t("monitors.addAnotherTitle")}</h2>
                <p className="mt-1 text-sm text-slate-500">{t("monitors.addAnotherDesc")}</p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                <PlusCircle size={14} />
                {t("monitors.newMonitor")}
              </div>
            </div>
          </div>
        ) : null}
        {selectedTaskId && selectedTaskUrl && !dialogOpen && !taskDone && (
          <button
            onClick={() => setDialogOpen(true)}
            className="flex w-full items-center gap-3 rounded-xl bg-indigo-50 px-4 py-3 text-sm text-indigo-700 ring-1 ring-inset ring-indigo-200 transition-colors hover:bg-indigo-100"
          >
            <Loader2 size={16} className="animate-spin" />
            <span className="flex-1 truncate text-left">
              {t("monitors.aiAnalyzing")}: {selectedTaskUrl}
            </span>
            <span className="flex items-center gap-1 text-xs font-medium">
              <Eye size={14} />
              {t("monitors.viewDetails")}
            </span>
          </button>
        )}
        {monitors.length === 0 ? (
          <div className="space-y-4">
            <EmptyState
              title={t("monitors.noMonitors")}
              description={t("monitors.noMonitorsDesc")}
            />
            <MonitorForm
              onSubmit={handleCreateMonitor}
              isLoading={createMonitor.isPending}
              initialUrl={data.project.url}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <MonitorForm
              onSubmit={handleCreateMonitor}
              isLoading={createMonitor.isPending}
              initialUrl={data.project.url}
            />
            <MonitorList
              monitors={monitors}
              onDelete={(id) =>
                deleteMonitor.mutate(id, {
                  onSuccess: () => toast.info(t("toast.monitorRemoved")),
                  onError: (err) =>
                    toast.error(err instanceof Error ? err.message : String(err)),
                })
              }
              onTaskCreated={handleTaskCreated}
            />
          </div>
        )}
      </div>

      {selectedTaskId && dialogOpen && (
        <AnalysisDialog
          taskId={selectedTaskId}
          url={selectedTaskUrl ?? ""}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </div>
  );
}
