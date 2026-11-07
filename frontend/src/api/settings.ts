import { apiJson } from "./client";
import type { AISettings } from "../types";

export function getSettings(): Promise<AISettings> {
  return apiJson<AISettings>("/settings");
}

export type SettingsSavePayload = {
  OPENAI_API_KEY?: string;
  OPENAI_BASE_URL?: string;
  OPENCMO_MODEL_DEFAULT?: string;
  // Reddit
  REDDIT_CLIENT_ID?: string;
  REDDIT_CLIENT_SECRET?: string;
  REDDIT_USERNAME?: string;
  REDDIT_PASSWORD?: string;
  OPENCMO_AUTO_PUBLISH?: string;
  // Twitter
  TWITTER_API_KEY?: string;
  TWITTER_API_SECRET?: string;
  TWITTER_ACCESS_TOKEN?: string;
  TWITTER_ACCESS_SECRET?: string;
  // GEO
  ANTHROPIC_API_KEY?: string;
  GOOGLE_AI_API_KEY?: string;
  MOONSHOT_API_KEY?: string;
  DASHSCOPE_API_KEY?: string;
  DEEPSEEK_API_KEY?: string;
  ZHIPU_API_KEY?: string;
  DOUBAO_API_KEY?: string;
  CLORO_API_KEY?: string;
  OPENCMO_GEO_CHATGPT?: string;
  // SEO
  PAGESPEED_API_KEY?: string;
  GOOGLE_GSC_CREDENTIALS?: string;
  GOOGLE_GSC_SITE_URL?: string;
  // Search (Tavily)
  TAVILY_API_KEY?: string;
  // SERP
  DATAFORSEO_LOGIN?: string;
  DATAFORSEO_PASSWORD?: string;
  // Email
  OPENCMO_SMTP_HOST?: string;
  OPENCMO_SMTP_PORT?: string;
  OPENCMO_SMTP_USER?: string;
  OPENCMO_SMTP_PASS?: string;
  OPENCMO_REPORT_EMAIL?: string;
};

export function saveSettings(data: SettingsSavePayload): Promise<{ ok: boolean }> {
  return apiJson("/settings", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
