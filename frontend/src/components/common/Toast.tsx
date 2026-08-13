import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertCircle, Info, X, Loader2 } from "lucide-react";

export type ToastKind = "success" | "error" | "info" | "loading";

export interface ToastOptions {
  /** Auto-dismiss after N ms. 0 or undefined → sticky (loading default). */
  duration?: number;
  /** Show a small action button (e.g. "Undo", "Retry"). */
  action?: { label: string; onClick: () => void };
}

interface ToastRecord {
  id: number;
  kind: ToastKind;
  message: string;
  duration: number;
  action?: ToastOptions["action"];
}

interface ToastApi {
  show: (kind: ToastKind, message: string, opts?: ToastOptions) => number;
  success: (message: string, opts?: ToastOptions) => number;
  error: (message: string, opts?: ToastOptions) => number;
  info: (message: string, opts?: ToastOptions) => number;
  /** Returns the toast id so the caller can dismiss/update it. */
  loading: (message: string, opts?: ToastOptions) => number;
  dismiss: (id: number) => void;
  /** Update an existing toast in-place (useful: loading → success). */
  update: (id: number, kind: ToastKind, message: string, opts?: ToastOptions) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const DEFAULT_DURATION: Record<ToastKind, number> = {
  success: 3200,
  error: 5200,
  info: 3600,
  loading: 0,
};

const PALETTE: Record<
  ToastKind,
  { bg: string; border: string; iconBg: string; iconColor: string; text: string }
> = {
  success: {
    bg: "bg-white",
    border: "border-emerald-200",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
    text: "text-slate-900",
  },
  error: {
    bg: "bg-white",
    border: "border-rose-200",
    iconBg: "bg-rose-50",
    iconColor: "text-rose-600",
    text: "text-slate-900",
  },
  info: {
    bg: "bg-white",
    border: "border-slate-200",
    iconBg: "bg-slate-100",
    iconColor: "text-slate-600",
    text: "text-slate-900",
  },
  loading: {
    bg: "bg-white",
    border: "border-indigo-200",
    iconBg: "bg-indigo-50",
    iconColor: "text-indigo-600",
    text: "text-slate-900",
  },
};

function ToastIcon({ kind }: { kind: ToastKind }) {
  const cls = `h-4 w-4 ${PALETTE[kind].iconColor}`;
  if (kind === "success") return <CheckCircle2 className={cls} strokeWidth={2.4} />;
  if (kind === "error") return <AlertCircle className={cls} strokeWidth={2.4} />;
  if (kind === "loading") return <Loader2 className={`${cls} animate-spin`} strokeWidth={2.4} />;
  return <Info className={cls} strokeWidth={2.4} />;
}

function ToastItem({ toast, onDismiss }: { toast: ToastRecord; onDismiss: (id: number) => void }) {
  const p = PALETTE[toast.kind];
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 18, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.18 } }}
      transition={{ type: "spring", stiffness: 320, damping: 26 }}
      className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl ${p.bg} ${p.border} border px-4 py-3 shadow-[0_8px_28px_-12px_rgba(15,23,42,0.18)] backdrop-blur`}
    >
      <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${p.iconBg}`}>
        <ToastIcon kind={toast.kind} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm leading-snug ${p.text}`}>{toast.message}</p>
        {toast.action && (
          <button
            type="button"
            onClick={() => {
              toast.action!.onClick();
              onDismiss(toast.id);
            }}
            className="mt-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss"
        className="-mr-1 -mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <X className="h-3.5 w-3.5" strokeWidth={2.4} />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const counterRef = useRef(0);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    setToasts((curr) => curr.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const scheduleDismiss = useCallback(
    (id: number, duration: number) => {
      if (duration <= 0) return;
      const prev = timersRef.current.get(id);
      if (prev) clearTimeout(prev);
      const handle = setTimeout(() => dismiss(id), duration);
      timersRef.current.set(id, handle);
    },
    [dismiss],
  );

  const show = useCallback(
    (kind: ToastKind, message: string, opts?: ToastOptions): number => {
      const id = ++counterRef.current;
      const duration = opts?.duration ?? DEFAULT_DURATION[kind];
      const record: ToastRecord = { id, kind, message, duration, action: opts?.action };
      setToasts((curr) => {
        // Cap stack at 5; drop the oldest. Clear their timers too so we don't
        // leak setTimeout callbacks that fire dismiss() for gone-from-state ids.
        const next = [...curr, record];
        if (next.length <= 5) return next;
        const dropped = next.slice(0, next.length - 5);
        for (const d of dropped) {
          const timer = timersRef.current.get(d.id);
          if (timer) {
            clearTimeout(timer);
            timersRef.current.delete(d.id);
          }
        }
        return next.slice(next.length - 5);
      });
      scheduleDismiss(id, duration);
      return id;
    },
    [scheduleDismiss],
  );

  const update = useCallback(
    (id: number, kind: ToastKind, message: string, opts?: ToastOptions) => {
      const duration = opts?.duration ?? DEFAULT_DURATION[kind];
      setToasts((curr) =>
        curr.map((t) =>
          t.id === id
            ? { ...t, kind, message, duration, action: opts?.action ?? t.action }
            : t,
        ),
      );
      scheduleDismiss(id, duration);
    },
    [scheduleDismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      show,
      success: (m, o) => show("success", m, o),
      error: (m, o) => show("error", m, o),
      info: (m, o) => show("info", m, o),
      loading: (m, o) => show("loading", m, o),
      dismiss,
      update,
    }),
    [show, dismiss, update],
  );

  useEffect(() => {
    return () => {
      timersRef.current.forEach((t) => clearTimeout(t));
      timersRef.current.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={api}>
      {children}
      {typeof document !== "undefined"
        ? createPortal(
            <div
              aria-live="polite"
              aria-atomic="false"
              className="pointer-events-none fixed inset-x-0 top-4 z-[9999] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:right-6 sm:left-auto sm:top-auto sm:items-end sm:px-0"
            >
              <AnimatePresence initial={false}>
                {toasts.map((t) => (
                  <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
                ))}
              </AnimatePresence>
            </div>,
            document.body,
          )
        : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return ctx;
}
