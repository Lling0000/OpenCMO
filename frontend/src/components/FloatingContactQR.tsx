import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { MessageCircle, X } from "lucide-react";
import { useI18n } from "../i18n";

const DISMISS_STORAGE_KEY = "contact-qr-dismissed";
const FADE_IN_DELAY_MS = 1500;
const QR_ASSET = "/contact-qr.png";

function readDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(DISMISS_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeDismissed(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(DISMISS_STORAGE_KEY, "1");
  } catch {
    // ignore — storage might be disabled (privacy mode etc.)
  }
}

function useHasHover(): boolean {
  const [hasHover, setHasHover] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return true;
    }
    return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mql = window.matchMedia("(hover: hover) and (pointer: fine)");
    const handler = (event: MediaQueryListEvent) => setHasHover(event.matches);
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handler);
      return () => mql.removeEventListener("change", handler);
    }
    // Safari < 14 fallback
    mql.addListener(handler);
    return () => mql.removeListener(handler);
  }, []);

  return hasHover;
}

export function FloatingContactQR() {
  const { t } = useI18n();
  const [dismissed, setDismissed] = useState<boolean>(readDismissed);
  const [visible, setVisible] = useState<boolean>(false);
  const [expanded, setExpanded] = useState<boolean>(false);
  const hasHover = useHasHover();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const panelId = useId();

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(true), FADE_IN_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  // Tap-outside collapse for touch devices.
  useEffect(() => {
    if (hasHover || !expanded) return;
    const onPointerDown = (event: globalThis.PointerEvent) => {
      const root = rootRef.current;
      if (!root) return;
      if (event.target instanceof Node && root.contains(event.target)) {
        return;
      }
      setExpanded(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [expanded, hasHover]);

  // Escape collapses the open card.
  useEffect(() => {
    if (!expanded) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded]);

  const handleDismiss = useCallback(() => {
    writeDismissed();
    setDismissed(true);
  }, []);

  const handlePointerEnter = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (event.pointerType !== "mouse" || !hasHover) return;
      setExpanded(true);
    },
    [hasHover],
  );

  const handlePointerLeave = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (event.pointerType !== "mouse" || !hasHover) return;
      setExpanded(false);
    },
    [hasHover],
  );

  const handleFocus = useCallback(() => setExpanded(true), []);
  const handleBlur = useCallback((event: FocusEvent<HTMLDivElement>) => {
    const next = event.relatedTarget as Node | null;
    if (next && rootRef.current?.contains(next)) return;
    setExpanded(false);
  }, []);

  const handlePillClick = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handlePillKey = useCallback((event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setExpanded((prev) => !prev);
    }
  }, []);

  if (dismissed) return null;

  return (
    <div
      ref={rootRef}
      className={`fixed bottom-4 right-4 z-50 flex flex-col items-end transition-opacity duration-500 sm:bottom-6 sm:right-6 ${
        visible ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      <button
        type="button"
        onClick={handleDismiss}
        aria-label={t("contactQR.close")}
        className="mb-2 inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-[#0c2538]/85 text-white/75 shadow-[0_8px_20px_rgba(8,32,50,0.32)] backdrop-blur transition-colors hover:bg-[#082032] hover:text-white"
      >
        <X size={14} aria-hidden="true" />
      </button>

      <div
        className={`grid origin-bottom-right transition-[grid-template-rows,opacity,transform] duration-300 ease-out ${
          expanded
            ? "scale-100 grid-rows-[1fr] opacity-100"
            : "pointer-events-none scale-95 grid-rows-[0fr] opacity-0"
        }`}
        aria-hidden={expanded ? "false" : "true"}
      >
        <div className="overflow-hidden">
          <div
            id={panelId}
            role="dialog"
            aria-label={t("contactQR.heading")}
            className="mb-3 w-[224px] rounded-3xl border border-white/10 bg-[#082032] p-4 text-white shadow-[0_24px_60px_rgba(8,32,50,0.32)] backdrop-blur sm:w-[248px] sm:p-5"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/55">
              {t("contactQR.heading")}
            </p>
            <p className="mt-2 text-sm font-semibold leading-5 text-white">
              {t("contactQR.subheading")}
            </p>
            <div className="mt-4 overflow-hidden rounded-2xl bg-white p-2">
              <img
                src={QR_ASSET}
                alt={t("contactQR.imageAlt")}
                width={240}
                height={240}
                loading="lazy"
                className="block h-[160px] w-full rounded-xl sm:h-[200px]"
              />
            </div>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={handlePillClick}
        onKeyDown={handlePillKey}
        aria-expanded={expanded}
        aria-controls={panelId}
        aria-label={t("contactQR.pillLabel")}
        className="inline-flex items-center gap-2 rounded-full bg-[#082032] px-4 py-2.5 text-sm font-semibold text-[#f7ecde] shadow-[0_16px_40px_rgba(8,32,50,0.32)] transition-colors hover:bg-[#0c2538] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c96f45] focus-visible:ring-offset-2 focus-visible:ring-offset-[#08141f]"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#c96f45] text-white">
          <MessageCircle size={15} aria-hidden="true" />
        </span>
        <span>{t("contactQR.pillLabel")}</span>
      </button>
    </div>
  );
}
