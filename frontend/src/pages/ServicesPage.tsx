import { Link } from "react-router";
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  KeyRound,
  LayoutDashboard,
  Mail,
  ServerCog,
  ShieldCheck,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { PublicSiteHeader } from "../components/marketing/PublicSiteHeader";
import { SiteFooter } from "../components/layout/SiteFooter";
import { useI18n } from "../i18n";
import type { TranslationKey } from "../i18n";
import { usePublicPageMetadata } from "../hooks/usePublicPageMetadata";
import { PUBLIC_HOME_NAV } from "../content/marketing";

const CONTACT_EMAIL = "hello@aidcmo.com";
const GITHUB_REPO_URL = "https://github.com/Lling0000/OpenCMO";

type ServiceCard = {
  icon: LucideIcon;
  title: TranslationKey;
  body: TranslationKey;
};

const HERO_PROOFS = [
  "service.audit.heroProofPrivate",
  "service.audit.heroProofByok",
  "service.audit.heroProofWorkflow",
] as const;

const SCOPE_CARDS: ServiceCard[] = [
  {
    icon: ServerCog,
    title: "service.audit.scopeDeploymentTitle",
    body: "service.audit.scopeDeploymentBody",
  },
  {
    icon: Workflow,
    title: "service.audit.scopeWorkflowTitle",
    body: "service.audit.scopeWorkflowBody",
  },
  {
    icon: KeyRound,
    title: "service.audit.scopeByokTitle",
    body: "service.audit.scopeByokBody",
  },
  {
    icon: ShieldCheck,
    title: "service.audit.scopeGovernanceTitle",
    body: "service.audit.scopeGovernanceBody",
  },
];

const PROCESS_STEPS = [
  "service.audit.processStep1",
  "service.audit.processStep2",
  "service.audit.processStep3",
  "service.audit.processStep4",
] as const;

const BRIEF_FIELDS = [
  "service.audit.briefField1",
  "service.audit.briefField2",
  "service.audit.briefField3",
  "service.audit.briefField4",
] as const;

export function ServicesPage() {
  const { t } = useI18n();

  usePublicPageMetadata({
    title: t("service.audit.metaTitle"),
    description: t("service.audit.metaDescription"),
    basePath: "/services",
  });

  return (
    <div className="min-h-screen bg-[#08141f] text-white">
      <PublicSiteHeader items={PUBLIC_HOME_NAV} theme="dark" />

      <main>
        <section className="border-b border-white/10">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 lg:grid-cols-[minmax(0,1fr)_420px] lg:px-8 lg:py-28">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                {t("service.audit.eyebrow")}
              </p>
              <h1 className="font-display mt-5 max-w-4xl text-5xl font-semibold tracking-tight text-white sm:text-6xl lg:text-7xl">
                {t("service.audit.heroTitle")}
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-white/72 sm:text-xl sm:leading-9">
                {t("service.audit.heroSubtitle")}
              </p>

              <div className="mt-9 flex flex-wrap gap-3">
                <a
                  href={`mailto:${CONTACT_EMAIL}`}
                  className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-7 py-4 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
                >
                  <Mail size={16} />
                  {t("service.audit.heroCta")}
                </a>
                <Link
                  to="/console"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-7 py-4 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
                >
                  <LayoutDashboard size={16} />
                  {t("service.audit.workspaceCta")}
                  <ArrowRight size={14} />
                </Link>
                <a
                  href={GITHUB_REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-7 py-4 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
                >
                  <Code2 size={16} />
                  {t("service.audit.githubCta")}
                  <ArrowRight size={14} />
                </a>
              </div>

              <div className="mt-8 flex flex-wrap gap-2">
                {HERO_PROOFS.map((key) => (
                  <span
                    key={key}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/68"
                  >
                    {t(key)}
                  </span>
                ))}
              </div>
            </div>

            <aside className="self-end rounded-lg border border-white/10 bg-white/6 p-6">
              <p className="text-sm font-semibold uppercase tracking-wider text-white/50">
                {t("service.audit.briefTitle")}
              </p>
              <p className="mt-3 text-base leading-7 text-white/75">
                {t("service.audit.briefSubtitle")}
              </p>
              <div className="mt-6 grid gap-3">
                {BRIEF_FIELDS.map((key) => (
                  <div key={key} className="flex items-start gap-3 rounded-lg bg-white/7 px-4 py-3">
                    <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-[#86c8bc]" />
                    <p className="text-sm leading-6 text-white/78">{t(key)}</p>
                  </div>
                ))}
              </div>
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-[#082032] transition-colors hover:bg-[#f7ecde]"
              >
                {CONTACT_EMAIL}
                <ArrowRight size={14} />
              </a>
            </aside>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-20 lg:px-8 lg:py-24">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
              {t("service.audit.scopeEyebrow")}
            </p>
            <h2 className="font-display mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              {t("service.audit.scopeTitle")}
            </h2>
            <p className="mt-4 text-base leading-7 text-white/68">
              {t("service.audit.scopeSubtitle")}
            </p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2">
            {SCOPE_CARDS.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="rounded-lg border border-white/10 bg-white/5 p-6">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#f7ecde] text-[#082032]">
                    <Icon size={18} />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-white">{t(item.title)}</h3>
                  <p className="mt-3 text-sm leading-7 text-white/66">{t(item.body)}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="border-y border-white/10 bg-[#06121d]">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 lg:grid-cols-[360px_minmax(0,1fr)] lg:px-8 lg:py-24">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                {t("service.audit.processEyebrow")}
              </p>
              <h2 className="font-display mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {t("service.audit.processTitle")}
              </h2>
              <p className="mt-4 text-base leading-7 text-white/68">
                {t("service.audit.processSubtitle")}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {PROCESS_STEPS.map((key, index) => (
                <div key={key} className="rounded-lg border border-white/10 bg-white/5 px-5 py-4">
                  <p className="text-xs font-semibold text-white/45">0{index + 1}</p>
                  <p className="mt-3 text-sm leading-7 text-white/78">{t(key)}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-20 lg:px-8 lg:py-24">
          <div className="grid gap-8 rounded-lg border border-white/10 bg-white/6 p-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:p-8">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-white/55">
                {t("service.audit.noteTitle")}
              </p>
              <h2 className="font-display mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {t("service.audit.finalTitle")}
              </h2>
              <p className="mt-4 text-base leading-8 text-white/68">
                {t("service.audit.noteBody")}
              </p>
            </div>
            <div className="border-t border-white/10 pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
              <p className="text-base leading-8 text-white/72">
                {t("service.audit.finalSubtitle")}
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href={`mailto:${CONTACT_EMAIL}`}
                  className="inline-flex items-center gap-2 rounded-full bg-[#f7ecde] px-7 py-4 text-sm font-semibold text-[#082032] transition-colors hover:bg-white"
                >
                  <Mail size={16} />
                  {t("service.audit.heroCta")}
                </a>
                <Link
                  to="/console"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-7 py-4 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
                >
                  {t("service.audit.workspaceCta")}
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
