/**
 * Shared TypeScript types for the LLM Observatory dashboard.
 */

export interface Trace {
  id: string;
  name: string;
  session_id: string | null;
  start_time: string;
  end_time: string | null;
  status: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Span {
  id: string;
  trace_id: string;
  parent_id: string | null;
  name: string;
  span_type: string;
  start_time: string;
  end_time: string | null;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  tokens_input: number | null;
  tokens_output: number | null;
  cost_usd: number | null;
  metadata: Record<string, unknown> | null;
  attributes: Record<string, unknown> | null;
}

export interface Evaluation {
  id: string;
  trace_id: string;
  span_id: string | null;
  evaluator_type: string;
  score: number | null;
  criteria: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface SummaryData {
  total_traces: number;
  total_spans: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  error_count: number;
  error_rate: number;
  total_evaluations: number;
  avg_evaluation_score: number;
}

export interface TimelinePoint {
  timestamp: string;
  count: number;
  cost_usd: number;
}

export interface CostByModel {
  model: string;
  cost_usd: number;
  span_count: number;
}

export interface TraceListResponse {
  traces: Trace[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvaluationListResponse {
  evaluations: Evaluation[];
  total: number;
  limit: number;
  offset: number;
}

export interface WebSocketMessage {
  type: string;
  data: unknown;
}
