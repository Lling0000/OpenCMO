import { ExternalLink, Github, Link2, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { getBlogIndexPath, getLandingPath, getServicesPath } from "../../content/marketing";
import { useSiteStats } from "../../hooks/useSiteStats";
import { usePublicSeoLocale } from "../../hooks/usePublicSeoLocale";
import { useI18n } from "../../i18n";
import { getSeoLocaleFromLocale } from "../../utils/publicRoutes";

const GITHUB_REPO = "https://github.com/Lling0000/OpenCMO";
const CONTACT_EMAIL = "hello@aidcmo.com";
const FRIEND_LINKS = [
  {
    href: "https://okara.ai/",
    labelKey: "siteFooter.okara",
  },
] as const;

type SiteFooterProps = {
  variant?: "workspace" | "public";
};

export function SiteFooter({ variant = "workspace" }: SiteFooterProps) {
  const { t, locale } = useI18n();
  const { data: siteStats } = useSiteStats();
  const publicSeoLocale = usePublicSeoLocale();
  const seoLocale = variant === "public" ? publicSeoLocale : getSeoLocaleFromLocale(locale);
  const numberFormatter = new Intl.NumberFormat(locale);
  const landingHref = getLandingPath(seoLocale);
  const blogHref = getBlogIndexPath(seoLocale);
  const servicesHref = getServicesPath(seoLocale);

  if (variant === "public") {
    return (
      <footer className="mt-12 pb-8">
        <div className="overflow-hidden rounded-[2.8rem] bg-[#08131d] text-white shadow-[0_28px_100px_rgba(8,19,29,0.18)]">
          <div className="grid gap-10 px-6 py-8 sm:px-8 sm:py-10 lg:grid-cols-[minmax(0,1fr)_420px]">
            <div>
              <Link to={landingHref} className="flex w-fit items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-white">
                  <Sparkles size={18} />
                </div>
                <div>
                  <p className="font-display text-2xl font-semibold tracking-tight">aidCMO</p>
                  <p className="text-xs text-white/48">{t("landing.headerTagline")}</p>
                </div>
              </Link>

              <p className="mt-5 max-w-xl text-base leading-8 text-white/68">
                {t("siteFooter.description")}
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                <a
                  href={`mailto:${CONTACT_EMAIL}`}
                  className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-4 py-3 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
                >
                  {t("siteFooter.contactEmail")}
                </a>
                <Link
                  to={blogHref}
                  className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold text-white/86 transition-colors hover:border-white/22 hover:bg-white/10 hover:text-white"
                >
                  {t("landing.navBlog")}
                </Link>
                <Link
                  to={servicesHref}
                  className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-4 py-3 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
                >
                  {t("landing.primaryCta")}
                </Link>
                <Link
                  to="/console"
                  className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold text-white/86 transition-colors hover:border-white/22 hover:bg-white/10 hover:text-white"
                >
                  {t("landing.workspaceCta")}
                </Link>
              </div>
            </div>

            <div className="grid gap-4">
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="flex items-center justify-between rounded-[1.8rem] border border-white/10 bg-white/5 px-5 py-4 transition-colors hover:bg-white/8"
              >
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/40">
                    {t("siteFooter.contactEmail")}
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">{CONTACT_EMAIL}</p>
                </div>
                <ExternalLink size={18} className="text-white/68" />
              </a>

              <a
                href={GITHUB_REPO}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between rounded-[1.8rem] border border-white/10 bg-white/5 px-5 py-4 transition-colors hover:bg-white/8"
              >
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/40">
                    {t("siteFooter.sourceCode")}
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">{t("siteFooter.githubRepo")}</p>
                </div>
                <Github size={18} className="text-white/68" />
              </a>

              {FRIEND_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-[1.8rem] border border-white/10 bg-white/5 px-5 py-4 transition-colors hover:bg-white/8"
                >
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/40">
                      {t("siteFooter.friendLinks")}
                    </p>
                    <p className="mt-2 text-base font-semibold text-white">{t(link.labelKey)}</p>
                  </div>
                  <ExternalLink size={18} className="text-white/68" />
                </a>
              ))}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-[1.8rem] border border-white/10 bg-white/5 px-5 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/40">
                    {t("siteFooter.totalVisits")}
                  </p>
                  <p className="mt-3 text-2xl font-semibold text-white">
                    {numberFormatter.format(siteStats?.total_visits ?? 0)}
                  </p>
                </div>
                <div className="rounded-[1.8rem] border border-white/10 bg-white/5 px-5 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/40">
                    {t("siteFooter.uniqueVisitors")}
                  </p>
                  <p className="mt-3 text-2xl font-semibold text-white">
                    {numberFormatter.format(siteStats?.unique_visitors ?? 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer className="mt-10 border-t border-slate-200/80 pt-6 pb-8 text-sm text-slate-500">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-slate-900">OpenCMO</p>
            <p className="max-w-sm leading-6 text-slate-500">
              {t("siteFooter.description")}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href={GITHUB_REPO}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:text-slate-900"
            >
              <Github size={14} />
              {t("siteFooter.sourceCode")}
            </a>
            {FRIEND_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:text-slate-900"
              >
                <Link2 size={14} />
                {t(link.labelKey)}
              </a>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t("siteFooter.totalVisits")}
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
              {numberFormatter.format(siteStats?.total_visits ?? 0)}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t("siteFooter.uniqueVisitors")}
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
              {numberFormatter.format(siteStats?.unique_visitors ?? 0)}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
