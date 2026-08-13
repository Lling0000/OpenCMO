import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, KeyRound, Sparkles } from "lucide-react";
import { useI18n } from "../../i18n";
import { ScheduleSelector } from "./ScheduleSelector";
import { getEffectiveKeyStatus } from "../../api/userKeys";
import { useSettings } from "../../hooks/useSettings";
import { SettingsDialog } from "../settings/SettingsDialog";
import { ApiError } from "../../api/client";
import { normalizeWebsiteUrl } from "../../utils/url";

export function MonitorForm({
  onSubmit,
  isLoading,
  initialUrl = "",
}: {
  onSubmit: (data: { url: string; cron_expr: string }) => Promise<void>;
  isLoading: boolean;
  initialUrl?: string;
}) {
  const { t } = useI18n();
  const [url, setUrl] = useState(initialUrl);
  const [cronExpr, setCronExpr] = useState("0 9 * * *");
  const [showSettings, setShowSettings] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const settingsQuery = useSettings();
  const keyStatus = getEffectiveKeyStatus(settingsQuery.data);
  const keysReady = keyStatus.effective.llm;

  useEffect(() => {
    if (!url && initialUrl) setUrl(initialUrl);
  }, [initialUrl, url]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setSubmitError("");
    try {
      await onSubmit({ url: normalizeWebsiteUrl(url), cron_expr: cronExpr });
      setUrl(initialUrl);
    } catch (error) {
      setSubmitError(error instanceof ApiError && error.errorCode === "invalid_url" ? t("monitorForm.invalidUrl") : t("monitorForm.createError"));
    }
  };

  return (
    <>
      <div className="rounded-3xl border border-slate-200/80 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.08),_transparent_42%),linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-6 shadow-sm">
        <div className="mb-5 flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white">
            <Sparkles size={18} />
          </div>
          <div className="max-w-3xl">
            <p className="text-sm text-slate-600">{t("monitorForm.subtitle")}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              type="text"
              inputMode="url"
              required
              placeholder={t("monitorForm.urlPlaceholder")}
              className="flex-1 rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm shadow-sm transition-shadow placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-slate-800 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                t("monitorForm.creatingWorkspace")
              ) : (
                <>
                  {t("monitorForm.analyzeMySite")}
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
          {submitError ? <p className="text-sm font-medium text-rose-600">{submitError}</p> : null}

          <div
            className={`rounded-2xl border px-4 py-3 text-sm ${
              keysReady ? "border-emerald-200 bg-emerald-50/70" : "border-amber-200 bg-amber-50/70"
            }`}
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-start gap-3">
                {keysReady ? (
                  <CheckCircle2 size={18} className="mt-0.5 text-emerald-600" />
                ) : (
                  <KeyRound size={18} className="mt-0.5 text-amber-600" />
                )}
                <div>
                  <p className={`text-sm font-semibold ${keysReady ? "text-emerald-900" : "text-amber-900"}`}>
                    {t(keysReady ? "onboarding.keyReadyTitle" : "onboarding.keyNeededTitle")}
                  </p>
                  <p className={`mt-1 text-sm leading-6 ${keysReady ? "text-emerald-800/80" : "text-amber-800/80"}`}>
                    {t(keysReady ? "onboarding.keyReadyDesc" : "onboarding.keyNeededDesc")}
                  </p>
                  <p className={`mt-2 text-xs ${keysReady ? "text-emerald-800/70" : "text-amber-800/70"}`}>
                    {t("onboarding.privacyHint")}
                  </p>
                </div>
              </div>

              {!keysReady ? (
                <button
                  type="button"
                  onClick={() => setShowSettings(true)}
                  className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-900 transition-colors hover:border-amber-400 hover:bg-amber-100"
                >
                  <KeyRound size={14} />
                  {t("onboarding.configureKeys")}
                </button>
              ) : null}
            </div>
          </div>

          <ScheduleSelector value={cronExpr} onChange={setCronExpr} />
        </form>
      </div>

      {showSettings ? <SettingsDialog onClose={() => setShowSettings(false)} /> : null}
    </>
  );
}
