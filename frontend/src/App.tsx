import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Bot, Menu, Sparkles, UserRound } from "lucide-react";
import { ApiError, sendChatMessage } from "./api";
import { Sidebar } from "./components/Sidebar";
import { Composer } from "./components/Composer";
import { AnalysisCard } from "./components/AnalysisCard";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { AssistantMarkdown } from "./components/AssistantMarkdown";
import type { ChatMessage, Conversation } from "./types";

const STORAGE_KEY = "procura-ai-conversations-v1";
const EXAMPLES = [
  "Analyze 50 new Dell Latitude 5440 laptops, Core i5, 16GB RAM, 512GB SSD, quoted at ₦850,000 each.",
  "What information do you need to assess a laptop quote?",
  "How do you decide whether market evidence is reliable?",
];

function createConversation(): Conversation {
  return {
    localId: crypto.randomUUID(), backendId: null, analysisId: null,
    title: "New analysis", updatedAt: new Date().toISOString(), messages: [], analysis: null,
  };
}

function loadConversations(): Conversation[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") as Conversation[];
    return Array.isArray(parsed) && parsed.length ? parsed : [createConversation()];
  } catch { return [createConversation()]; }
}

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState(() => conversations[0].localId);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [evidenceAnalysis, setEvidenceAnalysis] = useState<Conversation["analysis"]>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const active = useMemo(() => conversations.find((item) => item.localId === activeId) || conversations[0], [conversations, activeId]);
  const suggestions = useMemo(() => {
    if (active.messages.length === 0) return [];
    if (active.analysis) {
      return [
        "Why is the confidence level this low?",
        "Explain the market evidence used",
        "What should I verify before deciding?",
      ];
    }
    const lastReply = [...active.messages].reverse().find((message) => message.role === "assistant")?.content.toLowerCase() || "";
    if (lastReply.includes("still need") || lastReply.includes("missing")) {
      return [
        "Tell me exactly which details are missing",
        "Can you analyze it with the information available?",
        "Show me an example of a complete request",
      ];
    }
    return [
      "Analyze a business laptop quote",
      "What details do you need from me?",
      "How do you assess source reliability?",
    ];
  }, [active]);

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations)); }, [conversations]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [active.messages.length, loading]);

  const patchActive = (patcher: (conversation: Conversation) => Conversation) => {
    setConversations((current) => current.map((item) => item.localId === activeId ? patcher(item) : item));
  };

  const newConversation = () => {
    const next = createConversation();
    setConversations((current) => [next, ...current]);
    setActiveId(next.localId); setDraft(""); setError(null); setEvidenceAnalysis(null); setSidebarOpen(false);
  };

  const submit = async (prefilled?: string) => {
    const content = (prefilled ?? draft).trim();
    if (!content || loading) return;
    const now = new Date().toISOString();
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content, createdAt: now, status: "sending" };
    const currentBackendId = active.backendId;
    setDraft(""); setError(null); setLoading(true);
    patchActive((conversation) => ({
      ...conversation,
      title: conversation.messages.length === 0 ? content.slice(0, 48) + (content.length > 48 ? "…" : "") : conversation.title,
      updatedAt: now,
      messages: [...conversation.messages, userMessage],
    }));
    try {
      const result = await sendChatMessage(content, currentBackendId);
      patchActive((conversation) => ({
        ...conversation,
        backendId: result.conversation.id,
        analysisId: result.analysis_id,
        analysis: result.analysis || conversation.analysis,
        updatedAt: result.conversation.updated_at,
        messages: [
          ...conversation.messages.map((message) => message.id === userMessage.id ? { ...message, status: "sent" as const } : message),
          {
            id: result.assistant_message.id,
            role: "assistant",
            content: result.assistant_message.content,
            createdAt: result.assistant_message.created_at,
            status: "sent",
            ...(result.analysis ? { analysis: result.analysis } : {}),
          },
        ],
      }));
    } catch (caught) {
      const message = caught instanceof ApiError
        ? caught.status === 429 ? `You have sent requests too quickly. Try again${caught.retryAfter ? ` in ${caught.retryAfter} seconds` : " shortly"}.`
          : caught.status >= 500 ? "The analysis service is temporarily unavailable. Your message is saved—please try again."
          : caught.message
        : "Could not reach the backend. Confirm FastAPI is running on port 8000.";
      setError(message);
      patchActive((conversation) => ({ ...conversation, messages: conversation.messages.map((item) => item.id === userMessage.id ? { ...item, status: "failed" } : item) }));
    } finally { setLoading(false); }
  };

  return (
    <div className="app-shell">
      <Sidebar conversations={conversations} activeId={activeId} open={sidebarOpen} onClose={() => setSidebarOpen(false)} onNew={newConversation} onSelect={setActiveId} />
      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open conversations"><Menu size={21} /></button>
          <div><strong>{active.title}</strong><span><i /> Evidence-backed assistant</span></div>
          <div className="topbar-badge"><Sparkles size={14} /> Procurement intelligence</div>
        </header>
        <div className="chat-scroll">
          <div className="chat-content">
            {active.messages.length === 0 ? (
              <section className="welcome">
                <div className="welcome-mark"><Sparkles size={25} /></div>
                <span className="eyebrow">Your procurement copilot</span>
                <h1>Make sense of a laptop quote.</h1>
                <p>Describe what you need and the price you received. I’ll normalize the product, review current market evidence, and explain the recommendation.</p>
                <div className="prompt-grid">
                  {EXAMPLES.map((example, index) => <button key={example} onClick={() => void submit(example)}><span>0{index + 1}</span>{example}</button>)}
                </div>
              </section>
            ) : (
              <div className="message-list">
                {active.messages.map((message) => (
                  <Fragment key={message.id}>
                    <article className={`message ${message.role}`}>
                      <div className="avatar">{message.role === "assistant" ? <Bot size={18} /> : <UserRound size={18} />}</div>
                      <div className="message-body">
                        <span>{message.role === "assistant" ? "Procura AI" : "You"}</span>
                        {message.role === "assistant" ? <AssistantMarkdown content={message.content} /> : <p>{message.content}</p>}
                        {message.status === "failed" && <small className="failed-label">Not delivered</small>}
                      </div>
                    </article>
                    {message.analysis && <AnalysisCard analysis={message.analysis} onEvidence={() => setEvidenceAnalysis(message.analysis!)} />}
                  </Fragment>
                ))}
                {loading && <article className="message assistant"><div className="avatar"><Bot size={18} /></div><div className="message-body"><span>Procura AI</span><div className="thinking"><i /><i /><i /><small>Reviewing your request and market evidence</small></div></div></article>}
              </div>
            )}
            {error && <div className="error-banner"><AlertCircle size={18} /><span>{error}</span><button onClick={() => setError(null)}>Dismiss</button></div>}
            <div ref={endRef} />
          </div>
        </div>
        <Composer value={draft} loading={loading} suggestions={suggestions} onChange={setDraft} onSubmit={() => void submit()} />
      </main>
      <EvidenceDrawer analysis={evidenceAnalysis} open={evidenceAnalysis !== null} onClose={() => setEvidenceAnalysis(null)} />
    </div>
  );
}
