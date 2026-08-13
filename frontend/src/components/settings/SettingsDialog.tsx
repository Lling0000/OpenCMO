import { useState, useEffect } from "react";
import { X, Key, Check, ChevronDown, ChevronRight } from "lucide-react";
import { getSettings, saveSettings, type SettingsSavePayload } from "../../api/settings";
import { getEffectiveKeyStatus, getUserKeys, setUserKeys, type UserKeys } from "../../api/userKeys";
import { useI18n } from "../../i18n";
import type { AISettings } from "../../types";

function StatusBadge({ ok, okText, noText }: { ok: boolean; okText: string; noText: string }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium ${
        ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
      }`}
    >
      <Key size={14} />
      {ok ? okText : noText}
    </div>
  );
}

function Section({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-slate-100 pt-4">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="mb-3 flex w-full items-center gap-1.5 text-sm font-semibold text-slate-800"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {title}
      </button>
      {open && <div className="space-y-3">{children}</div>}
    </div>
  );
}

function Field({
  label,
  hint,
  type = "text",
  placeholder,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  type?: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const inputClass =
    "w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm shadow-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputClass}
      />
      {hint && <p className="mt-1 text-[10px] text-slate-400">{hint}</p>}
    </div>
  );
}

function Toggle({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5">
      <div>
        <p className="text-xs font-medium text-slate-700">{label}</p>
        {hint && <p className="text-[10px] text-slate-400">{hint}</p>}
      </div>
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
          value ? "bg-indigo-600" : "bg-slate-300"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            value ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

export function SettingsDialog({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [status, setStatus] = useState<AISettings | null>(null);

  // ── User-local keys (stored in browser localStorage) ──
  const [tavilyKey, setTavilyKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [googleAiKey, setGoogleAiKey] = useState("");
  const [pagespeedKey, setPagespeedKey] = useState("");
  const [gscCredentials, setGscCredentials] = useState("");
  const [gscSiteUrl, setGscSiteUrl] = useState("");
  const [moonshotKey, setMoonshotKey] = useState("");
  const [dashscopeKey, setDashscopeKey] = useState("");
  const [deepseekKey, setDeepseekKey] = useState("");
  const [zhipuKey, setZhipuKey] = useState("");
  const [doubaoKey, setDoubaoKey] = useState("");

  // ── Server-side settings ──
  const [redditClientId, setRedditClientId] = useState("");
  const [redditClientSecret, setRedditClientSecret] = useState("");
  const [redditUsername, setRedditUsername] = useState("");
  const [redditPassword, setRedditPassword] = useState("");
  const [autoPublish, setAutoPublish] = useState(false);
  const [twitterApiKey, setTwitterApiKey] = useState("");
  const [twitterApiSecret, setTwitterApiSecret] = useState("");
  const [twitterAccessToken, setTwitterAccessToken] = useState("");
  const [twitterAccessSecret, setTwitterAccessSecret] = useState("");
  const [geoChatgpt, setGeoChatgpt] = useState(false);
  const [dataforseoLogin, setDataforseoLogin] = useState("");
  const [dataforseoPassword, setDataforseoPassword] = useState("");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [reportEmail, setReportEmail] = useState("");
  const keyStatus = getEffectiveKeyStatus(status);

  useEffect(() => {
    // Load user-local keys
    const uk = getUserKeys();
    if (uk.TAVILY_API_KEY) setTavilyKey(uk.TAVILY_API_KEY);
    if (uk.ANTHROPIC_API_KEY) setAnthropicKey(uk.ANTHROPIC_API_KEY);
    if (uk.GOOGLE_AI_API_KEY) setGoogleAiKey(uk.GOOGLE_AI_API_KEY);
    if (uk.PAGESPEED_API_KEY) setPagespeedKey(uk.PAGESPEED_API_KEY);
    if (uk.GOOGLE_GSC_CREDENTIALS) setGscCredentials(uk.GOOGLE_GSC_CREDENTIALS);
    if (uk.GOOGLE_GSC_SITE_URL) setGscSiteUrl(uk.GOOGLE_GSC_SITE_URL);
    if (uk.MOONSHOT_API_KEY) setMoonshotKey(uk.MOONSHOT_API_KEY);
    if (uk.DASHSCOPE_API_KEY) setDashscopeKey(uk.DASHSCOPE_API_KEY);
    if (uk.DEEPSEEK_API_KEY) setDeepseekKey(uk.DEEPSEEK_API_KEY);
    if (uk.ZHIPU_API_KEY) setZhipuKey(uk.ZHIPU_API_KEY);
    if (uk.DOUBAO_API_KEY) setDoubaoKey(uk.DOUBAO_API_KEY);

    // Load server-side status
    getSettings().then((s) => {
      setStatus(s);
      if (!uk.GOOGLE_GSC_SITE_URL && s.gsc_site_url) setGscSiteUrl(s.gsc_site_url);
      setAutoPublish(s.auto_publish);
      setGeoChatgpt(s.geo_chatgpt_enabled);
      setSmtpHost(s.smtp_host);
      setSmtpPort(s.smtp_port);
      setSmtpUser(s.smtp_user);
      setReportEmail(s.report_email);
    });
  }, []);

  const handleSave = async () => {
    setLoading(true);
    setSaved(false);
    try {
      // 1. Save user-local keys to localStorage
      const newKeys: UserKeys = {};
      if (tavilyKey) newKeys.TAVILY_API_KEY = tavilyKey;
      if (anthropicKey) newKeys.ANTHROPIC_API_KEY = anthropicKey;
      if (googleAiKey) newKeys.GOOGLE_AI_API_KEY = googleAiKey;
      if (pagespeedKey) newKeys.PAGESPEED_API_KEY = pagespeedKey;
      if (gscCredentials) newKeys.GOOGLE_GSC_CREDENTIALS = gscCredentials;
      if (gscSiteUrl) newKeys.GOOGLE_GSC_SITE_URL = gscSiteUrl;
      if (moonshotKey) newKeys.MOONSHOT_API_KEY = moonshotKey;
      if (dashscopeKey) newKeys.DASHSCOPE_API_KEY = dashscopeKey;
      if (deepseekKey) newKeys.DEEPSEEK_API_KEY = deepseekKey;
      if (zhipuKey) newKeys.ZHIPU_API_KEY = zhipuKey;
      if (doubaoKey) newKeys.DOUBAO_API_KEY = doubaoKey;
      setUserKeys(newKeys);

      // 2. Save server-side settings only when an operator changed them.
      const serverSettings: SettingsSavePayload = {};
      if (redditClientId) serverSettings.REDDIT_CLIENT_ID = redditClientId;
      if (redditClientSecret) serverSettings.REDDIT_CLIENT_SECRET = redditClientSecret;
      if (redditUsername) serverSettings.REDDIT_USERNAME = redditUsername;
      if (redditPassword) serverSettings.REDDIT_PASSWORD = redditPassword;
      if (status && autoPublish !== status.auto_publish) {
        serverSettings.OPENCMO_AUTO_PUBLISH = autoPublish ? "1" : "0";
      }
      if (twitterApiKey) serverSettings.TWITTER_API_KEY = twitterApiKey;
      if (twitterApiSecret) serverSettings.TWITTER_API_SECRET = twitterApiSecret;
      if (twitterAccessToken) serverSettings.TWITTER_ACCESS_TOKEN = twitterAccessToken;
      if (twitterAccessSecret) serverSettings.TWITTER_ACCESS_SECRET = twitterAccessSecret;
      if (status && geoChatgpt !== status.geo_chatgpt_enabled) {
        serverSettings.OPENCMO_GEO_CHATGPT = geoChatgpt ? "1" : "0";
      }
      if (dataforseoLogin) serverSettings.DATAFORSEO_LOGIN = dataforseoLogin;
      if (dataforseoPassword) serverSettings.DATAFORSEO_PASSWORD = dataforseoPassword;
      if (status && smtpHost !== status.smtp_host) serverSettings.OPENCMO_SMTP_HOST = smtpHost;
      if (status && smtpPort !== status.smtp_port) serverSettings.OPENCMO_SMTP_PORT = smtpPort;
      if (status && smtpUser !== status.smtp_user) serverSettings.OPENCMO_SMTP_USER = smtpUser;
      if (smtpPass) serverSettings.OPENCMO_SMTP_PASS = smtpPass;
      if (status && reportEmail !== status.report_email) serverSettings.OPENCMO_REPORT_EMAIL = reportEmail;

      if (Object.keys(serverSettings).length > 0) {
        await saveSettings(serverSettings);
        // Clear sensitive fields after a confirmed save so they aren't
        // re-submitted accidentally on the next save.
        setRedditClientId("");
        setRedditClientSecret("");
        setRedditUsername("");
        setRedditPassword("");
        setTwitterApiKey("");
        setTwitterApiSecret("");
        setTwitterAccessToken("");
        setTwitterAccessSecret("");
        setDataforseoLogin("");
        setDataforseoPassword("");
        setSmtpPass("");
      }
      setSaved(true);
      // Refresh server status
      const s = await getSettings();
      setStatus(s);
      window.dispatchEvent(new CustomEvent("opencmo:settings-changed"));
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
      <div className="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{t("settings.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>

        <p className="mb-4 rounded-xl bg-indigo-50 px-3 py-2 text-[11px] font-medium text-indigo-700">
          {t("settings.accountScopedHint")}
        </p>

        <div className="space-y-4">
          {/* ── Reddit ── */}
          <Section title={t("settings.redditSection")} defaultOpen={false}>
            {status && (
              <StatusBadge
                ok={status.reddit_configured}
                okText={`${t("settings.redditConfigured")} (u/${status.reddit_username})`}
                noText={t("settings.redditNotConfigured")}
              />
            )}
            <Field label={t("settings.redditClientId")} placeholder={t("settings.redditClientIdPlaceholder")} value={redditClientId} onChange={setRedditClientId} />
            <Field label={t("settings.redditClientSecret")} type="password" placeholder={t("settings.redditClientSecretPlaceholder")} value={redditClientSecret} onChange={setRedditClientSecret} />
            <Field label={t("settings.redditUsername")} placeholder={t("settings.redditUsernamePlaceholder")} value={redditUsername} onChange={setRedditUsername} />
            <Field label={t("settings.redditPassword")} type="password" placeholder={t("settings.redditPasswordPlaceholder")} value={redditPassword} onChange={setRedditPassword} />
            <p className="text-[10px] text-slate-400">{t("settings.redditHint")}</p>
            <Toggle label={t("settings.autoPublish")} hint={t("settings.autoPublishHint")} value={autoPublish} onChange={setAutoPublish} />
          </Section>

          {/* ── Twitter ── */}
          <Section title={t("settings.twitterSection")}>
            {status && (
              <StatusBadge
                ok={status.twitter_configured}
                okText={`${t("settings.twitterConfigured")} (${status.twitter_api_key_masked})`}
                noText={t("settings.twitterNotConfigured")}
              />
            )}
            <Field label={t("settings.twitterApiKey")} type="password" placeholder="API Key" value={twitterApiKey} onChange={setTwitterApiKey} />
            <Field label={t("settings.twitterApiSecret")} type="password" placeholder="API Secret" value={twitterApiSecret} onChange={setTwitterApiSecret} />
            <Field label={t("settings.twitterAccessToken")} type="password" placeholder="Access Token" value={twitterAccessToken} onChange={setTwitterAccessToken} />
            <Field label={t("settings.twitterAccessSecret")} type="password" placeholder="Access Token Secret" value={twitterAccessSecret} onChange={setTwitterAccessSecret} />
            <p className="text-[10px] text-slate-400">{t("settings.twitterHint")}</p>
          </Section>

          {/* ── GEO Detection ── */}
          <Section title={t("settings.geoSection")}>
            {status && (
              <>
                <StatusBadge
                  ok={status.anthropic_key_set}
                  okText={`Claude ${t("settings.configured")} (${status.anthropic_key_masked})`}
                  noText={`Claude ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.google_ai_key_set}
                  okText={`Gemini ${t("settings.configured")} (${status.google_ai_key_masked})`}
                  noText={`Gemini ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.moonshot_key_set}
                  okText={`Kimi ${t("settings.configured")} (${status.moonshot_key_masked})`}
                  noText={`Kimi ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.dashscope_key_set}
                  okText={`Qwen ${t("settings.configured")} (${status.dashscope_key_masked})`}
                  noText={`Qwen ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.deepseek_key_set}
                  okText={`DeepSeek ${t("settings.configured")} (${status.deepseek_key_masked})`}
                  noText={`DeepSeek ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.zhipu_key_set}
                  okText={`Zhipu ${t("settings.configured")} (${status.zhipu_key_masked})`}
                  noText={`Zhipu ${t("settings.notConfigured")}`}
                />
                <StatusBadge
                  ok={status.doubao_key_set}
                  okText={`Doubao ${t("settings.configured")} (${status.doubao_key_masked})`}
                  noText={`Doubao ${t("settings.notConfigured")}`}
                />
              </>
            )}
            <Field label={t("settings.anthropicKey")} type="password" placeholder="sk-ant-..." value={anthropicKey} onChange={setAnthropicKey} />
            <Field label={t("settings.googleAiKey")} type="password" placeholder="AIza..." value={googleAiKey} onChange={setGoogleAiKey} />
            <Field label={t("settings.moonshotKey")} type="password" placeholder="sk-..." value={moonshotKey} onChange={setMoonshotKey} />
            <Field label={t("settings.dashscopeKey")} type="password" placeholder="sk-..." value={dashscopeKey} onChange={setDashscopeKey} />
            <Field label={t("settings.deepseekKey")} type="password" placeholder="sk-..." value={deepseekKey} onChange={setDeepseekKey} />
            <Field label={t("settings.zhipuKey")} type="password" placeholder="..." value={zhipuKey} onChange={setZhipuKey} />
            <Field label={t("settings.doubaoKey")} type="password" placeholder="..." value={doubaoKey} onChange={setDoubaoKey} />
            <Toggle label={t("settings.geoChatgpt")} hint={t("settings.geoChatgptHint")} value={geoChatgpt} onChange={setGeoChatgpt} />
            <p className="text-[10px] text-slate-400">{t("settings.geoHint")}</p>
          </Section>

          {/* ── SEO ── */}
          <Section title={t("settings.seoSection")}>
            {status && (
              <StatusBadge
                ok={status.pagespeed_key_set}
                okText={`PageSpeed ${t("settings.configured")} (${status.pagespeed_key_masked})`}
                noText={t("settings.pagespeedNotConfigured")}
              />
            )}
            <Field label={t("settings.pagespeedKey")} type="password" placeholder="AIza..." hint={t("settings.pagespeedHint")} value={pagespeedKey} onChange={setPagespeedKey} />
            {status && (
              <StatusBadge
                ok={status.gsc_credentials_set}
                okText={`GSC ${t("settings.configured")}`}
                noText={t("settings.gscNotConfigured")}
              />
            )}
            <Field label={t("settings.gscCredentials")} type="password" placeholder='{"token":"..."}' hint={t("settings.gscCredentialsHint")} value={gscCredentials} onChange={setGscCredentials} />
            <Field label={t("settings.gscSiteUrl")} placeholder="sc-domain:example.com" hint={t("settings.gscSiteUrlHint")} value={gscSiteUrl} onChange={setGscSiteUrl} />
          </Section>

          {/* ── Search (Tavily) ── */}
          <Section title={t("settings.tavilySection")}>
            {status && (
              <StatusBadge
                ok={keyStatus.effective.tavily}
                okText={
                  keyStatus.browserOverride.tavily
                    ? `Tavily ${t("settings.browserOverrideActive")}`
                    : `Tavily ${t("settings.serverDefaultActive")}`
                }
                noText={t("settings.tavilyOptional")}
              />
            )}
            <Field
              label={t("settings.tavilyKey")}
              type="password"
              placeholder="tvly-..."
              hint={t("settings.tavilyHint")}
              value={tavilyKey}
              onChange={setTavilyKey}
            />
          </Section>

          {/* ── SERP ── */}
          <Section title={t("settings.serpSection")}>
            {status && (
              <StatusBadge
                ok={status.dataforseo_configured}
                okText={`DataForSEO ${t("settings.configured")} (${status.dataforseo_login})`}
                noText={t("settings.dataforseoNotConfigured")}
              />
            )}
            <Field label={t("settings.dataforseoLogin")} placeholder="login@example.com" value={dataforseoLogin} onChange={setDataforseoLogin} />
            <Field label={t("settings.dataforseoPassword")} type="password" placeholder="Password" value={dataforseoPassword} onChange={setDataforseoPassword} />
            <p className="text-[10px] text-slate-400">{t("settings.dataforseoHint")}</p>
          </Section>

          {/* ── Email Reports ── */}
          <Section title={t("settings.emailSection")}>
            {status && (
              <StatusBadge
                ok={status.email_configured}
                okText={`${t("settings.emailConfigured")} (${status.smtp_user})`}
                noText={t("settings.emailNotConfigured")}
              />
            )}
            {status && !status.email_configured && status.system_smtp_active && (
              <p className="rounded-xl bg-slate-50 px-3 py-2 text-[11px] font-medium text-slate-600">
                {t("settings.systemSmtpActive")}
              </p>
            )}
            <Field label={t("settings.smtpHost")} placeholder="smtp.gmail.com" value={smtpHost} onChange={setSmtpHost} />
            <Field label={t("settings.smtpPort")} placeholder="587" value={smtpPort} onChange={setSmtpPort} />
            <Field label={t("settings.smtpUser")} placeholder="user@example.com" value={smtpUser} onChange={setSmtpUser} />
            <Field label={t("settings.smtpPass")} type="password" placeholder="App password" value={smtpPass} onChange={setSmtpPass} />
            <Field label={t("settings.reportEmail")} placeholder="report@example.com" hint={t("settings.reportEmailHint")} value={reportEmail} onChange={setReportEmail} />
          </Section>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saved ? (
              <>
                <Check size={14} />
                {t("settings.saved")}
              </>
            ) : (
              t("settings.save")
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
