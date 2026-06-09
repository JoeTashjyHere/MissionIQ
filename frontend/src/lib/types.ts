export type Uuid = string;

export interface User {
  id: Uuid;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface WorkspaceMembership {
  workspace_id: Uuid;
  workspace_name: string;
  workspace_slug: string;
  role: "owner" | "admin" | "member" | "viewer";
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
  memberships: WorkspaceMembership[];
}

export interface Workspace {
  id: Uuid;
  name: string;
  slug: string;
  description: string | null;
  owner_user_id: Uuid;
  settings_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Opportunity {
  id: Uuid;
  workspace_id: Uuid;
  name: string;
  agency: string | null;
  sub_agency: string | null;
  contract_vehicle: string | null;
  solicitation_number: string | null;
  naics_code: string | null;
  psc_code: string | null;
  set_aside: string | null;
  due_date: string | null;
  posted_date: string | null;
  estimated_value_cents: number | null;
  capture_stage: string;
  incumbent: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityOverview {
  opportunity: Opportunity;
  document_count: number;
  ready_document_count: number;
  ai_output_count: number;
  risk_count: number;
  open_risk_count: number;
  compliance_total: number;
  compliance_complete: number;
  last_ai_generation_at: string | null;
}

export type DocumentStatus =
  | "uploaded"
  | "parsing"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

export interface DocumentRecord {
  id: Uuid;
  workspace_id: Uuid;
  opportunity_id: Uuid;
  name: string;
  doc_type: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  chunk_count: number | null;
  status: DocumentStatus;
  progress_pct: number;
  stage_started_at: string | null;
  error_message: string | null;
  uploaded_at: string | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModuleSpec {
  id: string;
  group: string;
  label: string;
  description: string;
  version: string;
  output_schema_summary: Record<string, string>;
  requires_customer_dna: boolean;
  consumes_company_profile: boolean;
}

// ── Module output shapes ──────────────────────────────────────────────────

export interface SupportingEvidenceItem {
  evidence_ref: string;
  finding: string;
}

export interface CustomerDnaProfile {
  mission: string;
  strategic_goals: string[];
  core_values: string[];
  success_metrics: string[];
  operational_challenges: string[];
  technology_priorities: string[];
  risk_priorities: string[];
  stakeholder_concerns: string[];

  executive_summary: string;
  key_findings?: string[];
  supporting_evidence?: SupportingEvidenceItem[];
  recommended_actions?: string[];
  confidence?: "high" | "medium" | "low" | "insufficient";
}

export interface ComplianceRow {
  requirement_id: string;
  requirement_text: string;
  source_document?: string | null;
  source_page?: number | null;
  source_section?: string | null;
  category?: string | null;
  response_owner?: string | null;
  proposed_status?: "open" | "in_progress" | "complete" | "n_a";
  notes?: string | null;
  why_requirement_exists: string;
  mission_alignment: string;
  customer_priority: "critical" | "high" | "medium" | "low";
}

export interface ComplianceMatrixOutput {
  executive_summary: string;
  key_findings: string[];
  supporting_evidence?: SupportingEvidenceItem[];
  recommended_actions: string[];
  rows: ComplianceRow[];
  coverage_gaps?: string[];
}

export interface EvaluationFactor {
  factor: string;
  subfactor?: string | null;
  importance:
    | "most_important"
    | "important"
    | "less_important"
    | "equal"
    | "unspecified";
  required_response_elements?: string[];
  source_section?: string | null;
  source_page?: number | null;
}

export interface EvaluationCriteriaOutput {
  executive_summary: string;
  key_findings: string[];
  supporting_evidence?: SupportingEvidenceItem[];
  recommended_actions: string[];
  factors: EvaluationFactor[];
  evaluation_intelligence: string;
  likely_decision_drivers: string[];
  potential_discriminators: string[];
  potential_weaknesses: string[];
  strategic_recommendations: string[];
}

export interface RiskItem {
  title: string;
  description: string;
  mission_impact: string;
  probability: "low" | "medium" | "high";
  severity: "low" | "medium" | "high" | "critical";
  mitigation: string;
  supporting_evidence?: string[];
  owner?: string | null;
}

export interface RiskRegisterOutput {
  executive_summary: string;
  key_findings: string[];
  supporting_evidence?: SupportingEvidenceItem[];
  recommended_actions: string[];
  capture_risks: RiskItem[];
  proposal_risks: RiskItem[];
  delivery_risks: RiskItem[];
  customer_risks: RiskItem[];
  top_risks?: string[];
}

export type DocumentCitation = {
  type: "document_chunk";
  id: Uuid;
  document_id: Uuid;
  document_name: string;
  page_start: number | null;
  page_end: number | null;
  section_path: string | null;
  snippet: string;
};

export type MarketIntelCitation = {
  type: "market_intel_record";
  id: Uuid;
  source_id: string;
  external_id: string;
  source_url: string | null;
  title: string;
};

export type Citation = DocumentCitation | MarketIntelCitation;

export interface AIOutput {
  id: Uuid;
  workspace_id: Uuid;
  opportunity_id: Uuid | null;
  module_id: string;
  module_version: string;
  status: "ok" | "insufficient_context" | "error";
  model_provider: string;
  model_name: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  output_json: Record<string, unknown>;
  citations: Citation[];
  generated_at: string;
}

export interface MarketIntelRecord {
  id: Uuid;
  source_id: string;
  workspace_id: Uuid | null;
  external_id: string;
  source_url: string | null;
  title: string;
  agency: string | null;
  sub_agency: string | null;
  notice_type: string | null;
  naics_code: string | null;
  psc_code: string | null;
  set_aside: string | null;
  estimated_value_cents: number | null;
  posted_date: string | null;
  due_date: string | null;
  incumbent: string | null;
  summary: string | null;
  fetched_at: string | null;
}

export interface CompanyProfile {
  id: Uuid;
  workspace_id: Uuid;
  legal_name: string | null;
  duns: string | null;
  uei: string | null;
  cage_code: string | null;
  primary_naics: string | null;
  size_standard: string | null;
  certifications: string[] | null;
  overview: string | null;
  differentiators: string | null;
  past_performance_summary: string | null;
  contract_vehicles: string[] | null;
  technology_partners: string[] | null;
  case_studies: string | null;
  key_personnel: string | null;
  geographic_footprint: string | null;
  security_posture: string | null;
  delivery_model: string | null;
  pricing_posture: string | null;
}

// ── Seller-side intelligence: Company DNA + Capability Match ───────────────

export interface CompanyDnaProfile {
  company_summary: string;
  core_capabilities: string[];
  past_performance: string[];
  contract_vehicles?: string[];
  certifications?: string[];
  technology_partners?: string[];
  differentiators: string[];
  case_studies?: string[];
  key_personnel?: string[];
  geographic_footprint?: string | null;
  security_posture?: string | null;
  delivery_model?: string | null;
  pricing_posture?: string | null;

  executive_summary: string;
  key_findings?: string[];
  recommended_actions?: string[];

  confidence?: "high" | "medium" | "low" | "insufficient";
  profile_completeness?: "complete" | "partial" | "empty";
}

export interface FitArea {
  area: string;
  rationale: string;
  evidence_refs?: string[];
  confidence?: "high" | "medium" | "low";
}

export interface TeamingRecommendation {
  partner_profile: string;
  fills_gap: string;
  rationale: string;
}

export interface CompanyGapRisk {
  title: string;
  description: string;
  severity?: "low" | "medium" | "high" | "critical";
  mitigation: string;
}

export interface CapabilityMatchOutput {
  executive_summary: string;
  win_assessment: string;
  fit_score?: "strong" | "moderate" | "marginal" | "weak";
  seller_data_complete?: boolean;

  strong_fit_areas?: FitArea[];
  weak_fit_areas?: FitArea[];
  missing_capabilities?: string[];
  required_proof_points?: string[];
  recommended_teaming_partners?: TeamingRecommendation[];
  suggested_discriminators?: string[];
  reusable_win_themes?: string[];
  capture_questions?: string[];
  proposal_risks?: CompanyGapRisk[];

  key_findings?: string[];
  recommended_actions?: string[];
}

export interface Capability {
  id: Uuid;
  workspace_id: Uuid;
  name: string;
  category: string | null;
  maturity: string | null;
  description: string | null;
  keywords: string[] | null;
  evidence_links: string[] | null;
}

export interface ChatThread {
  id: Uuid;
  workspace_id: Uuid;
  opportunity_id: Uuid | null;
  title: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: Uuid;
  thread_id: Uuid;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  status: "ok" | "insufficient_context" | "error";
  model_provider: string | null;
  model_name: string | null;
  created_at: string;
}
