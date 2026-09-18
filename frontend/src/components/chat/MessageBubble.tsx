import ReactMarkdown from "../knowledge/KnowledgeMarkdown";
import { useI18n } from "../../i18n";
import type { ChatMessage } from "../../types";
import { Bot, User, CheckCircle, Loader2 } from "lucide-react";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const { t } = useI18n();
  const isUser = message.role === "user";
  const avatarClassName = isUser ? "bg-slate-200" : "bg-black";
  const containerClassName = isUser ? "text-right" : "";
  const bubbleClassName = isUser
    ? "bg-slate-100 text-slate-900 rounded-3xl rounded-tr-sm"
    : "text-slate-800";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${avatarClassName}`}
      >
        {isUser ? (
          <User size={16} className="text-slate-600" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>
      <div className={`max-w-[80%] ${containerClassName}`}>
        {!isUser && message.agent && (
          <span className="mb-2 inline-block font-semibold text-slate-800 text-[13px]">
            {message.agent}
          </span>
        )}
        {message.rag_status === "running" && <p role="status" className="text-xs text-slate-500">{t("knowledge.searching")}</p>}
        {message.rag_status === "degraded" && <p className="text-xs text-amber-700">{t("knowledge.degraded")}</p>}
        {message.tools && message.tools.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {message.tools.map((tool, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 rounded-lg px-2 py-0.5 text-[10px] font-medium ${
                  tool.done
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-amber-50 text-amber-700"
                }`}
              >
                {tool.done ? (
                  <CheckCircle size={10} />
                ) : (
                  <Loader2 size={10} className="animate-spin" />
                )}
                {tool.name}
              </span>
            ))}
          </div>
        )}
        <div
          className={`inline-block px-4 py-3 text-[15px] leading-relaxed ${bubbleClassName}`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown>{message.content || "\u200B"}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
