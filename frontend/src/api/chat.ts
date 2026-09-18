import { apiFetch, apiJson } from "./client";
import { buildUserKeysHeader } from "./userKeys";
import type { ChatEvent, ChatSessionSummary } from "../types";

export async function createSession(projectId?: number | null): Promise<string> {
  const resp = await apiFetch("/chat/sessions", {
    method: "POST",
    body: projectId != null ? JSON.stringify({ project_id: projectId }) : undefined,
  });
  if (!resp.ok) throw new Error("Failed to create chat session");
  const data = await resp.json();
  return data.session_id;
}

export function listSessions(): Promise<ChatSessionSummary[]> {
  return apiJson<ChatSessionSummary[]>("/chat/sessions");
}

export function getSessionMessages(
  sessionId: string,
): Promise<{ role: string; content: string; citations?: import("./knowledge").KnowledgeCitation[]; retrieval_id?: string; rag_status?: string }[]> {
  return apiJson(`/chat/sessions/${sessionId}/messages`);
}

export function deleteSession(
  sessionId: string,
): Promise<{ ok: boolean }> {
  return apiJson(`/chat/sessions/${sessionId}`, { method: "DELETE" });
}

export async function* streamChat(
  sessionId: string,
  message: string,
  projectId?: number | null,
  locale?: string,
): AsyncGenerator<ChatEvent> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = localStorage.getItem("opencmo_token");
  if (token) headers.Authorization = `Bearer ${token}`;
  const keysHeader = buildUserKeysHeader();
  if (keysHeader) headers["X-User-Keys"] = keysHeader;

  const resp = await fetch("/api/v1/chat", {
    method: "POST",
    headers,
    body: JSON.stringify({
      session_id: sessionId,
      message,
      rag_mode: localStorage.getItem("opencmo_rag_mode") || "auto",
      ...(projectId != null ? { project_id: projectId } : {}),
      ...(locale ? { locale } : {}),
    }),
  });

  if (!resp.ok) {
    if (resp.status === 401) {
      window.dispatchEvent(new CustomEvent("opencmo:unauthorized"));
    }
    throw new Error(`Chat request failed: ${resp.status}`);
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as ChatEvent;
        } catch {
          // skip malformed events
        }
      }
    }
  }
}
