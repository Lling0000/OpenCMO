import { Link, useLocation } from "react-router";
import { useI18n } from "../../i18n";
import type { TranslationKey } from "../../i18n";

const OVERVIEW_TAB = { path: "", labelKey: "project.overview" as const };

const TAB_GROUPS: Array<{
  titleKey: TranslationKey;
  step: number;
  accent: string;       // border + badge color
  accentBg: string;     // light background tint
  activeBg: string;     // active tab pill
  tabs: Array<{ path: string; labelKey: TranslationKey }>;
}> = [
  {
    titleKey: "project.tabGroupObserve",
    step: 1,
    accent: "border-blue-200 text-blue-600",
    accentBg: "bg-blue-50/60",
    activeBg: "bg-blue-600 text-white shadow-sm shadow-blue-200",
    tabs: [
      { path: "/seo", labelKey: "project.seo" },
      { path: "/geo", labelKey: "project.geo" },
      { path: "/serp", labelKey: "project.serp" },
      { path: "/community", labelKey: "project.community" },
      { path: "/graph", labelKey: "project.graph" },
    ],
  },
  {
    titleKey: "project.tabGroupDecide",
    step: 2,
    accent: "border-amber-200 text-amber-600",
    accentBg: "bg-amber-50/60",
    activeBg: "bg-amber-600 text-white shadow-sm shadow-amber-200",
    tabs: [
      { path: "/reports", labelKey: "project.reports" },
      { path: "/knowledge", labelKey: "knowledge.title" },
      { path: "/performance", labelKey: "project.performance" },
    ],
  },
  {
    titleKey: "project.tabGroupExecute",
    step: 3,
    accent: "border-emerald-200 text-emerald-600",
    accentBg: "bg-emerald-50/60",
    activeBg: "bg-emerald-600 text-white shadow-sm shadow-emerald-200",
    tabs: [
      { path: "/content", labelKey: "project.content" },
      { path: "/brand-kit", labelKey: "project.brandKit" },
      { path: "/github-leads", labelKey: "project.githubLeads" },
      { path: "/monitors", labelKey: "project.monitors" },
    ],
  },
];

export function ProjectTabs({ projectId }: { projectId: number }) {
  const { pathname } = useLocation();
  const { t } = useI18n();
  const base = `/projects/${projectId}`;

  return (
    <div className="mb-8 space-y-3">
      {/* Overview pill */}
      <div className="inline-flex max-w-full items-center gap-1 rounded-2xl bg-slate-100/80 p-1.5">
        <Link
          to={base}
          className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
            pathname === base
              ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80"
              : "text-slate-500 hover:bg-black/[0.02] hover:text-slate-900"
          }`}
        >
          {t(OVERVIEW_TAB.labelKey)}
        </Link>
      </div>

      {/* Three-step navigation */}
      <div className="grid gap-3 xl:grid-cols-3">
        {TAB_GROUPS.map((group) => (
          <div
            key={group.titleKey}
            className={`rounded-2xl border ${group.accent.split(" ")[0]} ${group.accentBg} p-1.5`}
          >
            {/* Step badge + title */}
            <div className="flex items-center gap-2 px-2.5 pt-2 pb-1">
              <span
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${group.accent.split(" ").slice(1).join(" ")} bg-white ring-1 ring-current/20`}
              >
                {group.step}
              </span>
              <span className={`text-xs font-semibold tracking-wide ${group.accent.split(" ").slice(1).join(" ")}`}>
                {t(group.titleKey)}
              </span>
            </div>

            {/* Tab pills */}
            <div className="mt-1 flex flex-wrap gap-1.5">
              {group.tabs.map(({ path, labelKey }) => {
                const to = `${base}${path}`;
                const active = pathname === to;
                return (
                  <Link
                    key={path}
                    to={to}
                    className={`whitespace-nowrap rounded-xl border px-4 py-2 text-sm font-medium transition-all duration-200 ${
                      active
                        ? `${group.activeBg} border-transparent`
                        : "border-white/80 bg-white/60 text-slate-700 shadow-sm hover:bg-white hover:shadow-md"
                    }`}
                  >
                    {t(labelKey)}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
