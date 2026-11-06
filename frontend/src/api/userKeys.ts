/**
 * User API Keys — stored in localStorage, injected for console requests.
 *
 * Each user's keys stay in their own browser until a console action needs
 * provider access. They are sent via `X-User-Keys` for that request and
 * injected into a request-local ContextVar on the backend.
 */

import type { AISettings } from "../types";

const STORAGE_KEY = "opencmo_user_keys";

/** Keys that the backend reads from X-User-Keys header */
export const USER_KEY_NAMES = [
  "OPENAI_API_KEY",
  "OPENAI_BASE_URL",
  "OPENCMO_MODEL_DEFAULT",
  "TAVILY_API_KEY",
  "ANTHROPIC_API_KEY",
  "GOOGLE_AI_API_KEY",
  "PAGESPEED_API_KEY",
  "GOOGLE_GSC_CREDENTIALS",
  "GOOGLE_GSC_SITE_URL",
  "MOONSHOT_API_KEY",
  "DASHSCOPE_API_KEY",
  "DEEPSEEK_API_KEY",
  "ZHIPU_API_KEY",
  "DOUBAO_API_KEY",
  "CLORO_API_KEY",
] as const;

export type UserKeyName = (typeof USER_KEY_NAMES)[number];
export type UserKeys = Partial<Record<UserKeyName, string>>;

/** Read all user keys from localStorage */
export function getUserKeys(): UserKeys {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** Save all user keys to localStorage */
export function setUserKeys(keys: UserKeys): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
  // Dispatch event so SetupBanner and other components can react
  window.dispatchEvent(new CustomEvent("opencmo:keys-changed"));
}

/** Get a single key */
export function getUserKey(name: UserKeyName): string {
  return getUserKeys()[name] ?? "";
}

/** Set a single key (merges with existing) */
export function setUserKey(name: UserKeyName, value: string): void {
  const keys = getUserKeys();
  if (value) {
    keys[name] = value;
  } else {
    delete keys[name];
  }
  setUserKeys(keys);
}

/** Build the base64-encoded header value for X-User-Keys */
export function buildUserKeysHeader(): string | null {
  const keys = getUserKeys();
  // Only include non-empty values
  const filtered: Record<string, string> = {};
  for (const [k, v] of Object.entries(keys)) {
    if (v) filtered[k] = v;
  }
  if (Object.keys(filtered).length === 0) return null;
  return btoa(JSON.stringify(filtered));
}

/** Quick check: does the user have essential keys configured? */
export function hasEssentialKeys(): { llm: boolean; tavily: boolean } {
  const keys = getUserKeys();
  return {
    llm: !!keys.OPENAI_API_KEY,
    tavily: !!keys.TAVILY_API_KEY,
  };
}

export function getEffectiveKeyStatus(settings?: AISettings | null) {
  const keys = getUserKeys();
  const browserOverride = {
    llm: !!keys.OPENAI_API_KEY,
    tavily: !!keys.TAVILY_API_KEY,
  };
  const serverDefault = {
    llm: !!settings?.api_key_set,
    tavily: !!settings?.tavily_key_set,
  };
  return {
    browserOverride,
    serverDefault,
    effective: {
      llm: browserOverride.llm || serverDefault.llm,
      tavily: browserOverride.tavily || serverDefault.tavily,
    },
  };
}
