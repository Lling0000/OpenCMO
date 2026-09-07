import { useState } from "react";
import { useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, FileText, Search, Settings, Upload } from "lucide-react";
import { useI18n, type TranslationKey } from "../i18n";
import { useProjectSummary } from "../hooks/useProject";
import { ProjectHeader } from "../components/project/ProjectHeader";
import { ProjectTabs } from "../components/project/ProjectTabs";
import KnowledgeMarkdown from "../components/knowledge/KnowledgeMarkdown";
import * as api from "../api/knowledge";
import { utcDate } from "../utils/time";

const configuration: [string, TranslationKey, "text" | "password" | "number"][] = [
  ["embedding_base_url", "knowledge.embeddingUrl", "text"],
  ["embedding_model", "knowledge.embeddingModel", "text"],
  ["embedding_api_key", "knowledge.embeddingKey", "password"],
  ["rerank_base_url", "knowledge.rerankUrl", "text"],
  ["rerank_model", "knowledge.rerankModel", "text"],
  ["rerank_api_key", "knowledge.rerankKey", "password"],
  ["parent_tokens", "knowledge.parentTokens", "number"],
  ["child_tokens", "knowledge.childTokens", "number"],
  ["overlap_tokens", "knowledge.overlap", "number"],
  ["rerank_min_score", "knowledge.threshold", "number"],
];
const inputClass = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-200";
const buttonClass = "rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50";

