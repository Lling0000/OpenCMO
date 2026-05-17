import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { ArrowRight, Mail } from "lucide-react";
import { useAuth } from "../components/auth/useAuth";
import { useI18n } from "../i18n";
import { ApiError } from "../api/client";
import { resendVerificationCode, verifyEmail } from "../api/auth";

const CODE_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 60;

function digitsFromString(value: string): string[] {
  const digits = value.replace(/\D/g, "").slice(0, CODE_LENGTH).split("");
  while (digits.length < CODE_LENGTH) digits.push("");
  return digits;
}

export function VerifyEmailPage() {
  const { t, locale } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const userIdRaw = params.get("user_id") ?? "";
  const email = params.get("email") ?? "";
  const next = params.get("next") || "/console";
  const userId = Number.parseInt(userIdRaw, 10);

  const [digits, setDigits] = useState<string[]>(() => Array(CODE_LENGTH).fill(""));
  const [error, setError] = useState<string>("");
  const [info, setInfo] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState<number>(RESEND_COOLDOWN_SECONDS);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);

  const code = useMemo(() => digits.join(""), [digits]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setInterval(() => setCooldown((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(id);
  }, [cooldown]);

  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const submitCode = useCallback(
    async (currentCode: string) => {
      if (!Number.isFinite(userId) || userId <= 0) {
        setError(t("verify.missingUser"));
        return;
      }
      if (currentCode.length !== CODE_LENGTH) {
        setError(t("verify.errorInvalid"));
        return;
      }
      setError("");
      setInfo("");
      setSubmitting(true);
      try {
        const payload = await verifyEmail({ user_id: userId, code: currentCode });
        await auth.applyAuthPayload(payload);
        navigate(next, { replace: true });
      } catch (err) {
        const apiErr = err as ApiError & {
          payload?: { error?: string; remaining_attempts?: number };
        };
        const code = apiErr?.errorCode ?? apiErr?.payload?.error ?? "code_invalid";
        const remaining = apiErr?.payload?.remaining_attempts ?? 0;
        switch (code) {
          case "code_expired":
            setError(t("verify.errorExpired"));
            break;
          case "code_locked":
            setError(t("verify.errorLocked"));
            break;
          case "no_pending_code":
            setError(t("verify.errorNoPending"));
            break;
          case "code_invalid":
            setError(
              remaining > 0
                ? t("verify.errorInvalidRemaining", { remaining })
                : t("verify.errorInvalid"),
            );
            // Reset for next attempt
            setDigits(Array(CODE_LENGTH).fill(""));
            inputsRef.current[0]?.focus();
            break;
          default:
            setError(t("verify.errorGeneric"));
        }
      } finally {
        setSubmitting(false);
      }
    },
    [auth, navigate, next, t, userId],
  );

  const handleDigitChange = useCallback(
    (index: number, raw: string) => {
      const filtered = raw.replace(/\D/g, "");
      if (!filtered) {
        setDigits((prev) => {
          const copy = prev.slice();
          copy[index] = "";
          return copy;
        });
        return;
      }
      setDigits((prev) => {
        const copy = prev.slice();
        // If multiple digits were inserted (paste-like), spread them.
        for (let i = 0; i < filtered.length && index + i < CODE_LENGTH; i += 1) {
          copy[index + i] = filtered[i] ?? "";
        }
        return copy;
      });
      const nextIndex = Math.min(CODE_LENGTH - 1, index + filtered.length);
      inputsRef.current[nextIndex]?.focus();
    },
    [],
  );

  const handleKeyDown = useCallback(
    (index: number, event: KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Backspace") {
        if (digits[index]) {
          setDigits((prev) => {
            const copy = prev.slice();
            copy[index] = "";
            return copy;
          });
          return;
        }
        if (index > 0) {
          inputsRef.current[index - 1]?.focus();
        }
      } else if (event.key === "ArrowLeft" && index > 0) {
        inputsRef.current[index - 1]?.focus();
      } else if (event.key === "ArrowRight" && index < CODE_LENGTH - 1) {
        inputsRef.current[index + 1]?.focus();
      }
    },
    [digits],
  );

  const handlePaste = useCallback((event: ClipboardEvent<HTMLInputElement>) => {
    const text = event.clipboardData.getData("text");
    if (!text) return;
    event.preventDefault();
    const pasted = digitsFromString(text);
    setDigits(pasted);
    const focusIndex = Math.min(CODE_LENGTH - 1, pasted.findIndex((d) => !d));
    inputsRef.current[focusIndex < 0 ? CODE_LENGTH - 1 : focusIndex]?.focus();
    if (pasted.every((d) => d)) {
      void submitCode(pasted.join(""));
    }
  }, [submitCode]);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void submitCode(code);
    },
    [code, submitCode],
  );

  const handleResend = useCallback(async () => {
    if (cooldown > 0 || resending) return;
    if (!Number.isFinite(userId) || userId <= 0) return;
    setResending(true);
    setError("");
    setInfo("");
    try {
      const result = await resendVerificationCode({ user_id: userId, locale });
      if (result.ok) {
        setInfo(t("verify.resentInfo"));
        setCooldown(RESEND_COOLDOWN_SECONDS);
      } else if (result.retry_after_seconds) {
        setCooldown(result.retry_after_seconds);
        setError(t("verify.errorRateLimited"));
      } else {
        setError(t("verify.errorGeneric"));
      }
    } catch (err) {
      const apiErr = err as ApiError & { payload?: { retry_after_seconds?: number; error?: string } };
      const retry = apiErr?.payload?.retry_after_seconds;
      if (retry) {
        setCooldown(retry);
        setError(t("verify.errorRateLimited"));
      } else {
        setError(t("verify.errorGeneric"));
      }
    } finally {
      setResending(false);
    }
  }, [cooldown, locale, resending, t, userId]);

  if (!auth.isLoading && auth.isAuthenticated) {
    return <Navigate to={next} replace />;
  }

  if (!Number.isFinite(userId) || userId <= 0) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f6f7f9] px-4 py-10 text-slate-950">
        <section className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-semibold">{t("verify.missingUser")}</h1>
          <p className="mt-3 text-sm text-slate-600">{t("verify.missingUserBody")}</p>
          <Link
            to="/signup"
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white"
          >
            {t("trial.startTrial")}
          </Link>
        </section>
      </main>
    );
  }

  const canResend = cooldown <= 0 && !resending;
  const ctaLabel = submitting ? t("trial.submitting") : t("verify.submit");
  const resendLabel = canResend
    ? t("verify.resend")
    : t("verify.resendCountdown", { seconds: cooldown });

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f7f9] px-4 py-10 text-slate-950">
      <section className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link to="/" className="text-sm font-semibold text-slate-500">
          OpenCMO
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight">{t("verify.title")}</h1>
        <p className="mt-2 flex items-center gap-2 text-sm leading-6 text-slate-500">
          <Mail size={14} className="text-slate-400" />
          <span>
            {t("verify.subtitle")} <span className="font-semibold text-slate-700">{email}</span>
          </span>
        </p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="grid grid-cols-6 gap-2" role="group" aria-label={t("verify.codeLabel")}>
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputsRef.current[index] = el;
                }}
                value={digit}
                onChange={(event) => handleDigitChange(index, event.target.value)}
                onKeyDown={(event) => handleKeyDown(index, event)}
                onPaste={handlePaste}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]*"
                maxLength={1}
                aria-label={t("verify.digitAria", { index: index + 1 })}
                className="aspect-square w-full rounded-lg border border-slate-300 bg-white text-center text-xl font-semibold tracking-widest text-slate-900 outline-none focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            ))}
          </div>
          {error && <p className="text-sm text-rose-600" role="alert">{error}</p>}
          {info && !error && <p className="text-sm text-emerald-600">{info}</p>}
          <button
            type="submit"
            disabled={submitting || code.length !== CODE_LENGTH}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {ctaLabel}
            <ArrowRight size={16} />
          </button>
        </form>
        <div className="mt-5 flex items-center justify-between text-sm text-slate-500">
          <button
            type="button"
            onClick={handleResend}
            disabled={!canResend}
            className="font-semibold text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
          >
            {resendLabel}
          </button>
          <Link to="/login" className="font-semibold text-slate-500">
            {t("trial.signIn")}
          </Link>
        </div>
      </section>
    </main>
  );
}
