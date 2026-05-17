import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { ArrowRight, Lock, Mail } from "lucide-react";
import { useAuth } from "../components/auth/useAuth";
import { useI18n } from "../i18n";
import { resendVerificationCode } from "../api/auth";

export function LoginPage() {
  const { t, locale } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const url = params.get("url") || "";
  const next = params.get("next") || (url ? `/console?url=${encodeURIComponent(url)}` : "/console");

  if (!auth.isLoading && auth.isAuthenticated) {
    return <Navigate to={next} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    const result = await auth.login(email, password);
    setLoading(false);
    if (result.ok) {
      navigate(next, { replace: true });
      return;
    }
    if (result.error === "email_not_verified" && result.userId) {
      const verifyParams = new URLSearchParams({
        user_id: String(result.userId),
        email: result.email ?? email,
      });
      if (next && next !== "/console") verifyParams.set("next", next);
      // Trigger a fresh code so the user does not have to hunt for the old one.
      void resendVerificationCode({ user_id: result.userId, locale }).catch(() => undefined);
      navigate(`/verify-email?${verifyParams.toString()}`, { replace: true });
      return;
    }
    setError(t("trial.authError"));
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f7f9] px-4 py-10 text-slate-950">
      <section className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link to="/" className="text-sm font-semibold text-slate-500">
          OpenCMO
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight">{t("trial.loginTitle")}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">{t("trial.loginSubtitle")}</p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">{t("trial.email")}</span>
            <span className="mt-1 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5">
              <Mail size={16} className="text-slate-400" />
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                autoComplete="email"
                required
                className="min-w-0 flex-1 outline-none"
              />
            </span>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">{t("trial.password")}</span>
            <span className="mt-1 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5">
              <Lock size={16} className="text-slate-400" />
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
                required
                className="min-w-0 flex-1 outline-none"
              />
            </span>
          </label>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {loading ? t("trial.submitting") : t("trial.signIn")}
            <ArrowRight size={16} />
          </button>
        </form>
        <p className="mt-5 text-center text-sm text-slate-500">
          {t("trial.needAccount")}{" "}
          <Link to={url ? `/signup?url=${encodeURIComponent(url)}` : "/signup"} className="font-semibold text-slate-950">
            {t("trial.startTrial")}
          </Link>
        </p>
      </section>
    </main>
  );
}
