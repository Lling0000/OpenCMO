import { useMemo, type ElementType } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileCheck,
  FileText,
  Globe2,
  Linkedin,
  MessageCircle,
  Newspaper,
  PenLine,
  Search,
  Sparkles,
  Twitter,
  Users,
  Zap,
} from "lucide-react";
import { apiJson } from "../../api/client";
import { useI18n } from "../../i18n";
import type { TranslationKey } from "../../i18n";
import type { LatestReports, LatestScans, MonitoringSummary } from "../../types";

type ActionFeedItem = {
  type: "insight" | "approval" | "finding";
  id: number;
  severity: "critical" | "warning" | "info";
  title: string;
  summary: string;
  cta: "view_data" | "review_approval" | "generate_content" | "start_chat";
  action_route?: string;
  insight_id?: number;
  approval_id?: number;
  created_at: string;
};

type AgentKey =
  | "seo"
  | "geo"
  | "community"
  | "reddit"
  | "twitter"
  | "linkedin"
  | "hackerNews"
  | "content"
  | "report";

type AgentTone = "ready" | "review" | "generate" | "monitoring" | "setup";

type AgentActionKind = "details" | "review" | "generate" | "discuss";

type QueueAction = {
  kind: AgentActionKind;
  labelKey: TranslationKey;
  to?: string;
};

type AgentRow = {
  key: AgentKey;
  titleKey: TranslationKey;
  descriptionKey: TranslationKey;
  statusKey: TranslationKey;
  count: number | null;
  countLabelKey: TranslationKey;
  icon: ElementType;
  tone: AgentTone;
  discussPromptKey: TranslationKey;
  actions: QueueAction[];
};

export type AgentActionQueueProps = {
  projectId: number;
  latest: LatestScans;
  latestMonitoring?: MonitoringSummary | null;
  latestReports?: LatestReports;
  pendingApprovals?: number;
  blogDraftsCount?: number;
  competitorCount?: number;
  keywordCount?: number;
  onDiscuss?: (prompt: string) => void;
};

const key = (value: string) => value as TranslationKey;

const LABEL_KEYS = {
  title: key("commandCenter.agentQueue.title"),
  subtitle: key("commandCenter.agentQueue.subtitle"),
  apiEnhanced: key("commandCenter.agentQueue.apiEnhanced"),
  fallback: key("commandCenter.agentQueue.fallback"),
  viewDetails: key("commandCenter.agentQueue.cta.viewDetails"),
  review: key("commandCenter.agentQueue.cta.review"),
  generate: key("commandCenter.agentQueue.cta.generate"),
  discuss: key("commandCenter.agentQueue.cta.discuss"),
  loading: key("commandCenter.agentQueue.loading"),
} satisfies Record<string, TranslationKey>;

const STATUS_STYLES: Record<AgentTone, { dot: string; badge: string; row: string }> = {
  ready: {
    dot: "bg-emerald-500",
    badge: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    row: "hover:border-emerald-200 hover:bg-emerald-50/30",
  },
  review: {
    dot: "bg-amber-500",
    badge: "bg-amber-50 text-amber-700 ring-amber-200",
    row: "hover:border-amber-200 hover:bg-amber-50/30",
  },
  generate: {
    dot: "bg-violet-500",
    badge: "bg-violet-50 text-violet-700 ring-violet-200",
    row: "hover:border-violet-200 hover:bg-violet-50/30",
  },
  monitoring: {
    dot: "bg-sky-500",
    badge: "bg-sky-50 text-sky-700 ring-sky-200",
    row: "hover:border-sky-200 hover:bg-sky-50/30",
  },
  setup: {
    dot: "bg-slate-400",
    badge: "bg-slate-50 text-slate-600 ring-slate-200",
    row: "hover:border-slate-300 hover:bg-slate-50/70",
  },
};

const ACTION_ICONS: Record<AgentActionKind, ElementType> = {
  details: Search,
  review: FileCheck,
  generate: Zap,
  discuss: Sparkles,
};

const CHANNEL_MATCHERS: Record<AgentKey, string[]> = {
  seo: ["seo", "technical", "pagespeed", "site health"],
  geo: ["geo", "ai search", "ai-search", "answer engine", "visibility"],
  community: ["community", "forum", "discussion"],
  reddit: ["reddit", "subreddit"],
  twitter: ["twitter", "tweet", "x agent", "x/twitter"],
  linkedin: ["linkedin"],
  hackerNews: ["hacker news", "hackernews", "hn"],
  content: ["content", "blog", "article"],
  report: ["report", "brief"],
};

