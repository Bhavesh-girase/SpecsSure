export interface Amendment {
  id: number;
  amendment_number: number;
  title?: string;
  published_at?: string;
  changed_clauses?: string;
  summary?: string;
  source_url?: string;
}

export interface VerificationEvidence {
  source_type: string;
  reference: string;
  verified_at?: string;
  trust_level: string;
  direct_url?: string;
}

export interface RecommendationExplanation {
  is_number: string;
  title: string;
  semantic_score: number;
  keyword_score: number;
  domain_score: number;
  graph_score: number;
  final_applicability_score: number;
  score_formula_note: string;
  auditable_trace: string[];
  natural_language_summary: string;
  source_evidence: VerificationEvidence[];
}

export interface RecommendedStandard {
  id: number;
  is_number: string;
  title: string;
  scope?: string;
  status: "current" | "superseded" | "withdrawn" | "under_review";
  relevance_score: number;
  relevance_reason: string;
  relationship_to_query: string;
  latest_edition?: string;
  amendments: Amendment[];
  superseded_by?: string;
  evidence: any[];
  explanation?: RecommendationExplanation;
}

export interface AlliedStandard {
  id: number;
  is_number: string;
  title: string;
  status: string;
  relationship_type: string;
  clause_reference?: string;
  parent_is_number: string;
  depth: number;
}

export interface CertificationInfo {
  is_number: string;
  standard_title?: string;
  is_mandatory: string; // 'yes' | 'no' | 'conditional'
  scheme?: string;
  qco_reference?: string;
  issuing_authority?: string;
  effective_from?: string;
  verification_state: string;
  note?: string;
}

export interface SpecGap {
  gap_type: "missing_parameter" | "ambiguous_term" | "outdated_reference" | "conflict" | "missing_normative_test";
  severity: "critical" | "warning" | "info";
  description: string;
  suggestion: string;
  affected_standard?: string;
  clause_reference?: string;
}

export interface SpecHealth {
  overall_score: number;
  completeness_score: number;
  currency_score: number;
  clarity_score: number;
  gaps: SpecGap[];
  summary: string;
}

export interface ExtractedRequirement {
  category: string;
  parameter: string;
  operator?: string;
  value: string;
  unit?: string;
  source_span?: string;
  confidence: number;
}

export interface GraphNode {
  id: string;
  db_id: number;
  is_number: string;
  label: string;
  title: string;
  status: string;
  division?: string;
  node_type: "primary" | "test_method" | "safety" | "installation" | "allied" | "superseded";
  depth: number;
  confidence?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  clause_reference?: string;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AnalysisResponse {
  analysis_id: string;
  input_language: string;
  detected_language: string;
  product_identity?: string;
  application_context?: string;
  extracted_requirements: ExtractedRequirement[];
  recommended_standards: RecommendedStandard[];
  allied_standards: AlliedStandard[];
  certification_info: CertificationInfo[];
  spec_health: SpecHealth;
  graph_data: GraphData;
  processing_time_seconds: number;
  disclaimer: string;
}

export interface QuickSearchResponse {
  query: string;
  results: RecommendedStandard[];
  total_found: number;
  processing_time_seconds: number;
}
