import { useState } from "react";
import { useAuth } from "./useAuth";
import { useI18n } from "../../i18n";
import { LogIn } from "lucide-react";

export function TokenPrompt() {
  const { login } = useAuth();
  const { t } = useI18n();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const ok = await login(token, token);
    setLoading(false);
    if (!ok) setError(t("auth.invalidToken"));
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900">
      <div className="w-full max-w-sm rounded-2xl bg-white/95 p-8 shadow-2xl backdrop-blur-sm">
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900">OpenCMO</h2>
          <p className="mt-1 text-sm text-slate-500">
            {t("auth.enterToken")}
          </p>
        </div>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={t("auth.tokenPlaceholder")}
            className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm shadow-sm transition-shadow placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-indigo-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogIn size={16} />
            {loading ? t("auth.loggingIn") : t("auth.login")}
          </button>
          {error && (
            <p className="mt-3 text-center text-sm text-rose-600">{error}</p>
          )}
        </form>
      </div>
    </div>
  );
}
