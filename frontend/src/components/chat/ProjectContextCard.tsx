import {
  Search,
  Globe,
  MessageCircle,
  TrendingUp,
  Target,
  AlertTriangle,
  Sparkles,
  ExternalLink,
  Tag,
} from "lucide-react";
import type { ChatProjectContext } from "../../api/chatContext";
import { useI18n } from "../../i18n";

function ScoreCard({
  label,
  value,
  icon: Icon,
  color,
  suffix,
}: {
  label: string;
  value: number | string | null;
  icon: typeof Search;
  color: string;
  suffix?: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white p-3 shadow-sm">
      <div
        className={`flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br ${color} text-white shadow-sm`}
      >
        <Icon size={16} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
          {label}
        </p>
        <p className="text-lg font-bold text-slate-800">
          {value != null ? value : "—"}
          {suffix && value != null ? (
            <span className="text-sm font-normal text-slate-400">{suffix}</span>
          ) : null}
        </p>
      </div>
    </div>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500",
    warning: "bg-amber-400",
    info: "bg-blue-400",
  };
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${colors[severity] ?? "bg-slate-300"}`}
    />
  );
}

export function ProjectContextCard({
  context,
  onSuggest,
  compact = false,
}: {
  context: ChatProjectContext;
  onSuggest: (prompt: string) => void;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const { project, scores, keywords, competitors, keyword_gaps, findings } =
    context;
  const name = project.brand_name;

  const suggestions = [
    { label: t("chat.suggestStrategy"), prompt: t("chat.suggestStrategyPrompt", { name }) },
    { label: t("chat.suggestCompetitor"), prompt: t("chat.suggestCompetitorPrompt", { name }) },
    { label: t("chat.suggestVisibility"), prompt: t("chat.suggestVisibilityPrompt", { name }) },
    { label: t("chat.suggestBlog"), prompt: t("chat.suggestBlogPrompt", { name }) },
  ];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-3 duration-500 space-y-4">
      {/* Header */}
      <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-violet-50/60 p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-indigo-500" />
              <p className="text-xs font-semibold uppercase tracking-widest text-indigo-500">
                {t("chat.contextLoaded")}
              </p>
            </div>
            <h3 className="mt-2 text-xl font-bold text-slate-900">
              {project.brand_name}
            </h3>
            <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
              <a
                href={project.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-indigo-600 transition-colors"
              >
                {project.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                <ExternalLink size={12} />
              </a>
              <span className="rounded-full bg-slate-200/60 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                {project.category === "auto" ? t("project.categoryAuto") : project.category}
              </span>
            </div>
          </div>
        </div>

        {/* AI greeting */}
        <div className="mt-4 rounded-xl bg-white/70 p-3 text-sm text-slate-600 leading-relaxed">
          🤖 {t("chat.aiGreeting", { name })}
        </div>
      </div>

      {/* Score cards */}
      <div className={compact ? "grid grid-cols-2 gap-3" : "grid grid-cols-2 gap-3 lg:grid-cols-4"}>
        <ScoreCard
          label="SEO"
          value={
            scores.seo != null ? `${Math.round(scores.seo * 100)}%` : null
          }
          icon={Search}
          color="from-violet-500 to-purple-600"
        />
        <ScoreCard
          label="GEO"
          value={scores.geo}
          icon={Globe}
          color="from-cyan-500 to-blue-600"
          suffix="/100"
        />
        <ScoreCard
          label={t("chat.community")}
          value={scores.community_hits}
          icon={MessageCircle}
          color="from-pink-500 to-rose-600"
          suffix={t("chat.communityHitsSuffix")}
        />
        <ScoreCard
          label="SERP"
          value={
            scores.serp_tracked > 0
              ? `${scores.serp_top10}/${scores.serp_tracked}`
              : null
          }
          icon={TrendingUp}
          color="from-emerald-500 to-teal-600"
          suffix={t("chat.serpInTop10Suffix")}
        />
      </div>

      {/* Keywords & Competitors */}
      <div className="grid gap-3 lg:grid-cols-2">
        {keywords.length > 0 && (
          <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-1.5">
              <Tag size={14} className="text-indigo-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t("chat.contextKeywords")}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {keywords.map((kw) => (
                <span
                  key={kw}
                  className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {competitors.length > 0 && (
          <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-1.5">
              <Target size={14} className="text-orange-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t("chat.contextCompetitors")}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {competitors.map((c) => (
                <span
                  key={c.label}
                  className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-700"
                >
                  {c.label}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Keyword gaps */}
      {keyword_gaps.length > 0 && (
        <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-4">
          <div className="mb-2 flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-amber-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600">
              {t("chat.contextGaps")}
            </span>
            <span className="text-[11px] text-amber-500">
              {t("chat.gapNote")}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {keyword_gaps.map((gap) => (
              <span
                key={gap}
                className="rounded-full border border-amber-200 bg-white px-2.5 py-1 text-xs font-medium text-amber-800"
              >
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {t("chat.contextFindings")}
          </p>
          <div className="space-y-1.5">
            {findings.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-slate-600">
                <SeverityDot severity={f.severity} />
                <span className="text-[11px] font-medium uppercase text-slate-400 w-14 shrink-0">
                  {f.domain}
                </span>
                {f.title}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick action suggestions */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          {t("chat.contextQuickStart")}
        </p>
        <div className={compact ? "grid gap-2" : "grid grid-cols-2 gap-2"}>
          {suggestions.map((s) => (
            <button
              key={s.label}
              onClick={() => onSuggest(s.prompt)}
              className="rounded-xl border border-slate-100 bg-white p-3 text-left text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-indigo-200 hover:bg-indigo-50/50 hover:text-indigo-700 hover:shadow active:scale-[0.98]"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
