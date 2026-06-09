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

// ── Win Strategy Engine (flagship synthesis) ──────────────────────────────

export type StrategicBasis = "evidence" | "inference" | "assumption";

export interface StrategicPoint {
  statement: string;
  basis: StrategicBasis;
  sources?: string[];
}

export interface BlackHatPoint {
  competitor_move: string;
  impact: string;
  our_counter: string;
  basis: StrategicBasis;
  sources?: string[];
}

export interface CompetitorPosture {
  name: string;
  positioning: string;
  threat_level: "low" | "medium" | "high";
  our_response: string;
  basis: StrategicBasis;
  sources?: string[];
}

export interface CompetitiveAssessment {
  summary: string;
  competitors: CompetitorPosture[];
}

export interface CaptureAction {
  action: string;
  rationale: string;
  priority: "immediate" | "near_term" | "pre_rfp";
  owner?: string | null;
}

export interface WinConfidenceAssessment {
  level: "high" | "medium" | "low";
  score: number;
  rationale: string;
  key_drivers?: string[];
}

export interface WinStrategyOutput {
  executive_pursuit_recommendation: string;
  pursuit_recommendation: "pursue" | "pursue_with_conditions" | "no_bid";

  strengths?: StrategicPoint[];
  weaknesses?: StrategicPoint[];
  key_discriminators?: StrategicPoint[];
  black_hat_assessment?: BlackHatPoint[];
  likely_evaluator_concerns?: StrategicPoint[];
  win_themes?: StrategicPoint[];

  competitive_assessment: CompetitiveAssessment;
  critical_capture_actions?: CaptureAction[];
  win_confidence_assessment: WinConfidenceAssessment;

  inputs_used?: string[];
  inputs_missing?: string[];
  key_findings?: string[];
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

// ── Memory + Knowledge Graph ─────────────────────────────────────────────
export type MemoryBasis = "historical" | "current" | "inference";

export interface SourceOpportunity {
  id: Uuid;
  name: string;
}

export interface MemoryItem {
  label: string;
  basis: MemoryBasis;
  entity_type?: string | null;
  detail?: string | null;
  frequency: number;
  source_opportunities: SourceOpportunity[];
  attributes: Record<string, unknown>;
}

export interface SimilarOpportunity {
  opportunity_id: Uuid;
  name: string;
  agency?: string | null;
  score: number;
  reasons: string[];
  shared_entities: number;
}

export interface AgencyIntelligence {
  agency?: string | null;
  mission?: string | null;
  strategic_goals: string[];
  opportunities_count: number;
  recurring_risks: MemoryItem[];
  recurring_win_themes: MemoryItem[];
  known_competitors: MemoryItem[];
}

export interface PursuitMemory {
  opportunity_id: Uuid;
  opportunity_name: string;
  has_history: boolean;
  summary: string;
  similar_opportunities: SimilarOpportunity[];
  prior_risks: MemoryItem[];
  prior_discriminators: MemoryItem[];
  prior_win_themes: MemoryItem[];
  agency_intelligence?: AgencyIntelligence | null;
  inferences: string[];
  graph_stats: Record<string, number>;
}

export interface HistoricalInsightRepository {
  win_themes: MemoryItem[];
  discriminators: MemoryItem[];
  risks: MemoryItem[];
  competitors: MemoryItem[];
  graph_stats: Record<string, number>;
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

// ── Executive Briefings & Gate Reviews ───────────────────────────────────
export interface Confidence {
  level: "high" | "medium" | "low";
  score: number;
  rationale: string;
}

export interface HistoricalEvidence {
  similar_opportunities: string[];
  historical_win_themes: string[];
  historical_risks: string[];
  historical_discriminators: string[];
  agency_patterns: string[];
}

export interface OpportunitySnapshot {
  agency: string | null;
  program: string | null;
  estimated_value: string | null;
  contract_vehicle: string | null;
  due_date: string | null;
  incumbent: string | null;
  pursuit_status: string | null;
  win_confidence: number;
}

export interface CustomerIntelligence {
  strategic_priorities: string[];
  success_metrics: string[];
  stakeholder_concerns: string[];
  mission_drivers: string[];
}

export interface CompanyPosition {
  strengths: StrategicPoint[];
  gaps: StrategicPoint[];
  proof_points: StrategicPoint[];
  competitive_advantages: StrategicPoint[];
}

export interface BriefWinStrategy {
  recommended_discriminators: StrategicPoint[];
  key_themes: StrategicPoint[];
  evaluation_priorities: StrategicPoint[];
  critical_actions: CaptureAction[];
}

export interface BriefRisk {
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  mitigation?: string | null;
  basis: StrategicBasis;
  sources?: string[];
}

export interface BriefRisks {
  top_capture_risks: BriefRisk[];
  top_proposal_risks: BriefRisk[];
  top_delivery_risks: BriefRisk[];
}

export type ExecRecommendationType =
  | "pursue_aggressively"
  | "pursue_with_conditions"
  | "monitor"
  | "no_bid";

export interface ExecRecommendation {
  recommendation: ExecRecommendationType;
  confidence_level: "high" | "medium" | "low";
  confidence_score: number;
  rationale: string;
  required_conditions: string[];
}

export interface ExecutiveBriefOutput {
  headline: string;
  opportunity_snapshot: OpportunitySnapshot;
  customer_intelligence: CustomerIntelligence;
  company_position: CompanyPosition;
  win_strategy: BriefWinStrategy;
  risks: BriefRisks;
  executive_recommendation: ExecRecommendation;
  historical_evidence: HistoricalEvidence;
  inputs_used?: string[];
  inputs_missing?: string[];
  key_findings?: string[];
}

export interface ScoreBlock {
  score: number;
  rationale: string;
  basis: StrategicBasis;
  drivers: string[];
  sources?: string[];
}

export interface GateReviewOutput {
  headline: string;
  attractiveness_score: ScoreBlock;
  competitive_position_score: ScoreBlock;
  capability_alignment_score: ScoreBlock;
  risk_score: ScoreBlock;
  probability_of_win: Confidence;
  top_reasons_to_pursue: StrategicPoint[];
  top_reasons_not_to_pursue: StrategicPoint[];
  decision_recommendation: "pursue" | "pursue_with_conditions" | "no_bid";
  decision_summary: string;
  required_executive_actions: CaptureAction[];
  open_questions: string[];
  escalations: string[];
  historical_evidence: HistoricalEvidence;
  inputs_used?: string[];
  inputs_missing?: string[];
  key_findings?: string[];
}

export interface DecisionFactor {
  name: string;
  score: number;
  rationale: string;
  evidence: string[];
  confidence: "high" | "medium" | "low";
  basis: StrategicBasis;
}

export interface BidDecisionOutput {
  recommendation: "bid" | "conditional_bid" | "no_bid";
  executive_summary: string;
  confidence: Confidence;
  factors: DecisionFactor[];
  decision_drivers: string[];
  required_next_steps: CaptureAction[];
  historical_evidence: HistoricalEvidence;
  inputs_used?: string[];
  inputs_missing?: string[];
}
