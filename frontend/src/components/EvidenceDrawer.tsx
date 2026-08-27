import { ExternalLink, Search, X } from "lucide-react";
import type { ProcurementAnalysis } from "../types";
import { formatMoney, humanize } from "../lib/format";

interface Props { analysis: ProcurementAnalysis | null; open: boolean; onClose: () => void; }

export function EvidenceDrawer({ analysis, open, onClose }: Props) {
  if (!analysis) return null;
  const items = analysis.evidence_observations;
  return (
    <>
      {open && <button className="drawer-scrim" aria-label="Close evidence" onClick={onClose} />}
      <aside className={`evidence-drawer ${open ? "drawer-open" : ""}`} aria-hidden={!open}>
        <div className="drawer-header">
          <div><span className="eyebrow">Traceable evidence</span><h2>Market observations</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close evidence"><X size={20} /></button>
        </div>
        <p className="drawer-intro">These are the listings used to position this quote. Reliability is a source-quality signal, not a guarantee.</p>
        {items.length === 0 ? (
          <div className="no-evidence"><Search size={25} /><strong>No comparable evidence yet</strong><p>The recommendation stays cautious until the collectors find suitable listings.</p></div>
        ) : (
          <div className="evidence-list">
            {items.map((item, index) => (
              <article className="evidence-item" key={`${item.source_name}-${item.source_url}-${index}`}>
                <div className="evidence-top"><span>{item.supplier_name}</span><strong>{formatMoney(item.unit_price, item.currency)}</strong></div>
                <h3>{item.product_name}</h3>
                <p>{item.cpu} · {item.ram_gb}GB RAM · {item.storage_capacity_gb}GB {item.storage_type.toUpperCase()}</p>
                <div className="evidence-meta"><span>{humanize(item.retrieval_method)} match · {item.match_score}%</span><span>{Math.round(Number(item.source_reliability) * 100)}% reliability</span></div>
                <p className="match-note">{item.match_explanation}</p>
                <div className="evidence-source"><span>{item.source_name} · {new Date(item.observation_date).toLocaleDateString("en-NG")}</span>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">View listing <ExternalLink size={13} /></a>}</div>
              </article>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}
