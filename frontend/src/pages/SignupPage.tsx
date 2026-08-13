import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { ArrowRight, Github, Lock, Mail, UserRound } from "lucide-react";
import { useAuth } from "../components/auth/useAuth";
import { useI18n } from "../i18n";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function SignupPage() {
  const { t, locale } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const url = params.get("url") || "";
  const next = params.get("next") || (url ? `/console?url=${encodeURIComponent(url)}` : "/console");

  const signupErrorMessage = (code?: string) => {
    switch (code) {
      case "invalid_email":
        return t("trial.errorInvalidEmail");
      case "password_too_short":
        return t("trial.errorPasswordTooShort");
      case "email_exists":
        return t("trial.errorEmailExists");
      case "rate_limited":
        return t("trial.errorRateLimited");
      case "signup_closed":
      case "invite_required":
        return t("trial.errorSignupClosed");
      default:
        return t("trial.authError");
    }
  };

  if (!auth.isLoading && auth.isAuthenticated) {
    return <Navigate to={next} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    const normalizedEmail = email.trim().toLowerCase();
    const trimmedName = name.trim();
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError(t("trial.errorInvalidEmail"));
      return;
    }
    if (password.length < 8) {
      setError(t("trial.errorPasswordTooShort"));
      return;
    }
    setLoading(true);
    const result = await auth.signup(normalizedEmail, password, trimmedName, locale);
    setLoading(false);
    if (!result.ok) {
      setError(signupErrorMessage(result.error));
      return;
    }
    if (result.needsVerification) {
      const verifyParams = new URLSearchParams({
        user_id: String(result.userId),
        email: result.email,
      });
      if (next && next !== "/console") verifyParams.set("next", next);
      navigate(`/verify-email?${verifyParams.toString()}`, { replace: true });
      return;
    }
    navigate(next, { replace: true });
  };

  return (
    <main className="min-h-screen bg-[#f6f7f9] px-4 py-10 text-slate-950">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1fr)_440px]">
        <section className="max-w-2xl">
          <Link to="/" className="text-sm font-semibold text-slate-500">
            OpenCMO
          </Link>
          <h1 className="mt-8 text-4xl font-semibold tracking-tight sm:text-5xl">
            {t("trial.signupTitle")}
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-600">
            {t("trial.signupSubtitle")}
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              ["trial.limitDays", "14"],
              ["trial.limitProjects", "3"],
              ["trial.limitScans", "3"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-2xl font-semibold">{value}</p>
                <p className="mt-1 text-sm text-slate-500">{t(label as never)}</p>
              </div>
            ))}
          </div>
          <a
            href="https://github.com/study8677/OpenCMO"
            target="_blank"
            rel="noreferrer"
            className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-slate-700"
          >
            <Github size={16} />
            {t("trial.githubLink")}
          </a>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">{t("trial.createAccount")}</h2>
          <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-4">
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
              <span className="mt-1 block text-xs text-slate-500">{t("trial.emailHint")}</span>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">{t("trial.password")}</span>
              <span className="mt-1 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5">
                <Lock size={16} className="text-slate-400" />
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  className="min-w-0 flex-1 outline-none"
                />
              </span>
              <span className="mt-1 block text-xs text-slate-500">{t("trial.passwordHint")}</span>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">{t("trial.displayName")}</span>
              <span className="mt-1 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5">
                <UserRound size={16} className="text-slate-400" />
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  autoComplete="name"
                  className="min-w-0 flex-1 outline-none"
                />
              </span>
              <span className="mt-1 block text-xs text-slate-500">{t("trial.displayNameHint")}</span>
            </label>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <p className="text-xs leading-5 text-slate-500">{t("trial.instantAccessHint")}</p>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? t("trial.submitting") : t("trial.startTrial")}
              <ArrowRight size={16} />
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-slate-500">
            {t("trial.haveAccount")}{" "}
            <Link to={url ? `/login?url=${encodeURIComponent(url)}` : "/login"} className="font-semibold text-slate-950">
              {t("trial.signIn")}
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