export function KnowledgePage() {
  const projectId = Number(useParams().id);
  const { t } = useI18n();
  const cache = useQueryClient();
  const project = useProjectSummary(projectId);
  const [tab, setTab] = useState<"documents" | "search" | "settings">("documents");
  const [offset, setOffset] = useState(0);
  const documents = useQuery({ queryKey: ["knowledge", projectId, offset], queryFn: () => api.listKnowledge(projectId, offset), refetchInterval: 4000 });
  const settings = useQuery({ queryKey: ["knowledge", "settings"], queryFn: api.getKnowledgeSettings, refetchInterval: 4000 });
  const [changes, setChanges] = useState<Record<string, unknown>>({});
  const config = { ...settings.data, ...changes };
  const [type, setType] = useState<"file" | "text" | "url">("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [shared, setShared] = useState(false);
  const [external, setExternal] = useState(false);
  const [replaceId, setReplaceId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [purpose, setPurpose] = useState("internal");
  const [result, setResult] = useState<api.KnowledgeSearch | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [versionId, setVersionId] = useState("");
  const detail = useQuery({ queryKey: ["knowledge", "detail", previewId], queryFn: () => api.knowledgeDocument(previewId!), enabled: Boolean(previewId) });
  const selectedVersion = versionId || detail.data?.versions?.[0]?.id || "";
  const preview = useQuery({ queryKey: ["knowledge", "version", previewId, selectedVersion],
    queryFn: () => api.getKnowledgeVersion(previewId!, selectedVersion), enabled: Boolean(previewId && selectedVersion) });

  async function action(fn: () => Promise<unknown>, success: TranslationKey = "knowledge.saved") {
    setBusy(true); setNotice(""); setError("");
    try { await fn(); setNotice(t(success)); await cache.invalidateQueries({ queryKey: ["knowledge"] }); }
    catch (reason) { setError(t("knowledge.failedAction") + " " + (reason instanceof Error ? reason.message : "")); }
    finally { setBusy(false); }
  }
  async function importSource() {
    if (type === "file") {
      if (!file) return;
      const body = new FormData();
      body.set("file", file); body.set("project_id", String(projectId)); body.set("title", title || file.name);
      body.set("scope", shared ? "account" : "project"); body.set("external_use", String(external));
      if (replaceId) body.set("document_id", replaceId);
      await api.importKnowledge(body);
    } else {
      await api.importKnowledge({ project_id: projectId, title, [type === "url" ? "url" : "text"]: text,
        scope: shared ? "account" : "project", external_use: external, ...(replaceId ? { document_id: replaceId } : {}) });
    }
    setText(""); setFile(null); setTitle(""); setReplaceId(null);
  }
  const statusKey = (status: string): TranslationKey =>
    status === "ready" ? "knowledge.ready" : status === "failed" ? "knowledge.failed" : status === "cancelled" ? "knowledge.cancelled" : status === "indexing" ? "knowledge.indexing" : "knowledge.queued";

  return <div>
    {project.data && <><ProjectHeader project={project.data.project} isPaused={project.data.is_paused} /><ProjectTabs projectId={projectId} /></>}
    <header className="mb-6 flex items-start gap-3">
      <div className="rounded-2xl bg-blue-50 p-3 text-blue-700"><BookOpen size={24} /></div>
      <div><h1 className="text-2xl font-semibold tracking-tight">{t("knowledge.title")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("knowledge.description")}</p></div>
    </header>
    <nav aria-label={t("knowledge.title")} className="mb-6 flex flex-wrap gap-2">
      {([["documents", FileText], ["search", Search], ["settings", Settings]] as const).map(([key, Icon]) =>
        <button key={key} onClick={() => setTab(key)} className={buttonClass + (tab === key ? " border-blue-300 bg-blue-50 text-blue-800" : "")}>
          <Icon size={14} className="mr-2 inline" />{t(("knowledge." + key) as TranslationKey)}
        </button>)}
    </nav>
    {(error || notice) && <p role={error ? "alert" : "status"} className={"mb-4 rounded-xl p-3 text-sm " + (error ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800")}>{error || notice}</p>}
    {settings.data && !config.enabled && <p className="mb-4 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">
      {t("knowledge.enabled")} · <button className="underline" onClick={() => setTab("settings")}>{t("knowledge.settings")}</button>
    </p>}
    {tab === "documents" && <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {(["file", "text", "url"] as const).map(key =>
            <button key={key} className={buttonClass + (type === key ? " text-blue-700" : "")} onClick={() => { setType(key); setText(""); }}>{t(("knowledge." + key) as TranslationKey)}</button>)}
          <button disabled={busy} className={buttonClass + " ml-auto"} onClick={() => void action(() => api.backfillKnowledge(projectId))}>{t("knowledge.backfill")}</button>
        </div>
        {replaceId && <p className="mb-2 text-sm text-blue-700">{t("knowledge.newVersion")} <button onClick={() => setReplaceId(null)} className="underline">{t("knowledge.close")}</button></p>}
        <label className="mb-3 block text-sm">{t("knowledge.name")}<input className={inputClass + " mt-1"} value={title} onChange={e => setTitle(e.target.value)} /></label>
        {type === "file" ? <label className="mb-3 block rounded-xl border border-dashed border-slate-300 p-5 text-sm">
          <Upload size={18} className="mb-2 text-blue-600" /><span>{t("knowledge.limits")}</span>
          <input type="file" accept=".pdf,.docx,.md,.markdown,.txt" className="mt-3 block w-full text-sm" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        </label> : <label className="block text-sm">{t(type === "url" ? "knowledge.url" : "knowledge.text")}
          <textarea className={inputClass + " mt-1"} rows={type === "url" ? 2 : 7} value={text} onChange={e => setText(e.target.value)} />
        </label>}
        <div className="my-4 flex flex-wrap gap-5 text-sm">
          <label><input type="checkbox" checked={shared} onChange={e => setShared(e.target.checked)} className="mr-2" />{t("knowledge.shared")}</label>
          <label><input type="checkbox" checked={external} onChange={e => setExternal(e.target.checked)} className="mr-2" />{t("knowledge.external")}</label>
        </div>
        <button className="rounded-xl bg-blue-700 px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={busy || (type === "file" ? !file : !title.trim() || !text.trim())} onClick={() => void action(importSource)}>{t("knowledge.import")}</button>
      </section>
      <section className="space-y-3">
        {documents.error && <p role="alert">{t("knowledge.failedAction")}</p>}
        {!documents.data?.length && <p className="rounded-2xl border border-dashed p-8 text-center text-slate-500">{t("knowledge.empty")}</p>}
        {documents.data?.map(doc => <article key={doc.id} className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0"><h2 className="break-words font-semibold">{doc.title}</h2>
              <p className="mt-1 text-xs text-slate-500">{t(doc.kind === "report" ? "project.reports" : doc.kind === "url" ? "knowledge.url" : doc.kind === "file" ? "knowledge.file" : "knowledge.text")} · {t(statusKey(doc.status))} · {utcDate(doc.created_at).toLocaleDateString()} · v{doc.version_count}</p>
              {doc.generated === 1 && <p className="mt-2 text-xs text-amber-700">{t("knowledge.generated")}</p>}
              {doc.error && <p className="mt-2 break-words text-xs text-red-600">{doc.error}</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              <button className={buttonClass} onClick={() => { setPreviewId(doc.id); setVersionId(""); }}>{t("knowledge.preview")}</button>
              <button disabled={busy} className={buttonClass} onClick={() => void action(() => api.reindexKnowledge(doc.id))}>{t("knowledge.retry")}</button>
              <button className={buttonClass} onClick={() => { setReplaceId(doc.id); setTitle(doc.title); setType("file"); window.scrollTo({ top: 0, behavior: "smooth" }); }}>{t("knowledge.newVersion")}</button>
              <button disabled={busy} className={buttonClass + " text-red-700"} onClick={() => {
                if (window.confirm(t("knowledge.confirmDelete"))) void action(() => api.deleteKnowledge(doc.id));
              }}>{t("knowledge.remove")}</button>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs">
            <label><input type="checkbox" className="mr-2" disabled={busy} checked={doc.scope === "account"}
              onChange={e => void action(() => api.updateKnowledge(doc.id, { scope: e.target.checked ? "account" : "project" }))} />{t("knowledge.shared")}</label>
            <label><input type="checkbox" className="mr-2" disabled={busy} checked={Boolean(doc.external_use)}
              onChange={e => void action(() => api.updateKnowledge(doc.id, { external_use: e.target.checked }))} />{t("knowledge.external")}</label>
          </div>
        </article>)}
        <div className="flex gap-2"><button className={buttonClass} disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>{t("knowledge.previous")}</button>
          <button className={buttonClass} disabled={(documents.data?.length ?? 0) < 50} onClick={() => setOffset(offset + 50)}>{t("knowledge.next")}</button></div>
      </section>
      {previewId && <section className="rounded-2xl border bg-white p-5">
        <div className="flex items-center gap-3"><h2 className="flex-1 font-semibold">{detail.data?.title}</h2>
          <select className={inputClass + " max-w-40"} aria-label={t("knowledge.preview")} value={selectedVersion} onChange={e => setVersionId(e.target.value)}>
            {detail.data?.versions?.map(v => <option key={v.id} value={v.id}>v{v.number}</option>)}</select>
          <button className={buttonClass} onClick={() => setPreviewId(null)}>{t("knowledge.close")}</button></div>
        <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap break-words font-sans text-sm">{preview.data?.text}</pre>
        <details className="mt-3"><summary className="cursor-pointer text-sm">{t("knowledge.preview")} ({preview.data?.chunks.length ?? 0})</summary>
          <pre className="max-h-60 overflow-auto text-xs">{JSON.stringify(preview.data?.chunks, null, 2)}</pre></details>
      </section>}
    </div>}
    {tab === "search" && <section className="rounded-2xl border bg-white p-5">
      <label className="block text-sm">{t("knowledge.query")}<textarea className={inputClass + " mt-2"} rows={3} value={query} onChange={e => setQuery(e.target.value)} /></label>
      <div className="my-3 flex gap-3"><select className={inputClass + " max-w-64"} value={purpose} aria-label={t("knowledge.mode")} onChange={e => setPurpose(e.target.value)}>
        <option value="internal">{t("knowledge.internal")}</option><option value="content">{t("knowledge.outbound")}</option></select>
        <button className={buttonClass} disabled={busy || !query.trim()} onClick={() => void action(async () => setResult(await api.searchKnowledge(projectId, query, purpose)), "knowledge.searchComplete")}>{t("knowledge.search")}</button></div>
      {result && <>
        {result.warnings.length > 0 && <p className="my-3 text-sm text-amber-700">{t("knowledge.degraded")}</p>}
        {!result.hits.length && <p>{t("knowledge.noResults")}</p>}
        {result.citations.map(cite => <article key={cite.id} className="my-3 rounded-xl border p-4">
          <KnowledgeMarkdown>{`[${cite.label}](${cite.url}) **${cite.title}**\n\n${cite.quote}`}</KnowledgeMarkdown>
        </article>)}
        <details className="mt-4"><summary className="cursor-pointer text-sm">{t("knowledge.details")}</summary>
          <pre className="mt-3 max-h-96 overflow-auto text-xs">{JSON.stringify({ lanes: result.lane_results, timings: result.timings, warnings: result.warnings,
            scores: result.hits.map(h => ({ title: h.title, lanes: h.lanes, fusion: h.fusion_score, rerank: h.rerank_score })) }, null, 2)}</pre></details>
      </>}
    </section>}
    {tab === "settings" && <section className="rounded-2xl border bg-white p-5">
      <label className="mb-5 block font-medium"><input type="checkbox" className="mr-2" checked={Boolean(config.enabled)}
        onChange={e => setChanges({ ...changes, enabled: e.target.checked })} />{t("knowledge.enabled")}</label>
      <div className="grid gap-4 md:grid-cols-2">{configuration.map(([key, label, type]) => <label key={key} className="text-sm">
        {t(label)}<input className={inputClass + " mt-1"} type={type} step={key === "rerank_min_score" ? "0.01" : undefined}
          autoComplete={type === "password" ? "new-password" : undefined} value={String(config[key] ?? "")}
          placeholder={type === "password" && config[key + "_set"] ? t("knowledge.configured") : ""}
          onChange={e => { const next = { ...changes };
            if (type === "password" && !e.target.value) delete next[key];
            else next[key] = type === "number" ? Number(e.target.value) : e.target.value;
            setChanges(next);
          }} /></label>)}</div>
      <div className="mt-6 flex flex-wrap gap-2">
        <button className={buttonClass} disabled={busy} onClick={() => void action(async () => {
          await api.saveKnowledgeSettings(changes); setChanges({});
        })}>{t("knowledge.save")}</button>
        <button className={buttonClass} disabled={busy} onClick={() => void action(() => api.testKnowledgeSettings(changes), "knowledge.success")}>{t("knowledge.test")}</button>
        <button className={buttonClass} disabled={busy || !settings.data?.enabled || !settings.data?.embedding_api_key_set}
          onClick={() => void action(api.rebuildKnowledge)}>{t("knowledge.rebuildAll")}</button>
      </div>
    </section>}
  </div>;
}
