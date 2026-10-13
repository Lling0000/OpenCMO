import { useState, type FormEvent } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Github,
  Globe,
  MessageSquareText,
  MonitorPlay,
  Search,
  type LucideIcon,
} from "lucide-react";
import { Link, useNavigate } from "react-router";
import { SiteFooter } from "../components/layout/SiteFooter";
import { PublicSiteHeader } from "../components/marketing/PublicSiteHeader";
import { SectionReveal } from "../components/marketing/SectionReveal";
import { BuiltInOpen } from "../components/marketing/BuiltInOpen";
import { useAuth } from "../components/auth/useAuth";
import {
  PUBLIC_HOME_NAV,
  getContactPath,
} from "../content/marketing";
import { usePublicPageMetadata } from "../hooks/usePublicPageMetadata";
import { usePublicSeoLocale } from "../hooks/usePublicSeoLocale";
import { useI18n } from "../i18n";
import { normalizeWebsiteUrl } from "../utils/url";

const GITHUB_REPO_URL = "https://github.com/Lling0000/OpenCMO";
const CONTACT_EMAIL = "hello@aidcmo.com";

// Neutral signal lanes (kept from old landing — no B2B baggage).
// These describe what OpenCMO actually does, in plain language.
const SIGNAL_LANES = [
  "landing.boardStream1",
  "landing.boardStream2",
  "landing.boardStream3",
] as const;

const PIPELINE_STAGES = [
  "landing.stage1",
  "landing.stage2",
  "landing.stage3",
  "landing.stage4",
  "landing.stage5",
  "landing.stage6",
] as const;

const HERO_BADGES = [
  "landing.heroBadgeOpenSource",
  "landing.heroBadgeLicense",
  "landing.heroBadgeSelfHost",
  "landing.heroBadgeByok",
] as const;

const PRODUCT_METRICS = [
  {
    label: "landing.productMetricSeoLabel",
    value: "14",
    detail: "landing.productMetricSeoDetail",
  },
  {
    label: "landing.productMetricAiLabel",
    value: "3",
    detail: "landing.productMetricAiDetail",
  },
  {
    label: "landing.productMetricCommunityLabel",
    value: "3",
    detail: "landing.productMetricCommunityDetail",
  },
] as const;

const PRODUCT_SURFACES: Array<{
  icon: LucideIcon;
  title: string;
  body: string;
}> = [
  {
    icon: Search,
    title: "landing.productSurfaceSeoTitle",
    body: "landing.productSurfaceSeoBody",
  },
  {
    icon: Globe,
    title: "landing.productSurfaceAiTitle",
    body: "landing.productSurfaceAiBody",
  },
  {
    icon: MessageSquareText,
    title: "landing.productSurfaceCommunityTitle",
    body: "landing.productSurfaceCommunityBody",
  },
] as const;

const PRODUCT_ACTIONS = [
  "landing.productAction1",
  "landing.productAction2",
  "landing.productAction3",
] as const;

const PRODUCT_CARDS = [
  {
    title: "landing.productCardProjectTitle",
    body: "landing.productCardProjectDesc",
  },
  {
    title: "landing.productCardScanTitle",
    body: "landing.productCardScanDesc",
  },
  {
    title: "landing.productCardReviewTitle",
    body: "landing.productCardReviewDesc",
  },
] as const;

