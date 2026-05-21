import { useEffect, useRef } from "react";
import { ChatContainer } from "../chat/ChatContainer";
import { useChat } from "../../hooks/useChat";
import { useChatContext } from "../../hooks/useChatContext";
import { useI18n } from "../../i18n";

interface ProjectChatPanelProps {
  projectId: number;
  projectName: string;
  initialPrompt?: string;
  onPromptConsumed?: () => void;
}

export function ProjectChatPanel({
  projectId,
  projectName,
  initialPrompt,
  onPromptConsumed,
}: ProjectChatPanelProps) {
  const chat = useChat(projectId);
  const { data: chatContext } = useChatContext(projectId);
  const { t } = useI18n();
  const consumedPromptRef = useRef<string | null>(null);
  const {
    messages,
    isStreaming,
    currentAgent,
    projectId: activeProjectId,
    sendMessage,
    selectProject,
    sessionReady,
  } = chat;

  useEffect(() => {
    if (!sessionReady || activeProjectId === projectId) return;
    void selectProject(projectId);
  }, [activeProjectId, projectId, selectProject, sessionReady]);

  useEffect(() => {
    const prompt = initialPrompt?.trim() ?? "";
    if (!prompt) {
      consumedPromptRef.current = null;
      return;
    }
    if (!sessionReady || isStreaming || activeProjectId !== projectId) return;
    if (consumedPromptRef.current === prompt) return;

    consumedPromptRef.current = prompt;
    void sendMessage(prompt);
    onPromptConsumed?.();
  }, [activeProjectId, initialPrompt, isStreaming, onPromptConsumed, projectId, sendMessage, sessionReady]);

  return (
    <section
      aria-label={t("chat.title")}
      className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <header className="shrink-0 border-b border-slate-100 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-indigo-500">
          {t("chat.title")}
        </p>
        <div className="mt-1 min-w-0">
          <p className="text-xs font-medium text-slate-400">
            {t("chat.currentProject")}
          </p>
          <h2 className="truncate text-sm font-semibold text-slate-900">
            {projectName}
          </h2>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-3">
        {!sessionReady ? (
          <div className="flex min-h-0 flex-1 items-center justify-center text-sm text-slate-400">
            {t("chat.thinking")}
          </div>
        ) : (
          <ChatContainer
            messages={messages}
            isStreaming={isStreaming}
            currentAgent={currentAgent}
            sendMessage={sendMessage}
            hasMessages={messages.length > 0}
            projectId={activeProjectId}
            projectContext={chatContext ?? null}
            compact
          />
        )}
      </div>
    </section>
  );
}
