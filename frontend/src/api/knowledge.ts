import { apiJson } from "./client";

export interface KnowledgeDocument {
  id: string; project_id: number | null; scope: "project" | "account";
  title: string; kind: string; status: string; error: string; external_use: number;
  generated: number; version_count: number; created_at: string; updated_at: string;
  versions?: { id: string; number: number; text_length: number }[];
}
export interface KnowledgeCitation {
  id: string; label: string; title: string; quote: string; heading: string;
  start: number; end: number; page: number | null; generated: boolean; url: string;
}
export interface KnowledgeSearch {
  retrieval_id: string; status: string; warnings: string[]; citations: KnowledgeCitation[];
  hits: { title: string; text: string; lanes: string[]; fusion_score: number; rerank_score: number | null }[];
  lane_results: Record<string, string[]>; timings: Record<string, number>;
}
export const listKnowledge = (project: number, offset = 0) =>
  apiJson<KnowledgeDocument[]>(`/knowledge/documents?project_id=${project}&offset=${offset}`);
export const knowledgeDocument = (id: string) => apiJson<KnowledgeDocument>(`/knowledge/documents/${id}`);
export const importKnowledge = (body: FormData | Record<string, unknown>) =>
  apiJson<{ task_id?: string; document_id: string; duplicate: boolean }>("/knowledge/documents",
    { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body) });
export const updateKnowledge = (id: string, body: Record<string, unknown>) =>
  apiJson(`/knowledge/documents/${id}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteKnowledge = (id: string) => apiJson(`/knowledge/documents/${id}`, { method: "DELETE" });
export const reindexKnowledge = (id: string) => apiJson(`/knowledge/documents/${id}/reindex`, { method: "POST" });
export const backfillKnowledge = (project: number) =>
  apiJson(`/projects/${project}/knowledge/backfill-reports`, { method: "POST" });
export const searchKnowledge = (project: number, query: string, purpose: string) =>
  apiJson<KnowledgeSearch>(`/projects/${project}/knowledge/search`, { method: "POST", body: JSON.stringify({ query, purpose }) });
export const getKnowledgeSettings = () => apiJson<Record<string, unknown>>("/knowledge/settings");
export const rebuildKnowledge = () => apiJson("/knowledge/rebuild", { method: "POST" });
export const saveKnowledgeSettings = (body: Record<string, unknown>) =>
  apiJson<Record<string, unknown>>("/knowledge/settings", { method: "POST", body: JSON.stringify(body) });
export const testKnowledgeSettings = (body: Record<string, unknown>) =>
  apiJson<{ ok: boolean; dimensions: number }>("/knowledge/settings/test", { method: "POST", body: JSON.stringify(body) });
export const getCitation = (id: string) =>
  apiJson<KnowledgeCitation & { source_text: string }>(`/knowledge/citations/${id}`);
export const getKnowledgeVersion = (id: string, version: string) =>
  apiJson<{ text: string; chunks: { id: string; level: string; start_offset: number; end_offset: number }[] }>(
    `/knowledge/documents/${id}/versions/${version}`);
