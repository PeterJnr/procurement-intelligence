import { MessageSquareText, Plus, Sparkles, X } from "lucide-react";
import type { Conversation } from "../types";
import { relativeDate } from "../lib/format";

interface Props {
  conversations: Conversation[];
  activeId: string;
  open: boolean;
  onClose: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
}

export function Sidebar({ conversations, activeId, open, onClose, onNew, onSelect }: Props) {
  return (
    <>
      {open && <button aria-label="Close conversations" className="sidebar-scrim" onClick={onClose} />}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div><strong>Procura AI</strong><span>Market intelligence</span></div>
          <button className="icon-button mobile-only" aria-label="Close menu" onClick={onClose}><X size={19} /></button>
        </div>
        <button className="new-chat" onClick={onNew}><Plus size={18} /> New analysis</button>
        <div className="history-label">Recent conversations</div>
        <nav className="conversation-list" aria-label="Conversation history">
          {conversations.map((conversation) => (
            <button
              key={conversation.localId}
              className={`conversation-item ${activeId === conversation.localId ? "active" : ""}`}
              onClick={() => { onSelect(conversation.localId); onClose(); }}
            >
              <MessageSquareText size={16} />
              <span className="conversation-copy"><strong>{conversation.title}</strong><small>{relativeDate(conversation.updatedAt)}</small></span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer"><span className="status-dot" /> Procurement API connected</div>
      </aside>
    </>
  );
}
