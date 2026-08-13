import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { History, Plus } from "lucide-react";
import { useChat } from "../hooks/useChat";
import { useChatContext } from "../hooks/useChatContext";
import { useProjects } from "../hooks/useProjects";
import { ChatContainer } from "../components/chat/ChatContainer";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatSkeleton } from "../components/common/Skeleton";
import { useI18n } from "../i18n";

function parseProjectId(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [initialProjectId] = useState<number | null>(() =>
    parseProjectId(searchParams.get("project_id")),
  );
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const chat = useChat(initialProjectId);
  const { data: projects } = useProjects();
  const { data: chatContext } = useChatContext(chat.projectId);
  const { t } = useI18n();
  const activeProject =
    projects?.find((project) => project.id === chat.projectId) ?? null;
  const currentProjectLabel =
    activeProject?.brand_name ??
    (chat.projectId != null ? `#${chat.projectId}` : t("chat.noProjectSelected"));

  useEffect(() => {
    if (!chat.sessionReady) return;
    const currentProjectId = parseProjectId(searchParams.get("project_id"));
    if (currentProjectId === chat.projectId) return;

    const nextParams = new URLSearchParams(searchParams);
    if (chat.projectId != null) {
      nextParams.set("project_id", String(chat.projectId));
    } else {
      nextParams.delete("project_id");
    }
    setSearchParams(nextParams, { replace: true });
  }, [chat.projectId, chat.sessionReady, searchParams, setSearchParams]);

  if (!chat.sessionReady) return <ChatSkeleton />;

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4 overflow-hidden">
      <ChatSidebar
        sessions={chat.sessions}
        activeSessionId={chat.sessionId}
        onSelect={chat.loadSession}
        onDelete={chat.removeSession}
        onNewChat={() => {
          void chat.resetChat();
        }}
        mobileOpen={mobileHistoryOpen}
        onCloseMobile={() => setMobileHistoryOpen(false)}
      />
      <div className="flex flex-1 flex-col min-w-0">
        <div className="mb-3 flex items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileHistoryOpen(true)}
            className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
          >
            <History size={16} />
            {t("chat.history")}
          </button>
          <button
            type="button"
            onClick={() => {
              void chat.resetChat();
            }}
            className="flex h-10 items-center gap-2 rounded-xl bg-slate-900 px-3 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
          >
            <Plus size={16} />
            {t("chat.newChat")}
          </button>
        </div>
        <div className="mb-4 shrink-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-indigo-500">
                {t("chat.currentProject")}
              </p>
              <h1 className="mt-1 text-lg font-semibold text-slate-900">
                {currentProjectLabel}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                {t("chat.projectHint")}
              </p>
            </div>

            <label className="flex w-full max-w-sm flex-col gap-1 text-sm text-slate-500">
              <span>{t("chat.selectProject")}</span>
              <select
                value={chat.projectId ?? ""}
                onChange={(event) => {
                  void chat.selectProject(parseProjectId(event.target.value));
                }}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              >
                <option value="">{t("chat.allProjects")}</option>
                {(projects ?? []).map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.brand_name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <ChatContainer
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          currentAgent={chat.currentAgent}
          sendMessage={chat.sendMessage}
          hasMessages={chat.messages.length > 0}
          projectId={chat.projectId}
          projectContext={chatContext ?? null}
        />
      </div>
    </div>
  );
}
