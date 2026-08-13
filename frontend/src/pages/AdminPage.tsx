import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AlertTriangle, Ban, CheckCircle2, Clock, RefreshCw, SlidersHorizontal } from "lucide-react";
import { disableAccount, enableAccount, extendTrial, getAdminSummary, updateQuota } from "../api/admin";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { SkeletonCard } from "../components/common/SkeletonCard";
import { useI18n } from "../i18n";
import type { AuthAccount } from "../types";

function AccountRow({
  account,
  onDisable,
  onEnable,
  onExtend,
  onQuota,
  busy,
}: {
  account: AuthAccount;
  onDisable: (accountId: number) => void;
  onEnable: (accountId: number) => void;
  onExtend: (accountId: number, days: number) => void;
  onQuota: (accountId: number, payload: {
    max_projects: number;
    daily_scan_limit: number;
    monthly_report_limit: number;
  }) => void;
  busy: boolean;
}) {
  const { t } = useI18n();
  const [days, setDays] = useState("7");
  const [maxProjects, setMaxProjects] = useState(String(account.max_projects));
  const [dailyScans, setDailyScans] = useState(String(account.daily_scan_limit));
  const [monthlyReports, setMonthlyReports] = useState(String(account.monthly_report_limit));

  const numberValue = (value: string, fallback: number) => {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
  };

  return (
    <tr>
      <td className="px-4 py-3 font-medium text-slate-900">{account.name}</td>
      <td className="px-4 py-3 text-slate-600">{account.status}</td>
      <td className="px-4 py-3 text-slate-600">{account.plan}</td>
      <td className="px-4 py-3 text-slate-600">
        {account.max_projects} / {account.daily_scan_limit} / {account.monthly_report_limit}
      </td>
      <td className="min-w-[360px] px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {account.status === "active" ? (
            <button
              disabled={busy}
              onClick={() => onDisable(account.id)}
              className="inline-flex items-center gap-1.5 rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Ban size={13} />
              {t("trial.disable")}
            </button>
          ) : (
            <button
              disabled={busy}
              onClick={() => onEnable(account.id)}
              className="inline-flex items-center gap-1.5 rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <CheckCircle2 size={13} />
              {t("trial.enable")}
            </button>
          )}
          <div className="flex items-center gap-1">
            <input
              aria-label={t("trial.extendDays")}
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={(event) => setDays(event.target.value)}
              className="h-8 w-16 rounded-md border border-slate-200 px-2 text-xs"
            />
            <button
              disabled={busy}
              onClick={() => onExtend(account.id, Math.max(1, numberValue(days, 7)))}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Clock size={13} />
              {t("trial.extendTrial")}
            </button>
          </div>
          <div className="flex items-center gap-1">
            <input
              aria-label={t("trial.projectLimit")}
              type="number"
              min={0}
              value={maxProjects}
              onChange={(event) => setMaxProjects(event.target.value)}
              className="h-8 w-14 rounded-md border border-slate-200 px-2 text-xs"
            />
            <input
              aria-label={t("trial.dailyScanLimit")}
              type="number"
              min={0}
              value={dailyScans}
              onChange={(event) => setDailyScans(event.target.value)}
              className="h-8 w-14 rounded-md border border-slate-200 px-2 text-xs"
            />
            <input
              aria-label={t("trial.monthlyReportLimit")}
              type="number"
              min={0}
              value={monthlyReports}
              onChange={(event) => setMonthlyReports(event.target.value)}
              className="h-8 w-14 rounded-md border border-slate-200 px-2 text-xs"
            />
            <button
              disabled={busy}
              onClick={() => onQuota(account.id, {
                max_projects: numberValue(maxProjects, account.max_projects),
                daily_scan_limit: numberValue(dailyScans, account.daily_scan_limit),
                monthly_report_limit: numberValue(monthlyReports, account.monthly_report_limit),
              })}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <SlidersHorizontal size={13} />
              {t("trial.apply")}
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
}

