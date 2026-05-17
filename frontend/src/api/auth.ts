import { apiJson } from "./client";
import type { AccountUsage, AuthAccount, AuthUser } from "../types";

export interface AuthPayload {
  ok: boolean;
  authenticated: boolean;
  user: AuthUser;
  account: AuthAccount;
  is_admin: boolean;
  usage: AccountUsage;
}

export interface SignupResponse {
  ok: boolean;
  needs_verification: boolean;
  user_id: number;
  email: string;
  dev_mode?: boolean;
}

export interface ResendCodeResponse {
  ok: boolean;
  dev_mode?: boolean;
  error?: string;
  retry_after_seconds?: number;
}

export function getMe(): Promise<AuthPayload | { authenticated: false }> {
  return apiJson<AuthPayload | { authenticated: false }>("/auth/me");
}

export function signup(data: {
  email: string;
  password: string;
  name?: string;
  locale?: string;
}): Promise<SignupResponse> {
  return apiJson<SignupResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function login(data: {
  email: string;
  password: string;
}): Promise<AuthPayload> {
  return apiJson<AuthPayload>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function verifyEmail(data: {
  user_id: number;
  code: string;
}): Promise<AuthPayload> {
  return apiJson<AuthPayload>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function resendVerificationCode(data: {
  user_id: number;
  locale?: string;
}): Promise<ResendCodeResponse> {
  return apiJson<ResendCodeResponse>("/auth/resend-code", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiJson<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

export function getUsage(): Promise<AccountUsage> {
  return apiJson<AccountUsage>("/account/usage");
}
