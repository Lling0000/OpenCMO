export interface Project {
  id: number;
  account_id?: number;
  brand_name: string;
  url: string;
  category: string;
  latest?: LatestScans;
  latest_monitoring?: MonitoringSummary | null;
  latest_reports?: LatestReports;
  pending_approvals?: number;
}

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: "user" | "admin";
  status: "active" | "disabled";
  created_at: string;
  last_login_at: string | null;
}

export interface AuthAccount {
  id: number;
  name: string;
  plan: string;
  status: "active" | "disabled";
  trial_started_at: string;
  trial_ends_at: string;
  max_projects: number;
  daily_scan_limit: number;
  monthly_report_limit: number;
  created_at: string;
}

export interface UsageBucket {
  used: number;
  limit: number;
}

export interface AccountUsage {
  plan: string;
  status: string;
  trial_started_at: string;
  trial_ends_at: string;
  remaining_days: number;
  projects: UsageBucket;
  daily_scans: UsageBucket;
  monthly_reports: UsageBucket;
}

export interface AdminSummary {
  total_users: number;
  new_users_today: number;
  active_trial_accounts: number;
  expired_trial_accounts: number;
  total_projects: number;
  projects_created_today: number;
  scans_today: number;
  reports_this_month: number;
  failed_tasks_24h: number;
  high_usage_accounts: Array<{
    id: number;
    name: string;
    status: string;
    plan: string;
    usage_count: number;
  }>;
  recent_users: AuthUser[];
  recent_accounts: AuthAccount[];
  recent_failed_tasks: Array<{
    task_id: string;
    kind: string;
    project_id: number | null;
    status: string;
    error: { message?: string };
    created_at: string;
    updated_at: string;
  }>;
}

export interface SiteStats {
  total_visits: number;
  unique_visitors: number;
}

export interface LatestScans {
  seo: {
    scanned_at: string;
    score: number | null;
    performance_score?: number | null;
    health_score?: number | null;
  } | null;
  geo: { scanned_at: string; score: number } | null;
  community: { scanned_at: string; total_hits: number } | null;
  serp: SerpSnapshot[];
}

export interface SerpSnapshot {
  keyword: string;
  position: number | null;
  url_found?: string | null;
  provider?: string;
  error?: string | null;
  checked_at?: string;
}

