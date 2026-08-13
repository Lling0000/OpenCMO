import { useState, useMemo } from "react";
import { useParams } from "react-router";
import { useProjectSummary } from "../hooks/useProject";
import {
  useGitHubLeads,
  useLeadStats,
  useDiscoveryRuns,
  useGenerateOutreach,
  useScoreLeads,
} from "../hooks/useGitHubLeads";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { EmptyState } from "../components/common/EmptyState";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import { KpiCard } from "../components/common/KpiCard";
import {
  Users,
  Mail,
  Star,
  Send,
  CheckCircle,
  ExternalLink,
  Twitter,
  Zap,
} from "lucide-react";
import { useI18n } from "../i18n";
import type { TranslationKey } from "../i18n";
import type { GitHubLead } from "../types";

const STATUS_BADGE: Record<string, string> = {
  not_contacted: "bg-zinc-100 text-zinc-600",
  draft_pending: "bg-amber-100 text-amber-700",
  contacted: "bg-sky-100 text-sky-700",
  replied: "bg-emerald-100 text-emerald-700",
  opted_out: "bg-rose-100 text-rose-600",
};

const DISCOVERY_STATUS_LABEL_KEYS: Record<string, TranslationKey> = {
  pending: "github.discoveryStatus.pending",
  running: "github.discoveryStatus.running",
  completed: "github.discoveryStatus.completed",
  failed: "github.discoveryStatus.failed",
  cancelled: "github.discoveryStatus.cancelled",
  canceled: "github.discoveryStatus.cancelled",
};

function enumFallback(value: string) {
  return value.replace(/_/g, " ");
}