export function AdminPage() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const summary = useQuery({ queryKey: ["admin-summary"], queryFn: getAdminSummary });
  const disable = useMutation({
    mutationFn: disableAccount,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-summary"] }),
  });
  const enable = useMutation({
    mutationFn: enableAccount,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-summary"] }),
  });
  const extend = useMutation({
    mutationFn: ({ accountId, days }: { accountId: number; days: number }) => extendTrial(accountId, days),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-summary"] }),
  });
  const quota = useMutation({
    mutationFn: ({
      accountId,
      payload,
    }: {
      accountId: number;
      payload: { max_projects: number; daily_scan_limit: number; monthly_report_limit: number };
    }) => updateQuota(accountId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-summary"] }),
  });

  if (summary.isLoading) return <SkeletonCard count={3} />;
  if (summary.error) return <ErrorAlert message={summary.error.message} />;
  if (!summary.data) return null;

  const cards = [
    ["trial.adminTotalUsers", summary.data.total_users],
    ["trial.adminNewUsers", summary.data.new_users_today],
    ["trial.adminActiveTrials", summary.data.active_trial_accounts],
    ["trial.adminExpiredTrials", summary.data.expired_trial_accounts],
    ["trial.adminProjects", summary.data.total_projects],
    ["trial.adminProjectsToday", summary.data.projects_created_today],
    ["trial.adminScans", summary.data.scans_today],
    ["trial.adminReports", summary.data.reports_this_month],
    ["trial.adminFailedTasksCount", summary.data.failed_tasks_24h],
  ] as const;
  const adminBusy = disable.isPending || enable.isPending || extend.isPending || quota.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">{t("trial.adminTitle")}</h1>
          <p className="mt-1 text-sm text-slate-500">{t("trial.adminSubtitle")}</p>
        </div>
        <button
          onClick={() => summary.refetch()}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
        >
          <RefreshCw size={15} />
          {t("trial.refresh")}
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{t(label as never)}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p>
          </div>
        ))}
      </div>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="font-semibold text-slate-950">{t("trial.adminRecentUsers")}</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("trial.email")}</th>
                <th className="px-4 py-3">{t("trial.displayName")}</th>
                <th className="px-4 py-3">{t("trial.status")}</th>
                <th className="px-4 py-3">{t("trial.createdAt")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.data.recent_users.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{user.email}</td>
                  <td className="px-4 py-3 text-slate-600">{user.name || "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{user.status}</td>
                  <td className="px-4 py-3 text-slate-600">{user.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="font-semibold text-slate-950">{t("trial.adminRecentAccounts")}</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("trial.account")}</th>
                <th className="px-4 py-3">{t("trial.status")}</th>
                <th className="px-4 py-3">{t("trial.plan")}</th>
                <th className="px-4 py-3">{t("trial.quota")}</th>
                <th className="px-4 py-3">{t("trial.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.data.recent_accounts.map((account) => (
                <AccountRow
                  key={account.id}
                  account={account}
                  busy={adminBusy}
                  onDisable={(accountId) => disable.mutate(accountId)}
                  onEnable={(accountId) => enable.mutate(accountId)}
                  onExtend={(accountId, days) => extend.mutate({ accountId, days })}
                  onQuota={(accountId, payload) => quota.mutate({ accountId, payload })}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="font-semibold text-slate-950">{t("trial.adminUsage")}</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("trial.account")}</th>
                <th className="px-4 py-3">{t("trial.status")}</th>
                <th className="px-4 py-3">{t("trial.plan")}</th>
                <th className="px-4 py-3">{t("trial.usageEvents")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.data.high_usage_accounts.map((account) => (
                <tr key={account.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{account.name}</td>
                  <td className="px-4 py-3 text-slate-600">{account.status}</td>
                  <td className="px-4 py-3 text-slate-600">{account.plan}</td>
                  <td className="px-4 py-3 text-slate-600">{account.usage_count}</td>
                </tr>
              ))}
              {!summary.data.high_usage_accounts.length && (
                <tr>
                  <td className="px-4 py-3 text-sm text-slate-500" colSpan={4}>
                    {t("trial.noUsageEvents")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle size={17} className="text-amber-600" />
          <h2 className="font-semibold text-slate-950">{t("trial.adminFailedTasks")}</h2>
        </div>
        <div className="mt-3 space-y-2">
          {summary.data.recent_failed_tasks.length ? summary.data.recent_failed_tasks.map((task) => (
            <div key={task.task_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
              <span className="font-medium text-slate-900">{task.kind}</span>{" "}
              {task.error?.message || task.task_id}
            </div>
          )) : (
            <p className="text-sm text-slate-500">{t("trial.noFailedTasks")}</p>
          )}
        </div>
      </section>
    </div>
  );
}
