export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  status?: "sending" | "sent" | "failed";
  analysis?: ProcurementAnalysis;
}

export interface EvidenceObservation {
  product_name: string;
  cpu: string;
  ram_gb: number;
  storage_capacity_gb: number;
  storage_type: string;
  condition: string;
  supplier_name: string;
  quantity: number;
  unit_price: string;
  currency: string;
  source_name: string;
  source_url: string | null;
  observation_date: string;
  source_reliability: string;
  match_score: number;
  matched_fields: string[];
  different_fields: string[];
  match_explanation: string;
  retrieval_method: "deterministic" | "semantic";
  semantic_similarity_score: number | null;
}

export interface ProcurementAnalysis {
  analysis_id: string | null;
  request: {
    product: string;
    specifications: { cpu?: string | null; ram?: string | null; storage?: string | null };
    condition: string;
    quantity: number;
    quoted_price: string;
    currency: string;
  };
  normalized_product: {
    category: string;
    product_name: string;
    cpu: string | null;
    ram_gb: number | null;
    storage_capacity_gb: number | null;
    storage_type: string | null;
    condition: string;
    missing_fields: string[];
    analysis_readiness: string;
    matching_key: string;
  };
  market_data_status: "fresh" | "stale" | "missing";
  match_level: "exact" | "strong" | "broad" | "semantic" | "none";
  evidence: {
    evidence_status: "no_data" | "limited" | "sufficient";
    observation_count: number;
    currency: string | null;
    median_unit_price: string | null;
    lowest_unit_price: string | null;
    highest_unit_price: string | null;
    average_source_reliability: string | null;
  };
  evidence_observations: EvidenceObservation[];
  quote_comparison: {
    quoted_unit_price: string;
    currency: string;
    position: string;
    difference_from_median: string | null;
    percentage_difference_from_median: string | null;
  };
  recommendation: {
    assessment: "fair" | "overpriced" | "underpriced" | "undetermined";
    recommended_action: string;
    confidence: "low" | "medium" | "high";
    reason_codes: string[];
  };
  analysis_explanation: string;
  analysis_explanation_status: "generated" | "fallback" | "disabled";
}

export interface Conversation {
  localId: string;
  backendId: string | null;
  analysisId: string | null;
  title: string;
  updatedAt: string;
  messages: ChatMessage[];
  analysis: ProcurementAnalysis | null;
}

export interface ChatApiResponse {
  conversation: { id: string; analysis_id: string | null; title: string | null; updated_at: string };
  assistant_message: { id: string; content: string; created_at: string };
  intent: string;
  analysis_id: string | null;
  analysis: ProcurementAnalysis | null;
}
