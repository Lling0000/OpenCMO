import { useState } from "react";
import { Play, Pause, RotateCcw, Loader2, Zap } from "lucide-react";
import { useExpansionProgress, useExpansionStatus, useStartExpansion, usePauseExpansion, useResetExpansion } from "../../hooks/useGraphData";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { useI18n } from "../../i18n";

export function ExpansionControls({ projectId }: { projectId: number }) {
  const { data: expansion } = useExpansionStatus(projectId);
  const startMut = useStartExpansion(projectId);
  const pauseMut = usePauseExpansion(projectId);
  const resetMut = useResetExpansion(projectId);
  const [showReset, setShowReset] = useState(false);
  const { t } = useI18n();

  const desired = expansion?.desired_state ?? "idle";
  const runtime = expansion?.runtime_state ?? "idle";
  const wave = expansion?.current_wave ?? 0;
  const discovered = expansion?.nodes_discovered ?? 0;
  const explored = expansion?.nodes_explored ?? 0;

  const isRunning = runtime === "running";
  const isPaused = runtime === "paused" || desired === "paused";
  const isInterrupted = runtime === "interrupted";
  const isIdle = runtime === "idle" && desired === "idle";
  const { data: progress } = useExpansionProgress(projectId, isRunning || wave > 0);
  const latestProgress = progress?.progress?.filter((item) => item.summary).at(-1);

  return (
    <div className="rounded-2xl border border-zinc-200/60 bg-white/80 px-5 py-3 shadow-sm backdrop-blur-sm">
      <div className="flex flex-wrap items-center gap-3">
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        {isRunning ? (
          <Zap className="h-4 w-4 text-purple-500 animate-pulse" />
        ) : (
          <Zap className="h-4 w-4 text-zinc-300" />
        )}
        <span className="text-sm font-semibold text-zinc-700">
          {t("graph.expansion")}
        </span>
      </div>

      <div className="h-5 w-px bg-zinc-200" />

      {/* Action buttons */}
      {(isIdle || isPaused || isInterrupted) && (
        <button
          onClick={() => startMut.mutate()}
          disabled={startMut.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-purple-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-purple-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {startMut.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {isIdle ? t("graph.startExploring") : t("graph.resume")}
        </button>
      )}

      {isRunning && desired === "running" && (
        <button
          onClick={() => pauseMut.mutate()}
          disabled={pauseMut.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-semibold text-zinc-700 transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pauseMut.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Pause className="h-3.5 w-3.5" />
          )}
          {t("graph.pause")}
        </button>
      )}

      {/* Pausing indicator */}
      {isRunning && desired === "paused" && (
        <span className="flex items-center gap-1.5 text-xs text-amber-600">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {t("graph.pausingHint")}
        </span>
      )}

      {(isPaused || isInterrupted || (isIdle && wave > 0)) && wave > 0 && (
        <button
          onClick={() => setShowReset(true)}
          disabled={resetMut.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-semibold text-zinc-700 transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t("graph.reset")}
        </button>
      )}

      <div className="h-5 w-px bg-zinc-200" />

      {/* Stats */}
      {wave > 0 && (
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>{t("graph.wave").replace("{{n}}", String(wave))}</span>
          <span>{t("graph.discovered").replace("{{count}}", String(discovered))}</span>
          <span>{t("graph.explored").replace("{{count}}", String(explored))}</span>
        </div>
      )}

      {isRunning && (
        <Loader2 className="ml-auto h-4 w-4 animate-spin text-purple-400" />
      )}

      {isInterrupted && (
        <span className="ml-auto text-xs text-amber-600 font-medium">
          {t("graph.interrupted")}
        </span>
      )}
      </div>

      {(latestProgress || wave > 0) && (
        <div className="mt-3 rounded-xl bg-zinc-50 px-3 py-2 text-xs leading-5 text-zinc-600">
          <span className="font-semibold text-zinc-800">{t("graph.expansionFocus")}</span>{" "}
          {latestProgress?.summary ?? t("graph.expansionIdleSummary", { discovered, explored })}
        </div>
      )}

      {showReset && (
        <ConfirmDialog
          title={t("graph.reset")}
          message={t("graph.resetConfirm")}
          onConfirm={() => { resetMut.mutate(); setShowReset(false); }}
          onCancel={() => setShowReset(false)}
        />
      )}
    </div>
  );
}
