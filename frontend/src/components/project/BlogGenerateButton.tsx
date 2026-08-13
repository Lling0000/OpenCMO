import { useEffect, useState } from "react";
import { Loader2, PenLine, RotateCw, XCircle, Eye } from "lucide-react";
import { useBlogGenerate } from "../../hooks/useBlogGen";
import { useTaskPoll } from "../../hooks/useTasks";
import { useQueryClient } from "@tanstack/react-query";
import { useI18n } from "../../i18n";
import type { BlogStyle, MarketingSkillId } from "../../types";
import type { TranslationKey } from "../../i18n";

const STYLES: { value: BlogStyle; labelKey: TranslationKey; descKey: TranslationKey }[] = [
  { value: "launch", labelKey: "blogGen.style.launch", descKey: "blogGen.style.launchDesc" },
  { value: "case_study", labelKey: "blogGen.style.case_study", descKey: "blogGen.style.case_studyDesc" },
  { value: "comparison", labelKey: "blogGen.style.comparison", descKey: "blogGen.style.comparisonDesc" },
  { value: "thought_leadership", labelKey: "blogGen.style.thought_leadership", descKey: "blogGen.style.thought_leadershipDesc" },
];

const MARKETING_SKILLS: { value: MarketingSkillId; labelKey: TranslationKey; descKey: TranslationKey }[] = [
  { value: "content_strategy", labelKey: "blogGen.skill.content_strategy", descKey: "blogGen.skill.content_strategyDesc" },
  { value: "copywriting", labelKey: "blogGen.skill.copywriting", descKey: "blogGen.skill.copywritingDesc" },
  { value: "ai_seo", labelKey: "blogGen.skill.ai_seo", descKey: "blogGen.skill.ai_seoDesc" },
  { value: "competitor_alternatives", labelKey: "blogGen.skill.competitor_alternatives", descKey: "blogGen.skill.competitor_alternativesDesc" },
  { value: "programmatic_seo", labelKey: "blogGen.skill.programmatic_seo", descKey: "blogGen.skill.programmatic_seoDesc" },
  { value: "directory_submissions", labelKey: "blogGen.skill.directory_submissions", descKey: "blogGen.skill.directory_submissionsDesc" },
];

export function BlogGenerateButton({
  projectId,
  onViewDrafts,
}: {
  projectId: number;
  onViewDrafts?: () => void;
}) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [style, setStyle] = useState<BlogStyle>("launch");
  const [skillId, setSkillId] = useState<MarketingSkillId>("content_strategy");
  const [bilingual, setBilingual] = useState(false);

  const blogGenerate = useBlogGenerate(projectId);
  const { data: task } = useTaskPoll(taskId);
  const qc = useQueryClient();
  const { t, locale } = useI18n();

  const status = task?.status;
  const progress = task?.progress;
  const latestPhase = progress?.length ? progress[progress.length - 1] : null;

  useEffect(() => {
    if (status === "completed" || status === "failed") {
      qc.invalidateQueries({ queryKey: ["project-summary", projectId] });
      qc.invalidateQueries({ queryKey: ["blog-drafts", projectId] });
    }
  }, [projectId, qc, status]);

  const handleGenerate = async () => {
    setShowConfig(false);
    try {
      const result = await blogGenerate.mutateAsync({ style, skill_id: skillId, bilingual, language: locale });
      setTaskId(result.task_id);
    } catch {
      // mutation error handled by TanStack
    }
  };

  // Running state
  if (status === "running" || status === "pending") {
    return (
      <div className="space-y-1">
        <span className="flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600">
          <Loader2 size={14} className="animate-spin" />
          {t("blogGen.generating")}
        </span>
        {latestPhase?.summary && (
          <p className="px-1 text-[11px] text-slate-500">{latestPhase.summary}</p>
        )}
      </div>
    );
  }

  // Completed state
  if (status === "completed") {
    return (
      <div className="flex items-center gap-2">
        {onViewDrafts && (
          <button
            type="button"
            onClick={onViewDrafts}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
          >
            <Eye size={13} />
            {t("blogGen.viewDraft")}
          </button>
        )}
        <button
          type="button"
          onClick={() => { setTaskId(null); setShowConfig(true); }}
          className="flex items-center gap-1.5 rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 transition-colors hover:bg-sky-100"
        >
          <RotateCw size={13} />
          {t("blogGen.regenerate")}
        </button>
      </div>
    );
  }

  // Failed state
  if (status === "failed") {
    return (
      <div className="flex items-center gap-2">
        <span
          className="flex items-center gap-1.5 rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-600"
          title={task?.error ?? ""}
        >
          <XCircle size={14} />
          {t("blogGen.failed")}
        </span>
        <button
          type="button"
          onClick={() => { setTaskId(null); setShowConfig(true); }}
          className="flex items-center gap-1.5 rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 transition-colors hover:bg-sky-100"
        >
          <RotateCw size={13} />
          {t("blogGen.retry")}
        </button>
      </div>
    );
  }

  // Config popover
  if (showConfig) {
    return (
      <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold text-slate-700">{t("blogGen.selectStyle")}</p>
        <div className="mt-2 space-y-2">
          {STYLES.map((s) => (
            <label
              key={s.value}
              className={`flex cursor-pointer items-start gap-2 rounded-xl border px-3 py-2 transition-colors ${
                style === s.value
                  ? "border-indigo-300 bg-indigo-50/50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                name="blogStyle"
                value={s.value}
                checked={style === s.value}
                onChange={() => setStyle(s.value)}
                className="mt-0.5"
              />
              <div>
                <span className="text-xs font-medium text-slate-900">{t(s.labelKey)}</span>
                <p className="text-[11px] leading-4 text-slate-500">{t(s.descKey)}</p>
              </div>
            </label>
          ))}
        </div>

        <p className="mt-4 text-xs font-semibold text-slate-700">{t("blogGen.selectSkill")}</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {MARKETING_SKILLS.map((s) => (
            <label
              key={s.value}
              className={`flex cursor-pointer items-start gap-2 rounded-xl border px-3 py-2 transition-colors ${
                skillId === s.value
                  ? "border-emerald-300 bg-emerald-50/50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                name="marketingSkill"
                value={s.value}
                checked={skillId === s.value}
                onChange={() => setSkillId(s.value)}
                className="mt-0.5"
              />
              <div className="min-w-0">
                <span className="text-xs font-medium text-slate-900">{t(s.labelKey)}</span>
                <p className="text-[11px] leading-4 text-slate-500">{t(s.descKey)}</p>
              </div>
            </label>
          ))}
        </div>

        <label className="mt-3 flex items-center gap-2">
          <input
            type="checkbox"
            checked={bilingual}
            onChange={(e) => setBilingual(e.target.checked)}
          />
          <span className="text-xs text-slate-700">{t("blogGen.bilingual")}</span>
        </label>

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={blogGenerate.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PenLine size={12} />
            {t("blogGen.generate")}
          </button>
          <button
            type="button"
            onClick={() => setShowConfig(false)}
            className="rounded-lg px-3 py-1.5 text-xs text-slate-500 transition-colors hover:bg-slate-100"
          >
            {t("blogGen.cancel")}
          </button>
        </div>
      </div>
    );
  }

  // Idle state
  return (
    <button
      type="button"
      onClick={() => setShowConfig(true)}
      disabled={blogGenerate.isPending}
      className="flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <PenLine size={12} />
      {t("blogGen.generate")}
    </button>
  );
}
