import { ArrowRight, BarChart3, Database, ShieldCheck, Tag } from "lucide-react";
import type { ProcurementAnalysis } from "../types";
import { formatMoney, humanize } from "../lib/format";

interface Props { analysis: ProcurementAnalysis; onEvidence: () => void; }

export function AnalysisCard({ analysis, onEvidence }: Props) {
  const { evidence, quote_comparison: quote, recommendation } = analysis;
  const tone = recommendation.assessment === "fair" || recommendation.assessment === "underpriced"
    ? "positive" : recommendation.assessment === "overpriced" ? "risk" : "caution";
  const percent = quote.percentage_difference_from_median;

  return (
    <section className="analysis-card" aria-label="Procurement analysis">
      <div className="analysis-heading">
        <div><span className="eyebrow">Procurement analysis</span><h2>{analysis.request.product}</h2></div>
        <span className={`assessment-pill ${tone}`}>{humanize(recommendation.assessment)}</span>
      </div>
      <div className="metric-grid">
        <div className="metric"><Tag size={17} /><span>Quoted unit price</span><strong>{formatMoney(quote.quoted_unit_price, quote.currency)}</strong></div>
        <div className="metric"><BarChart3 size={17} /><span>Market median</span><strong>{formatMoney(evidence.median_unit_price, evidence.currency || quote.currency)}</strong></div>
        <div className="metric"><ShieldCheck size={17} /><span>Confidence</span><strong>{humanize(recommendation.confidence)}</strong></div>
        <div className="metric"><Database size={17} /><span>Evidence</span><strong>{evidence.observation_count} observation{evidence.observation_count === 1 ? "" : "s"}</strong></div>
      </div>
      <div className="comparison-row">
        <div>
          <span>Quote position</span>
          <strong>{humanize(quote.position)}</strong>
          {percent !== null && <small>{Number(percent) > 0 ? "+" : ""}{percent}% from median</small>}
        </div>
        <div>
          <span>Recommended next move</span>
          <strong>{humanize(recommendation.recommended_action)}</strong>
          <small>{humanize(analysis.match_level)} product match · {humanize(analysis.market_data_status)} data</small>
        </div>
      </div>
      <div className="reason-list">
        {recommendation.reason_codes.slice(0, 4).map((reason) => <span key={reason}>{humanize(reason)}</span>)}
      </div>
      <button className="evidence-button" onClick={onEvidence}>Review market evidence <ArrowRight size={17} /></button>
    </section>
  );
}
