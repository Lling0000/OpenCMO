import { ExternalLink, GitFork, Github, Star, Users } from "lucide-react";
import { useI18n } from "../../i18n";
import { useGitHubStats } from "../../hooks/useGitHubStats";
import { utcDate } from "../../utils/time";

const GITHUB_REPO = "https://github.com/Lling0000/OpenCMO";

function relativeTimeFrom(iso: string, locale: string): string {
  try {
    const then = utcDate(iso).getTime();
    const now = Date.now();
    const diffSec = Math.round((now - then) / 1000);

    const rtf = new Intl.RelativeTimeFormat(locale === "zh" ? "zh-CN" : locale, {
      numeric: "auto",
    });

    const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
      ["year", 365 * 24 * 3600],
      ["month", 30 * 24 * 3600],
      ["week", 7 * 24 * 3600],
      ["day", 24 * 3600],
      ["hour", 3600],
      ["minute", 60],
    ];
    for (const [unit, secs] of ranges) {
      if (Math.abs(diffSec) >= secs) {
        return rtf.format(-Math.round(diffSec / secs), unit);
      }
    }
    return rtf.format(0, "second");
  } catch {
    return iso;
  }
}

function FallbackBlock() {
  const { t } = useI18n();
  return (
    <a
      href={GITHUB_REPO}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-5 py-3 text-sm font-semibold text-white/90 transition-colors hover:border-white/25 hover:text-white"
    >
      <Github size={16} />
      {t("landing.builtInOpen.fallbackStat")}
      <ExternalLink size={14} />
    </a>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: string;
  label?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5">
      <div className="flex items-center gap-3 text-white/80">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/8 text-white">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="font-display text-2xl font-semibold tracking-tight text-white">{value}</p>
          {label ? <p className="text-xs text-white/60">{label}</p> : null}
        </div>
      </div>
    </div>
  );
}

export function BuiltInOpen() {
  const { t, locale } = useI18n();
  const { data, isLoading, isError } = useGitHubStats();

  // Per Codex review fix: any null = full fallback (matches §1.3 spec
  // "前端检测到 null → 整个 stat card 区域不渲染").
  const anyNull =
    !data
    || data.stars === null
    || data.contributors === null
    || data.last_commit_iso === null;

  const showFallback = isError || anyNull;

  return (
    <section className="border-y border-white/8 bg-[#06121d]">
      <div className="mx-auto max-w-7xl px-4 py-20 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            {t("landing.builtInOpen.title")}
          </h2>
          <p className="mt-4 text-base text-white/70">
            {t("landing.builtInOpen.subtitle")}
          </p>
        </div>

        {isLoading ? (
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-24 animate-pulse rounded-2xl border border-white/10 bg-white/5"
              />
            ))}
          </div>
        ) : showFallback ? (
          <div className="mt-10">
            <FallbackBlock />
          </div>
        ) : (
          <>
            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <StatCard
                icon={<Star size={18} />}
                value={t("landing.builtInOpen.statStars").replace(
                  "{count}",
                  String(data!.stars),
                )}
              />
              <StatCard
                icon={<GitFork size={18} />}
                value={t("landing.builtInOpen.statLastCommit").replace(
                  "{time}",
                  relativeTimeFrom(data!.last_commit_iso!, locale),
                )}
              />
              <StatCard
                icon={<Users size={18} />}
                value={t("landing.builtInOpen.statContributors").replace(
                  "{count}",
                  String(data!.contributors),
                )}
              />
            </div>
            <div className="mt-8">
              <a
                href={GITHUB_REPO}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm font-semibold text-white/80 transition-colors hover:text-white"
              >
                {t("landing.builtInOpen.cta")}
              </a>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