function hasReadyReport(latestReports?: LatestReports) {
  return Boolean(
    latestReports?.strategic?.human ||
      latestReports?.strategic?.agent ||
      latestReports?.periodic?.human ||
      latestReports?.periodic?.agent,
  );
}

function routeFor(projectId: number, path: string) {
  return `/projects/${projectId}${path}`;
}

function normalizeText(item: ActionFeedItem) {
  return [item.title, item.summary, item.action_route, item.cta].filter(Boolean).join(" ").toLowerCase();
}

function countFeedMatches(items: ActionFeedItem[], agent: AgentKey) {
  const tokens = CHANNEL_MATCHERS[agent];
  return items.filter((item) => {
    const haystack = normalizeText(item);
    return tokens.some((token) => haystack.includes(token));
  }).length;
}

function countApprovalMatches(items: ActionFeedItem[], agent: AgentKey) {
  const tokens = CHANNEL_MATCHERS[agent];
  return items.filter((item) => {
    if (item.type !== "approval" && item.cta !== "review_approval") return false;
    const haystack = normalizeText(item);
    return tokens.some((token) => haystack.includes(token));
  }).length;
}

function getSeoIssueCount(latest: LatestScans, feedItems: ActionFeedItem[]) {
  const feedCount = countFeedMatches(feedItems, "seo");
  if (feedCount > 0) return feedCount;
  if (!latest.seo) return 0;

  const score = latest.seo.health_score ?? latest.seo.score ?? latest.seo.performance_score;
  if (score == null) return 0;
  return score < 0.9 ? 1 : 0;
}

