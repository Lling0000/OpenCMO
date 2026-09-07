import { useState, useCallback, useEffect, useRef } from "react";
import {
  createSession,
  streamChat,
  listSessions,
  getSessionMessages,
  deleteSession,
} from "../api/chat";
import { useI18n } from "../i18n";
import type { ChatMessage, ChatEvent, ToolStatus, ChatSessionSummary } from "../types";

let msgIdCounter = 0;
function nextId() {
  return `msg-${++msgIdCounter}`;
}

const TOOL_LABELS: Record<string, string> = {
  crawl_website: "Analyzing website",
  web_search: "Researching",
  analyze_competitor: "Analyzing competitor",
  generate_research_brief: "Preparing brief",
  generate_twitter_content: "Drafting Twitter/X content",
  generate_reddit_content: "Drafting Reddit content",
  generate_linkedin_content: "Drafting LinkedIn content",
  generate_producthunt_content: "Drafting Product Hunt launch copy",
  generate_hackernews_content: "Drafting Hacker News post",
  generate_blog_content: "Drafting article",
  generate_ruanyifeng_content: "Drafting weekly submission",
  generate_zhihu_content: "Drafting Zhihu content",
  generate_xiaohongshu_content: "Drafting Xiaohongshu note",
  generate_v2ex_content: "Drafting V2EX post",
  generate_juejin_content: "Drafting Juejin article",
  generate_jike_content: "Drafting Jike post",
  generate_wechat_content: "Drafting WeChat article",
  generate_oschina_content: "Drafting OSChina content",
  generate_gitcode_content: "Drafting GitCode content",
  generate_sspai_content: "Drafting SSPAI article",
  generate_infoq_content: "Drafting InfoQ article",
  generate_devto_content: "Drafting Dev.to article",
  research_trends: "Researching trends",
  github_user_discovery: "Finding GitHub prospects",
  get_competitive_landscape: "Analyzing market landscape",
};

function formatToolLabel(name?: string | null): string {
  if (!name) return "Working";
  if (TOOL_LABELS[name]) return TOOL_LABELS[name];
  return name
    .replace(/^transfer_to_/, "")
    .replace(/^generate_/, "")
    .replace(/_/g, " ")
    .replace(/\bexpert\b/gi, "")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/^./, (char) => char.toUpperCase()) || "Working";
}

function isInternalHandoffTool(name?: string | null): boolean {
  return Boolean(name && name.startsWith("transfer_to_"));
}