function ProductConsolePreview({ consoleHref = "/console" }: { consoleHref?: string }) {
  const { t } = useI18n();

  return (
    <div className="mx-auto mt-12 max-w-6xl overflow-hidden rounded-[2rem] border border-white/10 bg-[#f8fafc] text-slate-950 shadow-[0_34px_120px_rgba(0,0,0,0.34)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#082032] text-white">
            <Activity size={18} />
          </div>
          <div className="min-w-0 text-left">
            <p className="text-sm font-semibold text-slate-950">{t("landing.productPreviewTitle")}</p>
            <p className="truncate text-xs text-slate-500">{t("landing.productPreviewProject")}</p>
          </div>
        </div>
        <Link
          to={consoleHref}
          className="inline-flex items-center gap-2 rounded-full bg-[#082032] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0c2538]"
        >
          {t("landing.workspaceCta")}
          <ArrowRight size={14} />
        </Link>
      </div>

      <div className="grid gap-0 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-slate-50/80 p-5 lg:border-b-0 lg:border-r">
          <p className="text-xs font-semibold text-slate-500">{t("landing.productPreviewSidebarTitle")}</p>
          <div className="mt-4 space-y-2">
            {PRODUCT_SURFACES.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="flex items-start gap-3 rounded-xl bg-white px-3 py-3 shadow-sm">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                    <Icon size={15} />
                  </div>
                  <div className="min-w-0 text-left">
                    <p className="text-sm font-semibold text-slate-950">{t(item.title as never)}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{t(item.body as never)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        <div className="p-5 sm:p-6">
          <div className="grid gap-3 sm:grid-cols-3">
            {PRODUCT_METRICS.map((item) => (
              <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm">
                <p className="text-xs font-semibold text-slate-500">{t(item.label as never)}</p>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{item.value}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{t(item.detail as never)}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-slate-500">{t("landing.productPreviewPipelineLabel")}</p>
                  <h2 className="mt-2 text-xl font-semibold text-slate-950">{t("landing.productPreviewPipelineTitle")}</h2>
                </div>
                <BarChart3 size={20} className="text-[#c96f45]" />
              </div>
              <div className="mt-5 grid gap-2 sm:grid-cols-3">
                {["landing.stage2", "landing.stage4", "landing.stage6"].map((key, index) => (
                  <div key={key} className="rounded-xl bg-slate-50 px-3 py-3">
                    <p className="text-xs font-semibold text-slate-400">0{index + 1}</p>
                    <p className="mt-2 text-sm font-semibold text-slate-800">{t(key as never)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-5 space-y-2">
                {PRODUCT_ACTIONS.map((key) => (
                  <div key={key} className="flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50/70 px-3 py-3">
                    <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-700" />
                    <p className="text-sm leading-6 text-slate-800">{t(key)}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-[#082032] p-5 text-left text-white shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
                <MessageSquareText size={18} />
              </div>
              <h2 className="mt-5 text-xl font-semibold">{t("landing.productPreviewReportTitle")}</h2>
              <p className="mt-3 text-sm leading-6 text-white/70">{t("landing.productPreviewReportBody")}</p>
              <div className="mt-5 rounded-xl border border-white/10 bg-white/8 px-3 py-3">
                <p className="text-xs font-semibold text-white/45">{t("landing.productPreviewReviewLabel")}</p>
                <p className="mt-2 text-sm font-semibold text-white">{t("landing.productPreviewReviewValue")}</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

export function LandingPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const seoLocale = usePublicSeoLocale();
  const navigate = useNavigate();
  const [homepageUrl, setHomepageUrl] = useState("");
  const normalizedHomepageUrl = homepageUrl.trim() ? normalizeWebsiteUrl(homepageUrl.trim()) : "";
  const consoleTarget = normalizedHomepageUrl
    ? `/console?url=${encodeURIComponent(normalizedHomepageUrl)}`
    : "/console";
  const consoleHref = auth.isAuthenticated
    ? consoleTarget
    : normalizedHomepageUrl
      ? `/signup?url=${encodeURIComponent(normalizedHomepageUrl)}`
      : "/signup";

  usePublicPageMetadata({
    title: t("landing.metaTitle"),
    description: t("landing.metaDescription"),
    basePath: "/",
  });

  const handleHeroUrlSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const rawUrl = homepageUrl.trim();
    if (!rawUrl) return;
    navigate(consoleHref);
  };

  return (
    <div className="min-h-screen bg-[#08141f] text-white">
      <PublicSiteHeader items={PUBLIC_HOME_NAV} theme="dark" consoleHref={consoleHref} />

      <main className="overflow-hidden">
        {/* Hero ----------------------------------------------------- */}
        <section className="relative">
          <div className="mx-auto max-w-7xl px-4 pb-14 pt-16 text-center sm:pb-16 sm:pt-20 lg:px-8">
            <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
              {t("landing.heroEyebrow")}
            </p>
            <h1 className="font-display mx-auto mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
              {t("landing.heroTitle")}
            </h1>
            <p className="mx-auto mt-7 max-w-3xl text-lg leading-8 text-white/70 sm:text-xl sm:leading-9">
              {t("landing.heroSubtitle")}
            </p>

            <form onSubmit={handleHeroUrlSubmit} className="mx-auto mt-9 max-w-3xl">
              <div className="flex flex-col gap-3 rounded-[1.75rem] border border-white/12 bg-white/8 p-2 shadow-[0_18px_60px_rgba(0,0,0,0.22)] backdrop-blur sm:flex-row sm:items-center">
                <div className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl bg-white px-4 py-3 text-left text-slate-950">
                  <Search size={18} className="shrink-0 text-slate-400" />
                  <input
                    value={homepageUrl}
                    onChange={(event) => setHomepageUrl(event.target.value)}
                    type="text"
                    inputMode="url"
                    aria-label={t("landing.heroUrlPlaceholder")}
                    placeholder={t("landing.heroUrlPlaceholder")}
                    className="min-w-0 flex-1 bg-transparent text-base font-medium text-slate-950 outline-none placeholder:text-slate-400"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!homepageUrl.trim()}
                  className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-[#f7ecde] px-6 text-sm font-semibold text-[#082032] transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t("landing.heroUrlCta")}
                  <ArrowRight size={15} />
                </button>
              </div>
            </form>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-white/55">
              {t("landing.heroTrialNote")}
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <Link
                to={consoleHref}
                className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-7 py-4 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
              >
                <MonitorPlay size={16} />
                {t("landing.workspaceCta")}
                <ArrowRight size={16} />
              </Link>
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-7 py-4 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
              >
                <Github size={16} />
                {t("landing.heroSecondaryCta")}
                <ExternalLink size={14} />
              </a>
            </div>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
              {HERO_BADGES.map((key) => (
                <span
                  key={key}
                  className="rounded-full border border-white/10 bg-white/4 px-3 py-1.5 text-xs font-semibold text-white/65"
                >
                  {t(key)}
                </span>
              ))}
            </div>

            <ProductConsolePreview consoleHref={consoleHref} />
          </div>
        </section>

        {/* Built in the open --------------------------------------- */}
        <BuiltInOpen />

        {/* What OpenCMO does --------------------------------------- */}
        <section className="bg-[#08141f]">
          <div className="mx-auto max-w-7xl px-4 py-20 lg:px-8 lg:py-24">
            <SectionReveal>
              <div className="max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                  {t("landing.signalBoardEyebrow")}
                </p>
                <h2 className="font-display mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {t("landing.signalBoardTitle")}
                </h2>
                <p className="mt-4 text-base leading-7 text-white/70">
                  {t("landing.signalBoardSummary")}
                </p>
              </div>
            </SectionReveal>

            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {SIGNAL_LANES.map((key, idx) => (
                <SectionReveal key={key} delay={idx * 0.05}>
                  <div className="rounded-2xl border border-white/8 bg-white/4 p-6">
                    <p className="text-base leading-7 text-white/80">{t(key)}</p>
                  </div>
                </SectionReveal>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline ------------------------------------------------ */}
        <section className="border-y border-white/8 bg-[#06121d]">
          <div className="mx-auto max-w-7xl px-4 py-20 lg:px-8 lg:py-24">
            <SectionReveal>
              <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                {t("landing.boardStagesTitle")}
              </p>
              <h2 className="font-display mt-4 max-w-2xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {t("landing.metricPipelineValue")} · {t("landing.metricChannelsValue")}
              </h2>
            </SectionReveal>

            <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {PIPELINE_STAGES.map((key, idx) => (
                <SectionReveal key={key} delay={idx * 0.04}>
                  <div className="flex items-start gap-3 rounded-xl border border-white/8 bg-white/3 px-5 py-4">
                    <span className="mt-0.5 inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-white/8 text-xs font-semibold text-white/85">
                      {idx + 1}
                    </span>
                    <span className="text-sm font-semibold text-white/85">
                      {t(key)}
                    </span>
                  </div>
                </SectionReveal>
              ))}
            </div>
          </div>
        </section>

        {/* Product workflow ----------------------------------------- */}
        <section className="bg-[#08141f]">
          <div className="mx-auto max-w-7xl px-4 py-20 lg:px-8 lg:py-24">
            <SectionReveal>
              <div className="max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                  {t("landing.productSectionEyebrow")}
                </p>
                <h2 className="font-display mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {t("landing.productSectionTitle")}
                </h2>
                <p className="mt-4 text-base leading-7 text-white/70">
                  {t("landing.productSectionSubtitle")}
                </p>
              </div>
            </SectionReveal>

            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {PRODUCT_CARDS.map((item, idx) => (
                <SectionReveal key={item.title} delay={idx * 0.05}>
                  <div className="flex h-full flex-col rounded-2xl border border-white/8 bg-white/4 p-6">
                    <h3 className="text-xl font-semibold text-white">{t(item.title)}</h3>
                    <p className="mt-3 flex-1 text-sm leading-6 text-white/66">{t(item.body)}</p>
                    <Link
                      to={consoleHref}
                      className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white transition-colors hover:text-[#f7ecde]"
                    >
                      {t("landing.workspaceCta")}
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                </SectionReveal>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA ----------------------------------------------- */}
        <section className="bg-[#06121d]">
          <div className="mx-auto max-w-5xl px-4 py-20 text-center lg:px-8 lg:py-24">
            <SectionReveal>
              <h2 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-5xl">
                {t("landing.finalProductTitle")}
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-base text-white/70">
                {t("landing.finalProductSubtitle")}
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  to={consoleHref}
                  className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-7 py-4 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
                >
                  {t("landing.workspaceCta")}
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to={getContactPath(seoLocale)}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-7 py-4 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
                >
                  {t("landing.contactCta")}
                </Link>
                <a
                  href={GITHUB_REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-semibold text-white/65 transition-colors hover:text-white"
                >
                  {t("landing.heroSecondaryCta")}
                  <ExternalLink size={14} />
                </a>
              </div>
              <p className="mt-10 text-sm text-white/55">
                {t("landing.emailLabel")} ·{" "}
                <a
                  href={`mailto:${CONTACT_EMAIL}`}
                  className="text-white/85 underline-offset-4 hover:underline"
                >
                  {CONTACT_EMAIL}
                </a>
              </p>
            </SectionReveal>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