function buildRows({
  projectId,
  latest,
  latestMonitoring,
  latestReports,
  pendingApprovals,
  blogDraftsCount,
  competitorCount,
  keywordCount,
  feedItems,
}: Required<Pick<AgentActionQueueProps, "projectId" | "latest">> &
  Pick<
    AgentActionQueueProps,
    "latestMonitoring" | "latestReports" | "pendingApprovals" | "blogDraftsCount" | "competitorCount" | "keywordCount"
  > & {
    feedItems: ActionFeedItem[];
  }): AgentRow[] {
  const approvalsCount = pendingApprovals ?? 0;
  const draftsCount = blogDraftsCount ?? 0;
  const competitors = competitorCount ?? 0;
  const keywords = keywordCount ?? 0;
  const communityHits = latest.community?.total_hits ?? 0;
  const monitoringFindings = latestMonitoring?.findings_count ?? 0;
  const monitoringActions = latestMonitoring?.recommendations_count ?? 0;
  const reportReady = hasReadyReport(latestReports);

  const seoIssues = getSeoIssueCount(latest, feedItems);
  const geoActions = countFeedMatches(feedItems, "geo") || (latest.geo ? 1 : 0);
  const communityActions = countFeedMatches(feedItems, "community") || communityHits;
  const redditApprovals = countApprovalMatches(feedItems, "reddit");
  const redditOpportunities = Math.max(countFeedMatches(feedItems, "reddit"), redditApprovals, communityHits);
  const twitterDrafts = countApprovalMatches(feedItems, "twitter");
  const linkedinDrafts = countApprovalMatches(feedItems, "linkedin");
  const hnOpportunities = countFeedMatches(feedItems, "hackerNews");
  const contentActions = countFeedMatches(feedItems, "content") || draftsCount;
  const reportActions = countFeedMatches(feedItems, "report") || monitoringActions;
  const needsSetup = competitors === 0 || keywords === 0;
  const setupRoute = competitors === 0 ? routeFor(projectId, "/graph") : routeFor(projectId, "/serp");

  return [
    {
      key: "seo",
      titleKey: key("commandCenter.agentQueue.agent.seo.title"),
      descriptionKey: latest.seo
        ? key("commandCenter.agentQueue.agent.seo.description.ready")
        : key("commandCenter.agentQueue.agent.seo.description.pending"),
      statusKey: seoIssues > 0
        ? key("commandCenter.agentQueue.status.fixesQueued")
        : latest.seo
          ? key("commandCenter.agentQueue.status.monitoring")
          : key("commandCenter.agentQueue.status.needsScan"),
      count: seoIssues,
      countLabelKey: key("commandCenter.agentQueue.count.fixes"),
      icon: Search,
      tone: seoIssues > 0 ? "ready" : latest.seo ? "monitoring" : "setup",
      discussPromptKey: key("commandCenter.agentQueue.prompt.seo"),
      actions: [
        { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/seo") },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "geo",
      titleKey: key("commandCenter.agentQueue.agent.geo.title"),
      descriptionKey: latest.geo
        ? key("commandCenter.agentQueue.agent.geo.description.ready")
        : key("commandCenter.agentQueue.agent.geo.description.pending"),
      statusKey: latest.geo
        ? key("commandCenter.agentQueue.status.visibilityReady")
        : key("commandCenter.agentQueue.status.needsScan"),
      count: geoActions,
      countLabelKey: key("commandCenter.agentQueue.count.signals"),
      icon: Globe2,
      tone: latest.geo ? "ready" : "setup",
      discussPromptKey: key("commandCenter.agentQueue.prompt.geo"),
      actions: [
        { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/geo") },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "community",
      titleKey: key("commandCenter.agentQueue.agent.community.title"),
      descriptionKey: communityHits > 0
        ? key("commandCenter.agentQueue.agent.community.description.ready")
        : key("commandCenter.agentQueue.agent.community.description.pending"),
      statusKey: communityHits > 0
        ? key("commandCenter.agentQueue.status.opportunitiesReady")
        : key("commandCenter.agentQueue.status.monitoring"),
      count: communityActions,
      countLabelKey: key("commandCenter.agentQueue.count.threads"),
      icon: Users,
      tone: communityHits > 0 ? "ready" : "monitoring",
      discussPromptKey: key("commandCenter.agentQueue.prompt.community"),
      actions: [
        { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/community") },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "reddit",
      titleKey: key("commandCenter.agentQueue.agent.reddit.title"),
      descriptionKey: redditOpportunities > 0
        ? key("commandCenter.agentQueue.agent.reddit.description.ready")
        : key("commandCenter.agentQueue.agent.reddit.description.pending"),
      statusKey: redditApprovals > 0
        ? key("commandCenter.agentQueue.status.needsReview")
        : redditOpportunities > 0
          ? key("commandCenter.agentQueue.status.opportunitiesReady")
          : key("commandCenter.agentQueue.status.canGenerate"),
      count: redditOpportunities,
      countLabelKey: key("commandCenter.agentQueue.count.opportunities"),
      icon: MessageCircle,
      tone: redditApprovals > 0 ? "review" : redditOpportunities > 0 ? "ready" : "generate",
      discussPromptKey: key("commandCenter.agentQueue.prompt.reddit"),
      actions: [
        redditApprovals > 0
          ? { kind: "review", labelKey: LABEL_KEYS.review, to: "/approvals" }
          : { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/community") },
        { kind: "generate", labelKey: LABEL_KEYS.generate, to: routeFor(projectId, "/content") },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "twitter",
      titleKey: key("commandCenter.agentQueue.agent.twitter.title"),
      descriptionKey: twitterDrafts > 0
        ? key("commandCenter.agentQueue.agent.twitter.description.ready")
        : key("commandCenter.agentQueue.agent.twitter.description.pending"),
      statusKey: twitterDrafts > 0
        ? key("commandCenter.agentQueue.status.needsReview")
        : needsSetup
          ? key("commandCenter.agentQueue.status.needsInputs")
          : key("commandCenter.agentQueue.status.canGenerate"),
      count: twitterDrafts,
      countLabelKey: key("commandCenter.agentQueue.count.drafts"),
      icon: Twitter,
      tone: twitterDrafts > 0 ? "review" : needsSetup ? "setup" : "generate",
      discussPromptKey: key("commandCenter.agentQueue.prompt.twitter"),
      actions: [
        twitterDrafts > 0
          ? { kind: "review", labelKey: LABEL_KEYS.review, to: "/approvals" }
          : {
              kind: needsSetup ? "details" : "generate",
              labelKey: needsSetup ? LABEL_KEYS.viewDetails : LABEL_KEYS.generate,
              to: needsSetup ? setupRoute : routeFor(projectId, "/content"),
            },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "linkedin",
      titleKey: key("commandCenter.agentQueue.agent.linkedin.title"),
      descriptionKey: linkedinDrafts > 0
        ? key("commandCenter.agentQueue.agent.linkedin.description.ready")
        : key("commandCenter.agentQueue.agent.linkedin.description.pending"),
      statusKey: linkedinDrafts > 0
        ? key("commandCenter.agentQueue.status.needsReview")
        : needsSetup
          ? key("commandCenter.agentQueue.status.needsInputs")
          : key("commandCenter.agentQueue.status.canGenerate"),
      count: linkedinDrafts,
      countLabelKey: key("commandCenter.agentQueue.count.drafts"),
      icon: Linkedin,
      tone: linkedinDrafts > 0 ? "review" : needsSetup ? "setup" : "generate",
      discussPromptKey: key("commandCenter.agentQueue.prompt.linkedin"),
      actions: [
        linkedinDrafts > 0
          ? { kind: "review", labelKey: LABEL_KEYS.review, to: "/approvals" }
          : {
              kind: needsSetup ? "details" : "generate",
              labelKey: needsSetup ? LABEL_KEYS.viewDetails : LABEL_KEYS.generate,
              to: needsSetup ? setupRoute : routeFor(projectId, "/content"),
            },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "hackerNews",
      titleKey: key("commandCenter.agentQueue.agent.hackerNews.title"),
      descriptionKey: hnOpportunities > 0
        ? key("commandCenter.agentQueue.agent.hackerNews.description.ready")
        : key("commandCenter.agentQueue.agent.hackerNews.description.pending"),
      statusKey: hnOpportunities > 0
        ? key("commandCenter.agentQueue.status.opportunitiesReady")
        : needsSetup
          ? key("commandCenter.agentQueue.status.needsInputs")
          : key("commandCenter.agentQueue.status.canGenerate"),
      count: hnOpportunities,
      countLabelKey: key("commandCenter.agentQueue.count.opportunities"),
      icon: Newspaper,
      tone: hnOpportunities > 0 ? "ready" : needsSetup ? "setup" : "generate",
      discussPromptKey: key("commandCenter.agentQueue.prompt.hackerNews"),
      actions: [
        hnOpportunities > 0
          ? { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/community") }
          : {
              kind: needsSetup ? "details" : "generate",
              labelKey: needsSetup ? LABEL_KEYS.viewDetails : LABEL_KEYS.generate,
              to: needsSetup ? setupRoute : routeFor(projectId, "/content"),
            },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "content",
      titleKey: key("commandCenter.agentQueue.agent.content.title"),
      descriptionKey: draftsCount > 0
        ? key("commandCenter.agentQueue.agent.content.description.ready")
        : key("commandCenter.agentQueue.agent.content.description.pending"),
      statusKey: draftsCount > 0 || contentActions > 0
        ? key("commandCenter.agentQueue.status.draftsReady")
        : needsSetup
          ? key("commandCenter.agentQueue.status.needsInputs")
          : key("commandCenter.agentQueue.status.canGenerate"),
      count: contentActions,
      countLabelKey: key("commandCenter.agentQueue.count.drafts"),
      icon: PenLine,
      tone: draftsCount > 0 || contentActions > 0 ? "review" : needsSetup ? "setup" : "generate",
      discussPromptKey: key("commandCenter.agentQueue.prompt.content"),
      actions: [
        {
          kind: draftsCount > 0 ? "review" : needsSetup ? "details" : "generate",
          labelKey: draftsCount > 0 ? LABEL_KEYS.review : needsSetup ? LABEL_KEYS.viewDetails : LABEL_KEYS.generate,
          to: draftsCount > 0 || !needsSetup ? routeFor(projectId, "/content") : setupRoute,
        },
        { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
    {
      key: "report",
      titleKey: key("commandCenter.agentQueue.agent.report.title"),
      descriptionKey: latestMonitoring
        ? key("commandCenter.agentQueue.agent.report.description.ready")
        : key("commandCenter.agentQueue.agent.report.description.pending"),
      statusKey: reportReady
        ? key("commandCenter.agentQueue.status.reportReady")
        : latestMonitoring
          ? key("commandCenter.agentQueue.status.briefQueued")
          : key("commandCenter.agentQueue.status.needsScan"),
      count: reportActions || monitoringFindings,
      countLabelKey: key("commandCenter.agentQueue.count.actions"),
      icon: FileText,
      tone: reportReady ? "ready" : latestMonitoring ? "monitoring" : "setup",
      discussPromptKey: key("commandCenter.agentQueue.prompt.report"),
      actions: [
        { kind: "details", labelKey: LABEL_KEYS.viewDetails, to: routeFor(projectId, "/reports") },
        approvalsCount > 0
          ? { kind: "review", labelKey: LABEL_KEYS.review, to: "/approvals" }
          : { kind: "discuss", labelKey: LABEL_KEYS.discuss },
      ],
    },
  ];
}

function QueueButton({
  action,
  onClick,
}: {
  action: QueueAction;
  onClick?: () => void;
}) {
  const { t } = useI18n();
  const Icon = ACTION_ICONS[action.kind];
  const className =
    "inline-flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950";

  if (action.kind === "discuss") {
    return (
      <button type="button" onClick={onClick} className={className}>
        <Icon size={13} />
        {t(action.labelKey)}
      </button>
    );
  }

  return (
    <Link to={action.to ?? "#"} className={className}>
      <Icon size={13} />
      {t(action.labelKey)}
    </Link>
  );
}

function QueueRow({
  row,
  countFormatter,
  onDiscuss,
}: {
  row: AgentRow;
  countFormatter: Intl.NumberFormat;
  onDiscuss?: (prompt: string) => void;
}) {
  const { t } = useI18n();
  const Icon = row.icon;
  const style = STATUS_STYLES[row.tone];
  const count = row.count == null ? null : countFormatter.format(row.count);
  const handleDiscuss = () => onDiscuss?.(t(row.discussPromptKey));

  return (
    <div
      className={`group grid gap-3 border-b border-slate-100 px-3 py-3 transition last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center ${style.row}`}
    >
      <div className="flex min-w-0 items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
          <Icon size={16} />
        </div>
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-slate-950">{t(row.titleKey)}</h3>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ${style.badge}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
              {t(row.statusKey)}
            </span>
          </div>
          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs leading-5 text-slate-500">
            {count != null && (
              <span className="font-semibold text-slate-700">
                {count} {t(row.countLabelKey)}
              </span>
            )}
            <span className="min-w-0">{t(row.descriptionKey)}</span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 sm:justify-end">
        {row.actions.map((action, index) => (
          <QueueButton
            key={`${row.key}-${action.kind}-${index}`}
            action={action}
            onClick={action.kind === "discuss" ? handleDiscuss : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export function AgentActionQueue({
  projectId,
  latest,
  latestMonitoring,
  latestReports,
  pendingApprovals = 0,
  blogDraftsCount = 0,
  competitorCount = 0,
  keywordCount = 0,
  onDiscuss,
}: AgentActionQueueProps) {
  const { t, locale } = useI18n();
  const { data: feedItems = [], isFetching } = useQuery({
    queryKey: ["agent-action-queue", projectId, locale],
    queryFn: () => apiJson<ActionFeedItem[]>(`/projects/${projectId}/action-feed?lang=${locale}`),
    retry: 1,
    staleTime: 60_000,
  });
  const countFormatter = useMemo(() => new Intl.NumberFormat(locale), [locale]);
  const rows = useMemo(
    () =>
      buildRows({
        projectId,
        latest,
        latestMonitoring,
        latestReports,
        pendingApprovals,
        blogDraftsCount,
        competitorCount,
        keywordCount,
        feedItems,
      }),
    [
      projectId,
      latest,
      latestMonitoring,
      latestReports,
      pendingApprovals,
      blogDraftsCount,
      competitorCount,
      keywordCount,
      feedItems,
    ],
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Sparkles size={15} />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-950">{t(LABEL_KEYS.title)}</h2>
            <p className="mt-0.5 text-xs text-slate-500">{t(LABEL_KEYS.subtitle)}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500">
          {isFetching ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-200 border-t-slate-500" />
              {t(LABEL_KEYS.loading)}
            </>
          ) : feedItems.length > 0 ? (
            <>
              <CheckCircle2 size={13} className="text-emerald-500" />
              {t(LABEL_KEYS.apiEnhanced)}
            </>
          ) : (
            <>
              <CheckCircle2 size={13} className="text-slate-400" />
              {t(LABEL_KEYS.fallback)}
            </>
          )}
        </div>
      </div>

      <div>
        {rows.map((row) => (
          <QueueRow
            key={row.key}
            row={row}
            countFormatter={countFormatter}
            onDiscuss={onDiscuss}
          />
        ))}
      </div>
    </section>
  );
}