export function GitHubLeadsPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { t } = useI18n();
  const { data: summary, isLoading: projLoading } = useProjectSummary(projectId);

  // Filters
  const [filterLanguage, setFilterLanguage] = useState("");
  const [filterLocation, setFilterLocation] = useState("");
  const [filterHasEmail, setFilterHasEmail] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");

  const filters = useMemo(() => {
    // Default: only show enriched leads with score > 0 (i.e. contactable)
    const f: Record<string, string> = { enriched: "true", min_score: "1" };
    if (filterLanguage) f.language = filterLanguage;
    if (filterLocation) f.location = filterLocation;
    if (filterHasEmail) f.has_email = "true";
    if (filterStatus) f.status = filterStatus;
    return f;
  }, [filterLanguage, filterLocation, filterHasEmail, filterStatus]);

  const { data: leadsData, isLoading: leadsLoading } = useGitHubLeads(projectId, filters);
  const { data: stats } = useLeadStats(projectId);
  const { data: runs } = useDiscoveryRuns(projectId);

  // Outreach
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [outreachChannel, setOutreachChannel] = useState("email");
  const genOutreach = useGenerateOutreach();
  const scoreMut = useScoreLeads();

  // Expanded rows
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (projLoading) return <LoadingSpinner />;
  if (!summary) return <ErrorAlert message={t("common.projectNotFound")} />;
  const project = summary.project;

  const leads = leadsData?.leads ?? [];

  const toggleSelect = (login: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(login)) next.delete(login);
      else next.add(login);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === leads.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(leads.map((l) => l.login)));
    }
  };

  const toggleExpand = (login: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(login)) next.delete(login);
      else next.add(login);
      return next;
    });
  };

  const handleGenerate = () => {
    if (selected.size === 0) return;
    genOutreach.mutate({
      projectId,
      logins: Array.from(selected),
      channel: outreachChannel,
    });
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <ProjectHeader project={project} />
      <ProjectTabs projectId={projectId} />

      {/* KPI Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <KpiCard
          icon={Users}
          label={t("github.totalLeads")}
          value={stats?.total ?? 0}
          accentBg="bg-indigo-50"
          accentText="text-indigo-600"
        />
        <KpiCard
          icon={CheckCircle}
          label={t("github.enriched")}
          value={stats?.enriched ?? 0}
          accentBg="bg-emerald-50"
          accentText="text-emerald-600"
        />
        <KpiCard
          icon={Mail}
          label={t("github.hasEmail")}
          value={stats?.has_email ?? 0}
          accentBg="bg-sky-50"
          accentText="text-sky-600"
        />
        <KpiCard
          icon={Twitter}
          label={t("github.hasTwitter")}
          value={stats?.has_twitter ?? 0}
          accentBg="bg-cyan-50"
          accentText="text-cyan-600"
        />
        <KpiCard
          icon={Star}
          label={t("github.avgScore")}
          value={stats?.avg_score ?? 0}
          accentBg="bg-amber-50"
          accentText="text-amber-600"
        />
      </div>

      {/* Auto-discovery info + rescore */}
      <div className="flex items-center justify-between rounded-xl border border-zinc-100 bg-white px-5 py-4 shadow-sm">
        <div className="text-sm text-zinc-600">
          <span className="font-medium text-zinc-800">{t("github.autoMode")}</span>
          {" — "}
          {t("github.autoModeDesc")}
        </div>
        <button
          onClick={() => scoreMut.mutate({ projectId })}
          disabled={scoreMut.isPending}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Zap className="h-4 w-4" />
          {t("github.rescore")}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={filterLanguage}
          onChange={(e) => setFilterLanguage(e.target.value)}
          placeholder={t("github.filterLanguage")}
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          value={filterLocation}
          onChange={(e) => setFilterLocation(e.target.value)}
          placeholder={t("github.filterLocation")}
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm"
        />
        <label className="flex items-center gap-1.5 text-sm text-zinc-600">
          <input
            type="checkbox"
            checked={filterHasEmail}
            onChange={(e) => setFilterHasEmail(e.target.checked)}
            className="rounded border-zinc-300"
          />
          {t("github.filterHasEmail")}
        </label>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm"
        >
          <option value="">{t("github.allStatuses")}</option>
          <option value="not_contacted">{t("github.status.not_contacted")}</option>
          <option value="draft_pending">{t("github.status.draft_pending")}</option>
          <option value="contacted">{t("github.status.contacted")}</option>
          <option value="replied">{t("github.status.replied")}</option>
          <option value="opted_out">{t("github.status.opted_out")}</option>
        </select>
      </div>

      {/* Leads Table */}
      {leadsLoading ? (
        <LoadingSpinner />
      ) : leads.length === 0 ? (
        <EmptyState
          title={t("github.noLeads")}
          description={t("github.noLeadsDesc")}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-zinc-100 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-100 bg-zinc-50/50 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                <th className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size === leads.length && leads.length > 0}
                    onChange={toggleAll}
                    className="rounded border-zinc-300"
                  />
                </th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">{t("github.languages")}</th>
                <th className="px-4 py-3">{t("github.stars")}</th>
                <th className="px-4 py-3">{t("github.score")}</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <LeadRow
                  key={lead.login}
                  lead={lead}
                  selected={selected.has(lead.login)}
                  expanded={expanded.has(lead.login)}
                  onSelect={() => toggleSelect(lead.login)}
                  onExpand={() => toggleExpand(lead.login)}
                  t={t}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Bulk Action Bar */}
      {selected.size > 0 && (
        <div className="sticky bottom-4 z-10 flex items-center justify-between rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-3 shadow-lg">
          <span className="text-sm font-medium text-indigo-700">
            {selected.size} {t("github.selected")}
          </span>
          <div className="flex items-center gap-3">
            <select
              value={outreachChannel}
              onChange={(e) => setOutreachChannel(e.target.value)}
              className="rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-sm"
            >
              <option value="email">{t("github.channelEmail")}</option>
              <option value="twitter_dm">{t("github.channelTwitter")}</option>
              <option value="github_issue">{t("github.channelGithub")}</option>
            </select>
            <button
              onClick={handleGenerate}
              disabled={genOutreach.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {genOutreach.isPending ? "..." : t("github.generateOutreach")}
            </button>
          </div>
        </div>
      )}

      {/* Discovery History */}
      {runs && runs.length > 0 && (
        <div className="rounded-xl border border-zinc-100 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-zinc-700">{t("github.runHistory")}</h3>
          <div className="space-y-2">
            {runs.map((run) => (
              <div
                key={run.id}
                className="flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2 text-sm"
              >
                <span className="font-medium text-zinc-700">@{run.seed_username}</span>
                <span className="text-zinc-500">
                  {run.total_discovered} found, {run.total_enriched} enriched
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    run.status === "running"
                      ? "bg-amber-100 text-amber-700"
                      : run.status === "completed"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-rose-100 text-rose-600"
                  }`}
                >
                  {DISCOVERY_STATUS_LABEL_KEYS[run.status] ? t(DISCOVERY_STATUS_LABEL_KEYS[run.status]!) : enumFallback(run.status)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LeadRow({
  lead,
  selected,
  expanded,
  onSelect,
  onExpand,
  t,
}: {
  lead: GitHubLead;
  selected: boolean;
  expanded: boolean;
  onSelect: () => void;
  onExpand: () => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  return (
    <>
      <tr
        className="cursor-pointer border-b border-zinc-50 transition-colors hover:bg-zinc-50/50"
        onClick={onExpand}
      >
        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={selected}
            onChange={onSelect}
            className="rounded border-zinc-300"
          />
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <img
              src={`https://github.com/${lead.login}.png?size=32`}
              alt=""
              className="h-8 w-8 rounded-full"
            />
            <div className="min-w-0">
              <a
                href={`https://github.com/${lead.login}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="font-medium text-zinc-800 hover:text-indigo-600"
              >
                @{lead.login}
              </a>
              {lead.name && (
                <div className="truncate text-xs text-zinc-500">{lead.name}</div>
              )}
              {lead.location && (
                <div className="truncate text-xs text-zinc-400">{lead.location}</div>
              )}
            </div>
          </div>
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-1">
            {(lead.top_languages || []).slice(0, 3).map((lang) => (
              <span
                key={lang}
                className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600"
              >
                {lang}
              </span>
            ))}
          </div>
        </td>
        <td className="px-4 py-3 font-mono text-zinc-700">{lead.total_stars}</td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-16 overflow-hidden rounded-full bg-zinc-100">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{ width: `${lead.outreach_score}%` }}
              />
            </div>
            <span className="text-xs text-zinc-500">{lead.outreach_score}</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            {lead.email && (
              <span title={lead.email}><Mail className="h-4 w-4 text-sky-500" /></span>
            )}
            {lead.twitter_username && (
              <span title={`@${lead.twitter_username}`}><Twitter className="h-4 w-4 text-cyan-500" /></span>
            )}
            {lead.blog && (
              <span title={lead.blog}><ExternalLink className="h-4 w-4 text-zinc-400" /></span>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              STATUS_BADGE[lead.outreach_status] ?? STATUS_BADGE.not_contacted
            }`}
          >
            {t(`github.status.${lead.outreach_status}` as Parameters<typeof t>[0])}
          </span>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-zinc-100 bg-zinc-50/30">
          <td colSpan={7} className="px-8 py-4">
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                {lead.bio && <p className="mb-2 text-zinc-600">{lead.bio}</p>}
                {lead.company && (
                  <p className="text-xs text-zinc-500">Company: {lead.company}</p>
                )}
                {lead.email && (
                  <p className="text-xs text-zinc-500">Email: {lead.email}</p>
                )}
                {lead.blog && (
                  <p className="text-xs text-zinc-500">
                    Blog:{" "}
                    <a
                      href={lead.blog.startsWith("http") ? lead.blog : `https://${lead.blog}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline"
                    >
                      {lead.blog}
                    </a>
                  </p>
                )}
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-zinc-500">{t("github.topRepos")}</p>
                {(lead.top_repos || []).slice(0, 3).map((repo) => (
                  <div key={repo.name} className="mb-1 text-xs text-zinc-600">
                    <span className="font-medium">{repo.name}</span>
                    {repo.language && (
                      <span className="ml-1 text-zinc-400">[{repo.language}]</span>
                    )}
                    <span className="ml-1 text-amber-600">{repo.stars}</span>
                    {repo.description && (
                      <span className="ml-1 text-zinc-400">— {repo.description.slice(0, 80)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
