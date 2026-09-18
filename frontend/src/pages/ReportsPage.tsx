import { useState, useMemo, type ElementType, type ReactNode } from "react";
import { useParams } from "react-router";
import ReactMarkdown from "../components/knowledge/KnowledgeMarkdown";
import { Bot, ChevronDown, ChevronRight, FileText, History, Info, Mail, RefreshCcw, User, Download } from "lucide-react";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { PipelineProgress } from "../components/project/PipelineProgress";
import { useProjectSummary } from "../hooks/useProject";
import { useLatestReports, useReports, useSendReport } from "../hooks/useReports";
import { apiJson } from "../api/client";
import type { ReportKind, ReportRecord } from "../types";
import { useI18n, type TranslationKey } from "../i18n";
import { downloadAsPDF } from "../utils/pdf";
import { useQueryClient } from "@tanstack/react-query";
import { utcDate } from "../utils/time";

type Snapshot = {
  bottomLine: string;
  actions: string[];
  confidence: TranslationKey;
  report: ReportRecord | null;
};

function formatStamp(value: string | null | undefined) {
  if (!value) return "N/A";
  return utcDate(value).toISOString().replace("T", " ").slice(0, 16);
}

function ReportCard({
  label,
  tooltip,
  icon,
  report,
  allowDownload,
  noReportText,
  lowSampleText,
  failedReportText,
}: {
  label: string;
  tooltip?: string;
  icon: ElementType;
  report: ReportRecord | null;
  allowDownload?: boolean;
  noReportText: string;
  lowSampleText: string;
  failedReportText: string;
}) {
  const Icon = icon;
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const isCompleted = Boolean(report && report.generation_status === "completed" && report.content.trim());
  const failureReason =
    typeof report?.meta?.llm_error === "string"
      ? report.meta.llm_error
      : typeof report?.meta?.pipeline_error === "string"
        ? report.meta.pipeline_error
        : null;

  // Preview: first 200 chars of content
  const preview = isCompleted && report ? report.content.slice(0, 200).replace(/\n+/g, " ") : "";

  return (
    <div className={`rounded-3xl border bg-white shadow-sm transition-all duration-200 ${
      isCompleted
        ? "border-slate-200 hover:border-slate-300 hover:shadow-md cursor-pointer"
        : "border-slate-200"
    }`}>
      {/* Clickable header */}
      <div
        className={`flex items-center justify-between gap-4 p-6 ${isCompleted ? "select-none" : ""}`}
        onClick={isCompleted ? () => setExpanded(!expanded) : undefined}
      >
        <div className="flex items-center gap-3">
          <div className={`rounded-full p-2.5 ${isCompleted ? "bg-indigo-50 text-indigo-600" : "bg-slate-100 text-slate-400"}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
              {label}
              {tooltip && (
                <span className="group relative" onClick={(e) => e.stopPropagation()}>
                  <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
                  <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-56 -translate-x-1/2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-normal leading-relaxed text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                    {tooltip}
                  </span>
                </span>
              )}
            </div>
            {report ? (
              <div className="text-xs text-slate-500">
                v{report.version} · {formatStamp(report.created_at)}
              </div>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isCompleted && report?.meta?.low_sample ? (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-700">
              {lowSampleText}
            </span>
          ) : null}
          {allowDownload && isCompleted && report ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                downloadAsPDF({
                  elementId: `report-content-${report.id}`,
                  filename: `OpenCMO-${label.replace(/\s+/g, "-")}-v${report.version}.pdf`,
                  title: `${label} (v${report.version})`,
                  missingElementMessage: t("reports.pdfUnavailable"),
                });
              }}
              className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none"
              title={t("reports.downloadPdf")}
            >
              <Download className="h-4 w-4" />
            </button>
          ) : null}
          {isCompleted ? (
            <div className={`rounded-full p-1.5 transition-colors ${expanded ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-400"}`}>
              <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
            </div>
          ) : null}
        </div>
      </div>

      {/* Collapsed preview */}
      {isCompleted && !expanded && preview ? (
        <div
          className="border-t border-slate-100 px-6 py-3 text-sm text-slate-500 cursor-pointer"
          onClick={() => setExpanded(true)}
        >
          <p className="line-clamp-2">{preview}...</p>
          <span className="mt-1 inline-block text-xs font-medium text-indigo-500">{t("reports.clickToExpand")}</span>
        </div>
      ) : null}

      {/* Full content stays mounted so PDF export also works while the card is collapsed. */}
      {isCompleted && report ? (
        <div className={expanded ? "border-t border-slate-100 px-6 pb-6 pt-4" : "hidden"}>
          <div id={`report-content-${report.id}`} className="premium-report">
            <ReactMarkdown>{report.content}</ReactMarkdown>
          </div>
        </div>
      ) : null}

      {/* Error state */}
      {report && !isCompleted ? (
        <div className="px-6 pb-6">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-700">
            <div className="font-semibold">{failedReportText}</div>
            {failureReason ? (
              <p className="mt-2 text-xs leading-relaxed text-rose-600">{failureReason}</p>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Empty state */}
      {!report ? (
        <div className="px-6 pb-6">
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
            {noReportText}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ReportHistory({
  title,
  reports,
  latestLabel,
  failedLabel,
}: {
  title: string;
  reports: ReportRecord[];
  latestLabel: string;
  failedLabel: string;
}) {
  const [openId, setOpenId] = useState<number | null>(null);

  if (!reports.length) return null;

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900">
        <History className="h-4 w-4 text-slate-500" />
        {title}
      </div>
      <div className="space-y-2">
        {reports.map((report) => {
          const isOpen = openId === report.id;
          return (
            <div
              key={report.id}
              className={`rounded-2xl border transition-all duration-200 ${
                isOpen
                  ? "border-indigo-200 bg-white shadow-sm"
                  : "border-slate-200 bg-slate-50/80 hover:border-slate-300 hover:bg-white hover:shadow-sm"
              }`}
            >
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : report.id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left cursor-pointer"
              >
                <ChevronRight className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-90 text-indigo-500" : ""}`} />
                <div className="flex flex-1 flex-wrap items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-900">
                    v{report.version} · {report.audience}
                  </span>
                  {report.is_latest ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-700">
                      {latestLabel}
                    </span>
                  ) : null}
                  {report.generation_status !== "completed" ? (
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-700">
                      {failedLabel}
                    </span>
                  ) : null}
                  <span className="text-slate-500">{formatStamp(report.created_at)}</span>
                </div>
              </button>
              {isOpen ? (
                <div className="border-t border-slate-100 px-4 pb-4 pt-3">
                  {report.generation_status === "completed" && report.content.trim() ? (
                    <div className="premium-report">
                      <ReactMarkdown>{report.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
                      {report.meta?.llm_error || report.meta?.pipeline_error || failedLabel}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function stripMarkdown(value: string): string {
  return value
    .replace(/!\[[^\]]*]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/^[#>*\-\d.\s]+/g, "")
    .replace(/\*\*|__|`/g, "")
    .trim();
}

function buildExecutiveSnapshot(
  report: ReportRecord | null,
  fallbackText: string,
  defaultConfidence: TranslationKey,
): Snapshot {
  if (!report || report.generation_status !== "completed" || !report.content.trim()) {
    return { bottomLine: fallbackText, actions: [], confidence: defaultConfidence, report: null };
  }

  const lines = report.content
    .split("\n")
    .map(stripMarkdown)
    .filter(Boolean);
  const bottomLine =
    lines.find((line) => line.length >= 28 && line.length <= 240) ??
    lines[0] ??
    fallbackText;
  const actions = lines
    .filter((line) => /^(do|ship|fix|create|publish|run|launch|prioritize|回复|发布|修复|创建|推进|优先)/i.test(line))
    .slice(0, 3);
  const fallbackActions = lines
    .filter((line) => line !== bottomLine && line.length >= 16 && line.length <= 160)
    .slice(0, 3);

  return {
    bottomLine,
    actions: actions.length ? actions : fallbackActions,
    confidence: report.meta?.low_sample ? defaultConfidence : "reports.snapshotConfidenceReady",
    report,
  };
}

function ExecutiveSnapshot({ snapshot }: { snapshot: Snapshot }) {
  const { t } = useI18n();

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-600">
            {t("reports.snapshotEyebrow")}
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
            {t("reports.snapshotTitle")}
          </h2>
          <p className="mt-4 text-base leading-8 text-slate-700">{snapshot.bottomLine}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <span className="font-semibold text-slate-900">{t("reports.snapshotConfidence")}:</span>{" "}
          {t(snapshot.confidence)}
        </div>
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        {(snapshot.actions.length ? snapshot.actions : [t("reports.snapshotNoActions")]).map((action, index) => (
          <div key={`${action}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              {t("reports.snapshotAction")} {index + 1}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{action}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReportSection({
  title,
  description,
  kind,
  human,
  agent,
  onRegenerate,
  regenerating,
  extraAction,
  regenerateLabel,
  humanLabel,
  humanTip,
  agentLabel,
  agentTip,
  noReportText,
  lowSampleText,
  failedReportText,
}: {
  title: string;
  description: string;
  kind: ReportKind;
  human: ReportRecord | null;
  agent: ReportRecord | null;
  onRegenerate: (kind: ReportKind) => void;
  regenerating: boolean;
  extraAction?: ReactNode;
  regenerateLabel: string;
  humanLabel: string;
  humanTip: string;
  agentLabel: string;
  agentTip: string;
  noReportText: string;
  lowSampleText: string;
  failedReportText: string;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 shadow-sm lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-500">{description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => onRegenerate(kind)}
            disabled={regenerating}
            className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCcw className={`h-4 w-4 ${regenerating ? "animate-spin" : ""}`} />
            {regenerateLabel}
          </button>
          {extraAction}
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <ReportCard label={humanLabel} tooltip={humanTip} icon={User} report={human} allowDownload noReportText={noReportText} lowSampleText={lowSampleText} failedReportText={failedReportText} />
        <ReportCard label={agentLabel} tooltip={agentTip} icon={Bot} report={agent} noReportText={noReportText} lowSampleText={lowSampleText} failedReportText={failedReportText} />
      </div>
    </section>
  );
}

export function ReportsPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const qc = useQueryClient();
  const { t, locale } = useI18n();
  const summaryQuery = useProjectSummary(projectId);
  const latestQuery = useLatestReports(projectId, locale);
  const reportsQuery = useReports(projectId, locale);
  const sendMutation = useSendReport(projectId, locale);

  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTaskLocale, setActiveTaskLocale] = useState<string | null>(null);
  const [regeneratingKind, setRegeneratingKind] = useState<ReportKind | null>(null);

  const summary = summaryQuery.data;
  const latest = latestQuery.data;
  const allReports = reportsQuery.data ?? [];
  const latestPeriodicHuman = latest?.periodic?.human ?? null;
  const canEmailLatestReport = Boolean(
    latestPeriodicHuman &&
      latestPeriodicHuman.generation_status === "completed" &&
      latestPeriodicHuman.content.trim(),
  );
  const executiveSnapshot = useMemo(
    () =>
      buildExecutiveSnapshot(
        latest?.strategic?.human ?? latest?.periodic?.human ?? null,
        t("reports.snapshotEmpty"),
        "reports.snapshotConfidenceLow",
      ),
    [latest?.periodic?.human, latest?.strategic?.human, t],
  );

  const strategicHistory = useMemo(
    () => allReports.filter((item) => item.kind === "strategic"),
    [allReports],
  );
  const periodicHistory = useMemo(
    () => allReports.filter((item) => item.kind === "periodic"),
    [allReports],
  );

  if (summaryQuery.isLoading || latestQuery.isLoading || reportsQuery.isLoading) {
    return <LoadingSpinner />;
  }

  const error =
    (summaryQuery.error instanceof Error && summaryQuery.error.message) ||
    (latestQuery.error instanceof Error && latestQuery.error.message) ||
    (reportsQuery.error instanceof Error && reportsQuery.error.message) ||
    (sendMutation.error instanceof Error && sendMutation.error.message) ||
    "";

  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;

  const handleRegenerate = async (kind: ReportKind) => {
    setRegeneratingKind(kind);
    try {
      const result = await apiJson<{ task_id: string }>(`/projects/${projectId}/reports/${kind}/regenerate`, {
        method: "POST",
        body: JSON.stringify({ locale }),
      });
      setActiveTaskId(result.task_id);
      setActiveTaskLocale(locale);
    } catch {
      setRegeneratingKind(null);
    }
  };

  const handlePipelineComplete = () => {
    const completedLocale = activeTaskLocale ?? locale;
    setActiveTaskId(null);
    setActiveTaskLocale(null);
    setRegeneratingKind(null);
    qc.invalidateQueries({ queryKey: ["reports", projectId, completedLocale] });
    qc.invalidateQueries({ queryKey: ["latest-reports", projectId, completedLocale] });
    qc.invalidateQueries({ queryKey: ["project-summary", projectId] });
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ProjectHeader project={summary.project} />
      <ProjectTabs projectId={projectId} />

      <div className="space-y-6">
        <div className="rounded-3xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_45%,#eef2ff_100%)] p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-slate-900 p-2 text-white">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{t("reports.title")}</h1>
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-500">
                {t("reports.description")}
              </p>
              {error ? <div className="mt-4"><ErrorAlert message={error} /></div> : null}
              {sendMutation.data?.ok ? (
                <div className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {t("reports.emailSent").replace("{{recipient}}", String(sendMutation.data.recipient))}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {/* Pipeline Progress Visualization */}
        {activeTaskId && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <PipelineProgress
              taskId={activeTaskId}
              onComplete={handlePipelineComplete}
            />
          </div>
        )}

        <ExecutiveSnapshot snapshot={executiveSnapshot} />

        <ReportSection
          title={t("reports.strategic")}
          description={t("reports.strategicDesc")}
          kind="strategic"
          human={latest?.strategic?.human ?? null}
          agent={latest?.strategic?.agent ?? null}
          onRegenerate={handleRegenerate}
          regenerating={regeneratingKind === "strategic"}
          regenerateLabel={t("reports.regenerateStrategic")}
          humanLabel={t("reports.humanReadout")}
          humanTip={t("reports.humanReadoutTip")}
          agentLabel={t("reports.agentBrief")}
          agentTip={t("reports.agentBriefTip")}
          noReportText={t("reports.noReport")}
          lowSampleText={t("reports.lowSample")}
          failedReportText={t("reports.failed")}
        />

        <ReportSection
          title={t("reports.weekly")}
          description={t("reports.weeklyDesc")}
          kind="periodic"
          human={latest?.periodic?.human ?? null}
          agent={latest?.periodic?.agent ?? null}
          onRegenerate={handleRegenerate}
          regenerating={regeneratingKind === "periodic"}
          regenerateLabel={t("reports.regenerateWeekly")}
          humanLabel={t("reports.humanReadout")}
          humanTip={t("reports.humanReadoutTip")}
          agentLabel={t("reports.agentBrief")}
          agentTip={t("reports.agentBriefTip")}
          noReportText={t("reports.noReport")}
          lowSampleText={t("reports.lowSample")}
          failedReportText={t("reports.failed")}
          extraAction={
            <button
              type="button"
              onClick={() => sendMutation.mutate()}
              disabled={sendMutation.isPending || !canEmailLatestReport}
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Mail className="h-4 w-4" />
              {sendMutation.isPending ? t("reports.sending") : t("reports.sendEmail")}
            </button>
          }
        />

        <div className="grid gap-6 xl:grid-cols-2">
          <ReportHistory title={t("reports.strategicHistory")} reports={strategicHistory} latestLabel={t("reports.latest")} failedLabel={t("reports.failed")} />
          <ReportHistory title={t("reports.weeklyHistory")} reports={periodicHistory} latestLabel={t("reports.latest")} failedLabel={t("reports.failed")} />
        </div>
      </div>
    </div>
  );
}