export interface Monitor {
  id: number;
  project_id: number;
  brand_name: string;
  url: string;
  category: string;
  job_type: string;
  locale?: string;
  cron_expr: string;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface MonitorRun {
  id: number;
  task_id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  summary: string | null;
  created_at: string;
  completed_at: string | null;
  findings_count: number;
  recommendations_count: number;
}

export interface TaskRecord {
  task_id: string;
  task_kind?: "scan" | "report" | "graph_expansion" | "blog_generation";
  monitor_id?: number;
  project_id: number;
  job_type?: string;
  report_kind?: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled" | "canceled";
  created_at: string;
  completed_at: string | null;
  error: string | null;
  progress: TaskProgressEntry[];
  run_id?: number | null;
  summary?: string;
  findings_count?: number;
  recommendations_count?: number;
  runtime_state?: string;
  current_wave?: number;
  nodes_discovered?: number;
  nodes_explored?: number;
  style?: BlogStyle;
  skill_id?: MarketingSkillId;
  skill_name?: string;
  bilingual?: boolean;
  draft_ids?: number[];
  quality_scores?: BlogQualityScores;
}

export interface TaskArtifactStageCard {
  stage: string;
  status: "started" | "running" | "completed" | "failed" | "warning";
  summary: string;
  agent: string;
  event_count: number;
  kind?: "normal" | "fallback" | "degraded";
  hint?: string;
}

export interface TaskArtifactIssue {
  stage: string;
  status: "warning" | "failed";
  summary: string;
  resolution: string;
}

export interface TaskArtifactWatchout {
  stage: string;
  status: "started" | "running" | "completed" | "failed" | "warning";
  kind: "source_limit" | "fallback" | "coverage_gap" | "task_error";
  code: string;
  title: string;
  summary: string;
  resolution: string;
  blocking: boolean;
}

export interface TaskArtifactQuality {
  level: "reliable" | "partial" | "limited";
  headline: string;
  summary: string;
  blocking: boolean;
  fallbacks_used: string[];
  source_warnings: string[];
}

export interface TaskArtifactOpportunity {
  type: string;
  domain: string;
  title: string;
  summary: string;
  priority: "high" | "medium" | "low";
  score: number;
  recommended_action: string;
  evidence_refs: Finding["evidence_refs"];
}

export interface TaskArtifactCluster {
  name: string;
  brand_keyword_count: number;
  competitor_keyword_count: number;
  gap_keywords: string[];
  quick_win_keywords: string[];
  opportunity_score: number;
}

export interface TaskArtifacts {
  overview: {
    headline: string;
    findings_count: number;
    recommendations_count: number;
    focus_domains: string[];
  };
  quality: TaskArtifactQuality;
  stage_cards: TaskArtifactStageCard[];
  watchouts: TaskArtifactWatchout[];
  issues: TaskArtifactIssue[];
  brief: {
    top_findings: Finding[];
    top_recommendations: Recommendation[];
  };
  opportunities: {
    summary: Record<string, number>;
    top: TaskArtifactOpportunity[];
  };
  cluster_summary: {
    top_clusters: TaskArtifactCluster[];
    gap_keywords: string[];
  };
}

export type ApprovalStatus = "pending" | "approved" | "rejected" | "failed";

export interface ApprovalRecord {
  id: number;
  project_id: number;
  channel: string;
  approval_type: string;
  status: ApprovalStatus;
  title: string;
  target_label: string;
  target_url: string;
  agent_name: string;
  content: string;
  payload: Record<string, unknown>;
  preview: Record<string, unknown>;
  publish_result: Record<string, unknown> | null;
  decision_note: string;
  created_at: string;
  decided_at: string | null;
  source_insight_id?: number | null;
  pre_metrics_json?: string;
  post_metrics_json?: string;
}

export interface AnalysisProgress {
  role?: string;
  content?: string;
  round?: number;
  stage?: string;
  status?: "started" | "running" | "completed" | "failed" | "warning";
  agent?: string;
  summary?: string;
  detail?: string;
}

export interface TaskProgressEntry extends AnalysisProgress {
  phase?: string;
}

export interface Finding {
  domain: string;
  severity: "critical" | "warning" | "info";
  title: string;
  summary: string;
  confidence: number | null;
  evidence_refs: Array<{
    domain: string;
    source: string;
    key: string;
    value: string;
    url?: string | null;
  }>;
}

export interface Recommendation {
  domain: string;
  priority: "high" | "medium" | "low";
  owner_type: string;
  action_type: string;
  title: string;
  summary: string;
  rationale: string;
  confidence: number | null;
  evidence_refs: Array<{
    domain: string;
    source: string;
    key: string;
    value: string;
    url?: string | null;
  }>;
}

export interface MonitoringSummary {
  run_id: number;
  status: "pending" | "running" | "completed" | "failed";
  summary: string;
  created_at: string;
  completed_at: string | null;
  findings_count: number;
  recommendations_count: number;
}

export interface SeoScan {
  id: number;
  url: string;
  scanned_at: string;
  score_performance: number | null;
  score_lcp: number | null;
  score_cls: number | null;
  score_tbt: number | null;
  has_robots_txt: boolean | null;
  has_sitemap: boolean | null;
  has_schema_org: boolean | null;
  seo_health_score: number | null;
}

export interface GeoScan {
  id: number;
  scanned_at: string;
  geo_score: number;
  visibility_score: number | null;
  position_score: number | null;
  sentiment_score: number | null;
  platform_results_json: string;
}

export interface CommunityScan {
  id: number;
  scanned_at: string;
  total_hits: number;
  results_json: string;
}

export interface Discussion {
  id: number;
  platform: string;
  detail_id: string;
  title: string;
  url: string;
  first_seen_at: string;
  last_checked_at: string;
  raw_score: number | null;
  comments_count: number | null;
  engagement_score: number | null;
  intent_type?: "direct_mention" | "competitor_mention" | "opportunity" | null;
  match_reason?: string | null;
  matched_query?: string | null;
  matched_terms?: string[] | null;
  confidence?: number | null;
  source_kind?: "post" | "comment" | "external_search" | null;
}

export interface TrackedKeyword {
  id: number;
  keyword: string;
  created_at: string;
}

export interface ChartData {
  labels: string[];
  [key: string]: (number | null)[] | string[];
}

export interface SerpChartData {
  labels: string[];
  keywords: string[];
  positions: Record<string, (number | null)[]>;
}

export interface CommunityChartData {
  scan_labels: string[];
  scan_hits: number[];
  platform_labels: string[];
  platform_counts: number[];
}

export interface ChatEvent {
  type:
    | "retrieval"
    | "delta"
    | "agent"
    | "tool_call"
    | "tool_done"
    | "handoff"
    | "handoff_done"
    | "tool_search"
    | "tool_search_done"
    | "message_created"
    | "reasoning"
    | "done"
    | "error";
  content?: string;
  name?: string;
  target?: string;
  agent_name?: string;
  final_output?: string;
  review_applied?: boolean;
  review_profile?: string;
  review_weak_points?: string[];
  status?: string;
  citations?: import("../api/knowledge").KnowledgeCitation[];
  retrieval_id?: string;
  rag_status?: string;
  message?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  tools?: ToolStatus[];
  citations?: import("../api/knowledge").KnowledgeCitation[];
  retrieval_id?: string;
  rag_status?: string;
}

export interface ToolStatus {
  name: string;
  done: boolean;
}

export interface ProjectSummary {
  project: Project;
  is_paused: boolean;
  latest: LatestScans;
  previous: {
    seo?: {
      scanned_at: string;
      score: number | null;
      performance_score?: number | null;
      health_score?: number | null;
    };
    geo?: { scanned_at: string; score: number };
  } | null;
  latest_monitoring?: MonitoringSummary | null;
  latest_reports?: LatestReports;
  keyword_count?: number;
  competitor_count?: number;
  pending_approvals?: number;
  blog_drafts_count?: number;
}

export type BlogStyle = "launch" | "case_study" | "comparison" | "thought_leadership";
export type MarketingSkillId =
  | "content_strategy"
  | "copywriting"
  | "ai_seo"
  | "competitor_alternatives"
  | "programmatic_seo"
  | "directory_submissions";

export interface BlogQualityScores {
  seo: number;
  readability: number;
  keyword_coverage: number;
  structure: number;
  overall: number;
  framework?: number;
  [key: string]: number | string | undefined;
}

export interface BlogDraftMeta {
  marketing_skill?: {
    id: MarketingSkillId;
    name: string;
    description?: string;
    source_path?: string;
    source_url?: string;
    source_commit?: string;
    license?: string;
  };
  source_commit?: string;
  translated_from_draft_id?: number;
  [key: string]: unknown;
}

export interface BlogDraft {
  id: number;
  project_id: number;
  task_id: string;
  style: BlogStyle;
  language: string;
  status: string;
  title: string;
  content?: string;
  content_preview?: string;
  quality_scores: BlogQualityScores;
  paired_draft_id: number | null;
  approval_id: number | null;
  meta?: BlogDraftMeta;
  created_at: string;
  completed_at: string | null;
}

export type ReportKind = "strategic" | "periodic";
export type ReportAudience = "human" | "agent";
export type ReportGenerationStatus = "pending" | "running" | "completed" | "failed";

export interface ReportMeta {
  sample_count?: number;
  low_sample?: boolean;
  facts_summary?: string;
  model?: string;
  used_fallback?: boolean;
  llm_error?: string;
  pipeline_error?: string;
  window_days?: number;
  window_start?: string;
  window_end?: string;
  [key: string]: unknown;
}

export interface ReportRecord {
  id: number;
  project_id: number;
  kind: ReportKind;
  audience: ReportAudience;
  locale: string;
  version: number;
  is_latest: boolean;
  source_run_id: number | null;
  window_start: string | null;
  window_end: string | null;
  generation_status: ReportGenerationStatus;
  status: ReportGenerationStatus;
  content: string;
  content_html: string;
  meta: ReportMeta;
  created_at: string;
}

export interface ReportBundle {
  kind: ReportKind;
  locale?: string;
  human: ReportRecord;
  agent: ReportRecord;
}

export interface LatestReports {
  strategic: {
    human: ReportRecord | null;
    agent: ReportRecord | null;
  };
  periodic: {
    human: ReportRecord | null;
    agent: ReportRecord | null;
  };
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  project_id: number | null;
  project_name?: string | null;
}

export interface AISettings {
  api_key_set: boolean;
  api_key_masked: string;
  base_url: string;
  model: string;
  // Reddit
  reddit_configured: boolean;
  reddit_username: string;
  auto_publish: boolean;
  // Twitter
  twitter_configured: boolean;
  twitter_api_key_masked: string;
  // GEO
  anthropic_key_set: boolean;
  anthropic_key_masked: string;
  google_ai_key_set: boolean;
  google_ai_key_masked: string;
  moonshot_key_set: boolean;
  moonshot_key_masked: string;
  dashscope_key_set: boolean;
  dashscope_key_masked: string;
  deepseek_key_set: boolean;
  deepseek_key_masked: string;
  zhipu_key_set: boolean;
  zhipu_key_masked: string;
  doubao_key_set: boolean;
  doubao_key_masked: string;
  geo_chatgpt_enabled: boolean;
  // SEO
  pagespeed_key_set: boolean;
  pagespeed_key_masked: string;
  gsc_credentials_set: boolean;
  gsc_site_url: string;
  // Search (Tavily)
  tavily_key_set: boolean;
  tavily_key_masked: string;
  // GitHub
  github_token_set: boolean;
  github_token_masked: string;
  // SERP
  dataforseo_configured: boolean;
  dataforseo_login: string;
  // Email
  email_configured: boolean;
  smtp_host: string;
  smtp_port: string;
  smtp_user: string;
  report_email: string;
  // True when no per-account SMTP is set but the shared system SMTP can
  // still deliver mail (admin account / env). Used by the UI to surface a
  // hint that branded emails will go out under the system identity.
  system_smtp_active?: boolean;
}

// GitHub Leads
export interface GitHubLead {
  id: number;
  login: string;
  github_id: number | null;
  name: string;
  bio: string;
  company: string;
  location: string;
  email: string;
  blog: string;
  twitter_username: string;
  hireable: boolean | null;
  followers: number;
  following: number;
  public_repos: number;
  top_languages: string[];
  total_stars: number;
  top_repos: { name: string; description: string; language: string; stars: number }[];
  source: string;
  seed_username: string;
  outreach_score: number;
  outreach_status: string;
  outreach_channel: string;
  outreach_note: string;
  enriched: boolean;
  created_at: string;
  updated_at: string;
}

export interface GitHubDiscoveryRun {
  id: number;
  task_id: string;
  seed_username: string;
  source: string;
  max_hops: number;
  total_discovered: number;
  total_enriched: number;
  status: string;
  error: string;
  created_at: string;
  completed_at: string | null;
}

export interface GitHubLeadStats {
  total: number;
  enriched: number;
  has_email: number;
  has_twitter: number;
  avg_score: number;
}