export function useChat(initialProjectId: number | null = null) {
  const { locale } = useI18n();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<number | null>(initialProjectId);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAgent, setCurrentAgent] = useState("CMO Agent");
  // Track whether sessionReady means we can accept input (even without a session yet)
  const [ready, setReady] = useState(false);
  const creatingSessionRef = useRef(false);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch {
      // ignore
    }
  }, []);

  // On mount: just load existing sessions list, mark as ready (no auto session creation)
  useEffect(() => {
    void refreshSessions().then(() => setReady(true));
  }, [refreshSessions]);

  // Ensure a session exists for sending messages. Returns sessionId.
  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId;
    if (creatingSessionRef.current) {
      // Wait for existing creation to finish
      await new Promise<void>((resolve) => {
        const interval = setInterval(() => {
          if (!creatingSessionRef.current) {
            clearInterval(interval);
            resolve();
          }
        }, 50);
      });
      // sessionId should be set by now via setState, but we read from the closure
      // So we return a promise that resolves with the updated value
      return new Promise<string>((resolve) => {
        setSessionId((current) => {
          if (current) resolve(current);
          return current;
        });
      });
    }

    creatingSessionRef.current = true;
    try {
      const newId = await createSession(projectId);
      setSessionId(newId);
      await refreshSessions();
      return newId;
    } finally {
      creatingSessionRef.current = false;
    }
  }, [sessionId, projectId, refreshSessions]);

  const loadSession = useCallback(
    async (id: string) => {
      if (isStreaming) return;
      try {
        const msgs = await getSessionMessages(id);
        const session = sessions.find((item) => item.id === id);
        setSessionId(id);
        setProjectId(session?.project_id ?? null);
        setMessages(
          msgs.map((m) => ({
            id: nextId(),
            role: m.role as "user" | "assistant",
            content: m.content,
            citations: m.citations,
            retrieval_id: m.retrieval_id,
            rag_status: m.rag_status,
          })),
        );
        setCurrentAgent("CMO Agent");
      } catch {
        // session might be stale
      }
    },
    [isStreaming, sessions],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreaming || !content.trim()) return;

      // Ensure session exists (lazy creation)
      const sid = sessionId ?? await ensureSession();
      if (!sid) return;

      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content: content.trim(),
      };
      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: "assistant",
        content: "",
        agent: currentAgent,
        tools: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      try {
        for await (const event of streamChat(sid, content.trim(), projectId, locale)) {
          handleEvent(event, assistantMsg.id);
        }
        // Refresh session list after completion (title may have changed)
        await refreshSessions();
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? {
                  ...m,
                  content:
                    m.content ||
                    `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
                }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [sessionId, isStreaming, currentAgent, projectId, locale, refreshSessions, ensureSession],
  );

  const handleEvent = useCallback(
    (event: ChatEvent, msgId: string) => {
      switch (event.type) {
        case "retrieval":
          setMessages(prev => prev.map(m => m.id === msgId ? { ...m, rag_status: event.status } : m));
          break;
        case "delta":
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId
                ? { ...m, content: m.content + (event.content ?? "") }
                : m,
            ),
          );
          break;
        case "agent":
          setCurrentAgent(event.name ?? "CMO Agent");
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId ? { ...m, agent: event.name } : m,
            ),
          );
          break;
        case "tool_call":
          if (isInternalHandoffTool(event.name)) break;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId
                ? {
                    ...m,
                    tools: [
                      ...(m.tools ?? []),
                      { name: formatToolLabel(event.name), done: false },
                    ],
                  }
                : m,
            ),
          );
          break;
        case "tool_done":
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== msgId) return m;
              const tools = [...(m.tools ?? [])];
              const last = tools.findLast((t: ToolStatus) => !t.done);
              if (last) last.done = true;
              return { ...m, tools };
            }),
          );
          break;
        case "handoff":
          break;
        case "handoff_done":
          break;
        case "done":
          if (event.agent_name) setCurrentAgent(event.agent_name);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId
                ? {
                    ...m,
                    agent: event.agent_name ?? m.agent,
                    content: event.final_output ?? m.content,
                    citations: event.citations,
                    retrieval_id: event.retrieval_id,
                    rag_status: event.rag_status,
                  }
                : m,
            ),
          );
          break;
        case "error":
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId
                ? { ...m, content: m.content || `Error: ${event.message}` }
                : m,
            ),
          );
          break;
      }
    },
    [],
  );

  const resetChat = useCallback(async (nextProjectId: number | null = projectId) => {
    if (isStreaming) return;
    setMessages([]);
    setCurrentAgent("CMO Agent");
    setProjectId(nextProjectId);
    setSessionId(null); // Defer session creation until first message
  }, [isStreaming, projectId]);

  const selectProject = useCallback(
    async (nextProjectId: number | null) => {
      if (nextProjectId === projectId) return;
      // Only reset if there are existing messages, otherwise just update projectId
      if (messages.length > 0) {
        await resetChat(nextProjectId);
      } else {
        setProjectId(nextProjectId);
        setSessionId(null); // Clear stale session
      }
    },
    [projectId, messages.length, resetChat],
  );

  const removeSession = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
        // If deleted session is the active one, reset
        if (id === sessionId) {
          await resetChat(projectId);
        }
      } catch {
        // ignore
      }
    },
    [projectId, sessionId, resetChat],
  );

  return {
    messages,
    isStreaming,
    currentAgent,
    projectId,
    sendMessage,
    resetChat,
    selectProject,
    sessionReady: ready,
    sessionId,
    sessions,
    loadSession,
    removeSession,
  };
}
