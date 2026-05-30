import { useState } from "react";
import type { ElementType, ReactNode } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle, Info, AlertCircle, CheckCircle,
  Zap, FileCheck, Search, Sparkles,
} from "lucide-react";
import { apiJson } from "../../api/client";
import { useI18n } from "../../i18n";
import type { TranslationKey } from "../../i18n";

interface ActionItem {
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
}

const CTA_CONFIG: Record<string, { labelKey: TranslationKey; icon: ElementType; color: string }> = {
  view_data: { labelKey: "actionFeed.viewDetails", icon: Search, color: "bg-sky-500 hover:bg-sky-400 shadow-[0_8px_24px_rgba(14,165,233,0.25)]" },
  review_approval: { labelKey: "actionFeed.reviewDraft", icon: FileCheck, color: "bg-amber-500 hover:bg-amber-400 shadow-[0_8px_24px_rgba(245,158,11,0.25)]" },
  generate_content: { labelKey: "actionFeed.generateFix", icon: Zap, color: "bg-violet-500 hover:bg-violet-400 shadow-[0_8px_24px_rgba(139,92,246,0.25)]" },
  start_chat: { labelKey: "actionFeed.discuss", icon: Sparkles, color: "bg-emerald-500 hover:bg-emerald-400 shadow-[0_8px_24px_rgba(16,185,129,0.25)]" },
};

const SEV_STYLES: Record<string, { border: string; icon: ElementType; iconColor: string }> = {
  critical: { border: "border-l-rose-500", icon: AlertCircle, iconColor: "text-rose-500" },
  warning: { border: "border-l-amber-500", icon: AlertTriangle, iconColor: "text-amber-500" },
  info: { border: "border-l-sky-500", icon: Info, iconColor: "text-sky-500" },
};

const TYPE_LABEL_KEYS: Record<ActionItem["type"], TranslationKey> = {
  insight: "actionFeed.typeInsight",
  approval: "actionFeed.typeApproval",
  finding: "actionFeed.typeFinding",
};

const CTA_RECOMMENDATION_KEYS: Record<ActionItem["cta"], TranslationKey> = {
  view_data: "actionFeed.recommendViewData",
  review_approval: "actionFeed.recommendReviewApproval",
  generate_content: "actionFeed.recommendGenerateContent",
  start_chat: "actionFeed.recommendStartChat",
};

const STATUS_LABEL_KEYS: Record<ActionItem["cta"], TranslationKey> = {
  view_data: "actionFeed.needsData",
  review_approval: "actionFeed.pendingReview",
  generate_content: "actionFeed.readyToGenerate",
  start_chat: "actionFeed.readyToDiscuss",
};

function ActionField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        {label}
      </p>
      <div className="mt-1 text-sm leading-6 text-slate-700">{children}</div>
    </div>
  );
}

export function ActionFeed({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const [quickLoading, setQuickLoading] = useState<number | null>(null);
  const { t, locale } = useI18n();
  const { data: items = [], isLoading: loading } = useQuery({
    queryKey: ["action-feed", projectId, locale],
    queryFn: () => apiJson<ActionItem[]>(`/projects/${projectId}/action-feed?lang=${locale}`),
  });

  const handleCta = async (item: ActionItem) => {
    if (item.cta === "review_approval") {
      navigate("/approvals");
      return;
    }
    if (item.cta === "view_data" && item.action_route) {
      navigate(item.action_route);
      return;
    }
    if (item.cta === "generate_content" && item.insight_id) {
      setQuickLoading(item.id);
      try {
        await apiJson(`/projects/${projectId}/quick-generate`, {
          method: "POST",
          body: JSON.stringify({ insight_id: item.insight_id }),
        });
        navigate("/approvals");
      } catch {
        // ignore
      } finally {
        setQuickLoading(null);
      }
      return;
    }
    if (item.cta === "start_chat") {
      navigate(`/chat?project_id=${projectId}`);
      return;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-emerald-300 bg-emerald-50/50 p-8 text-center">
        <CheckCircle className="mx-auto h-10 w-10 text-emerald-400" />
        <h3 className="mt-3 text-sm font-semibold text-emerald-800">{t("actionFeed.allClear")}</h3>
        <p className="mt-1 text-xs text-emerald-600">
          {t("actionFeed.allClearDesc")}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <Zap className="h-4.5 w-4.5 text-violet-500" />
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-600">
          {t("actionFeed.title")}
        </h2>
        <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-700">
          {items.length}
        </span>
      </div>

      {items.map((item) => {
        const sev = (SEV_STYLES[item.severity] ?? SEV_STYLES.info)!;
        const cta = (CTA_CONFIG[item.cta] ?? CTA_CONFIG.view_data)!;
        const CtaIcon = cta.icon;
        const SevIcon = sev.icon;
        const isLoading = quickLoading === item.id;

        return (
          <div
            key={`${item.type}-${item.id}`}
            className={`group rounded-2xl border border-slate-200/70 border-l-4 bg-white/90 p-4 shadow-sm backdrop-blur-sm transition-all hover:shadow-md ${sev.border}`}
          >
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-50">
                <SevIcon size={16} className={sev.iconColor} />
              </div>

              <div className="min-w-0 flex-1 space-y-4">
                <div className="grid gap-4 lg:grid-cols-2">
                  <ActionField label={t("actionFeed.problem")}>
                    <p className="font-semibold text-slate-900">{item.title}</p>
                  </ActionField>

                  <ActionField label={t("actionFeed.impact")}>
                    <p>{item.summary}</p>
                  </ActionField>

                  <ActionField label={t("actionFeed.recommendedAction")}>
                    <p>{t(CTA_RECOMMENDATION_KEYS[item.cta])}</p>
                  </ActionField>

                  <ActionField label={t("actionFeed.statusOwner")}>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                        {t(STATUS_LABEL_KEYS[item.cta])}
                      </span>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">
                        {t(TYPE_LABEL_KEYS[item.type])}
                      </span>
                    </div>
                  </ActionField>
                </div>
              </div>

              <button
                onClick={() => handleCta(item)}
                disabled={isLoading}
                className={`inline-flex w-full shrink-0 items-center justify-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 md:w-auto ${cta.color}`}
              >
                {isLoading ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                ) : (
                  <CtaIcon size={14} />
                )}
                {t(cta.labelKey)}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
