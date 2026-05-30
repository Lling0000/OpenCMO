import { useEffect, useState } from "react";
import { Play, XCircle, Loader2, Eye, RotateCw } from "lucide-react";
import { useRunMonitor } from "../../hooks/useMonitors";
import { useTaskPoll } from "../../hooks/useTasks";
import { useQueryClient } from "@tanstack/react-query";
import { useI18n } from "../../i18n";

export function RunScanButton({
  monitorId,
  projectId,
  onTaskCreated,
  onViewResults,
}: {
  monitorId: number;
  projectId: number;
  onTaskCreated?: (taskId: string) => void;
  onViewResults?: (taskId: string) => void;
}) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const runMonitor = useRunMonitor();
  const { data: task } = useTaskPoll(taskId);
  const qc = useQueryClient();
  const { locale, t } = useI18n();

  const status = task?.status;

  useEffect(() => {
    if (!taskId || !status) return;

    qc.invalidateQueries({ queryKey: ["monitors"] });
    qc.invalidateQueries({ queryKey: ["monitor-runs", monitorId] });

    if (status === "completed") {
      qc.invalidateQueries({ queryKey: ["project-summary", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    }
  }, [monitorId, projectId, qc, status, taskId]);

  const handleRun = async () => {
    try {
      const record = await runMonitor.mutateAsync({ id: monitorId, locale });
      setTaskId(record.task_id);
      onTaskCreated?.(record.task_id);
    } catch {
      // 409 or other error handled by mutation
    }
  };

  const handleViewResults = () => {
    if (taskId && onViewResults) {
      onViewResults(taskId);
    }
  };

  if (status === "running" || status === "pending") {
    return (
      <span className="flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600">
        <Loader2 size={14} className="animate-spin" />
        {t("runScan.running")}
      </span>
    );
  }

  if (status === "completed") {
    return (
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleViewResults}
          disabled={!taskId || !onViewResults}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Eye size={13} />
          {t("runScan.viewResults")}
        </button>
        <button
          type="button"
          onClick={handleRun}
          disabled={runMonitor.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 transition-colors hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCw size={13} />
          {t("runScan.rerun")}
        </button>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex items-center gap-2">
        <span
          className="flex items-center gap-1.5 rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-600"
          title={task?.error ?? ""}
        >
          <XCircle size={14} />
          {t("runScan.failed")}
        </span>
        <button
          type="button"
          onClick={handleRun}
          disabled={runMonitor.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 transition-colors hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCw size={13} />
          {t("runScan.rerun")}
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={handleRun}
      disabled={runMonitor.isPending}
      className="flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Play size={12} />
      {t("runScan.run")}
    </button>
  );
}
