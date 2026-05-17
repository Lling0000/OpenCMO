import { buildUserKeysHeader } from "./userKeys";

const API_PREFIX = "/api/v1";
const PUBLIC_BYOK_PATHS = new Set([
  "/auth/login",
  "/auth/logout",
  "/auth/me",
  "/auth/signup",
  "/auth/verify-email",
  "/auth/resend-code",
  "/github-stats",
  "/health",
  "/site/stats",
  "/waitlist",
]);

function shouldSendUserKeys(path: string): boolean {
  return !PUBLIC_BYOK_PATHS.has(path.split("?")[0] ?? path);
}

export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (
    init?.body &&
    typeof init.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const token = localStorage.getItem("opencmo_token");
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (shouldSendUserKeys(path)) {
    const keysHeader = buildUserKeysHeader();
    if (keysHeader) headers.set("X-User-Keys", keysHeader);
  }

  const resp = await fetch(`${API_PREFIX}${path}`, { ...init, headers });
  if (resp.status === 401) {
    window.dispatchEvent(new CustomEvent("opencmo:unauthorized"));
  }
  return resp;
}

export async function apiJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const resp = await apiFetch(path, init);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(
      resp.status,
      getApiErrorMessage(body, resp.statusText),
      body.error_code ?? body.error,
      body,
    );
  }
  return resp.json() as Promise<T>;
}

function getApiErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;

  const payload = body as {
    error?: unknown;
    detail?: unknown;
    message?: unknown;
  };
  const candidate = payload.error ?? payload.detail ?? payload.message;

  if (typeof candidate === "string" && candidate.trim()) {
    return candidate;
  }
  if (Array.isArray(candidate)) {
    const messages = candidate
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const issue = item as { msg?: unknown; loc?: unknown };
        const msg = typeof issue.msg === "string" ? issue.msg : "";
        const loc = Array.isArray(issue.loc) ? issue.loc.join(".") : "";
        return loc && msg ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (candidate && typeof candidate === "object") {
    try {
      return JSON.stringify(candidate);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public errorCode?: string,
    public payload?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
