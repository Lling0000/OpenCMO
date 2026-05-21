import type { ChatMessage } from "../../types";
import type { ChatProjectContext } from "../../api/chatContext";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { AgentGrid } from "./AgentGrid";
import { ProjectContextCard } from "./ProjectContextCard";
import { useI18n } from "../../i18n";
import { ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import { useState } from "react";

function ContextBadge({ context }: { context: ChatProjectContext }) {
  const [open, setOpen] = useState(false);
  const { t } = useI18n();
  const { project, scores, keywords } = context;

  return (
    <div className="mb-3 rounded-xl border border-indigo-100 bg-indigo-50/50">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors"
      >
        <Sparkles size={12} />
        <span className="font-semibold">
          {t("chat.projectContextBadge")}: {project.brand_name}
        </span>
        <span className="flex-1" />
        <span className="text-[11px] text-indigo-400">
          SEO {scores.seo != null ? `${Math.round(scores.seo * 100)}%` : "—"}
          {" · "}GEO {scores.geo ?? "—"}
          {scores.community_hits != null ? ` · ${scores.community_hits} ${t("chat.discussions")}` : ""}
        </span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {open && (
        <div className="border-t border-indigo-100 px-3 py-2 text-xs text-slate-500 space-y-1">
          {keywords.length > 0 && (
            <p>
              <span className="font-medium text-slate-600">{t("chat.contextKeywords")}:</span>{" "}
              {keywords.join(", ")}
            </p>
          )}
          {context.competitors.length > 0 && (
            <p>
              <span className="font-medium text-slate-600">{t("chat.contextCompetitors")}:</span>{" "}
              {context.competitors.map((c) => c.label).join(", ")}
            </p>
          )}
          {context.keyword_gaps.length > 0 && (
            <p>
              <span className="font-medium text-amber-600">{t("chat.contextGaps")}:</span>{" "}
              {context.keyword_gaps.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function ChatContainer({
  messages,
  isStreaming,
  currentAgent,
  sendMessage,
  hasMessages,
  projectId,
  projectContext,
  compact = false,
}: {
  messages: ChatMessage[];
  isStreaming: boolean;
  currentAgent: string;
  sendMessage: (content: string) => void;
  hasMessages: boolean;
  projectId: number | null;
  projectContext?: ChatProjectContext | null;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const projectName = projectContext?.project.brand_name ?? null;

  return (
    <div className="flex flex-1 min-h-0 flex-col">
      {/* Agent badge */}
      <div className="mb-3 shrink-0">
        <p className="text-xs text-slate-400">
          {t("chat.agent", { name: currentAgent })}
        </p>
      </div>

      {/* When no messages: show project context + agent grid */}
      {!hasMessages ? (
        <div className="flex flex-1 min-h-0 flex-col mx-auto w-full max-w-3xl">
          <div className="flex-1 min-h-0 overflow-y-auto p-2">
            {projectContext && projectId ? (
              <div className="space-y-6">
                <ProjectContextCard
                  context={projectContext}
                  onSuggest={(prompt) => sendMessage(prompt)}
                  compact={compact}
                />
                {!compact && (
                  <div className="border-t border-slate-100 pt-6">
                    <AgentGrid
                      onSelect={(prompt) => sendMessage(prompt)}
                      projectName={projectName}
                    />
                  </div>
                )}
              </div>
            ) : (
              <AgentGrid
                onSelect={(prompt) => sendMessage(prompt)}
                projectName={projectName}
              />
            )}
          </div>
          <div className="shrink-0">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
          </div>
        </div>
      ) : (
        <div className="flex flex-1 min-h-0 flex-col">
          {/* Collapsed context badge when chatting */}
          {projectContext && <ContextBadge context={projectContext} />}
          <MessageList messages={messages} isStreaming={isStreaming} />
          <div className="shrink-0">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
          </div>
        </div>
      )}
    </div>
  );
}
