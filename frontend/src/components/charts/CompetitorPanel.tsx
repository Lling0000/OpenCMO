import { useState } from "react";
import { Plus, Trash2, X, Sparkles, Loader2 } from "lucide-react";
import { useCompetitors, useAddCompetitor, useDeleteCompetitor, useDiscoverCompetitors } from "../../hooks/useGraphData";
import { useI18n } from "../../i18n";

export function CompetitorPanel({ projectId }: { projectId: number }) {
  const { data: competitors } = useCompetitors(projectId);
  const addComp = useAddCompetitor(projectId);
  const delComp = useDeleteCompetitor(projectId);
  const discover = useDiscoverCompetitors(projectId);
  const { t } = useI18n();

  const [showManual, setShowManual] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [kwInput, setKwInput] = useState("");

  const handleAdd = () => {
    if (!name.trim()) return;
    const keywords = kwInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    addComp.mutate(
      { name: name.trim(), url: url.trim() || undefined, keywords },
      {
        onSuccess: () => {
          setName("");
          setUrl("");
          setKwInput("");
          setShowManual(false);
        },
      },
    );
  };

  return (
    <div className="rounded-2xl border border-zinc-200/60 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-800">
          {t("competitor.title")}
        </h3>
        <div className="flex items-center gap-2">
          {/* AI Discover — Primary action */}
          <button
            onClick={() => discover.mutate()}
            disabled={discover.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-indigo-500 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-all hover:from-violet-600 hover:to-indigo-600 active:scale-95 disabled:opacity-60"
          >
            {discover.isPending ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Sparkles size={12} />
            )}
            {discover.isPending
              ? t("competitor.discovering")
              : t("competitor.aiDiscover")}
          </button>
          {/* Manual add — Secondary */}
          <button
            onClick={() => setShowManual(!showManual)}
            className="flex items-center gap-1 rounded-lg bg-zinc-50 px-2.5 py-1.5 text-xs font-medium text-zinc-500 ring-1 ring-inset ring-zinc-200/50 transition-all hover:bg-zinc-100 active:scale-95"
          >
            {showManual ? <X size={12} /> : <Plus size={12} />}
            {t("competitor.manual")}
          </button>
        </div>
      </div>

      {/* AI discovery result banner */}
      {discover.isSuccess && (
        <div className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700 ring-1 ring-emerald-200/60 animate-in fade-in slide-in-from-top-2 duration-300">
          ✨ {t("competitor.aiDiscoverSuccess").replace("{{count}}", String(discover.data?.competitors?.length ?? 0))}
        </div>
      )}

      {discover.isError && (
        <div className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600 ring-1 ring-rose-200/60">
          {t("competitor.aiDiscoverFailed")}
        </div>
      )}

      {/* Manual add form */}
      {showManual && (
        <div className="mb-4 space-y-2 rounded-xl bg-zinc-50/80 p-3 ring-1 ring-zinc-100 animate-in fade-in slide-in-from-top-2 duration-200">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("competitor.namePlaceholder")}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t("competitor.urlPlaceholder")}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <input
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            placeholder={t("competitor.kwPlaceholder")}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <button
            onClick={handleAdd}
            disabled={!name.trim() || addComp.isPending}
            className="w-full rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition-all hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.98]"
          >
            {addComp.isPending
              ? t("competitor.adding")
              : t("competitor.manualAdd")}
          </button>
        </div>
      )}

      {/* Competitor list */}
      {!competitors?.length ? (
        <p className="text-xs text-zinc-400">
          {t("competitor.noCompetitorsAi")}
        </p>
      ) : (
        <div className="space-y-1.5">
          {competitors.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors hover:bg-zinc-50"
            >
              <div className="min-w-0 flex-1">
                <span className="font-medium text-zinc-700">{c.name}</span>
                {c.url && (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-xs text-zinc-400 hover:text-indigo-500"
                  >
                    {c.url}
                  </a>
                )}
              </div>
              <button
                onClick={() => delComp.mutate(c.id)}
                className="rounded-lg p-1.5 text-zinc-300 hover:bg-rose-50 hover:text-rose-500 transition-all"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
