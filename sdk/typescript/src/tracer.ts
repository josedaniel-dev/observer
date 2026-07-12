/**
 * Core tracing engine for LLM Observatory
 */

import { randomUUID } from "crypto";

export type SpanStatus = "ok" | "error" | "unset";

export interface TokenUsage {
  input: number;
  output: number;
  total: number;
}

export interface Span {
  id: string;
  traceId: string;
  parentId?: string;
  name: string;
  spanType: string;
  startTime: number;
  endTime?: number;
  status: SpanStatus;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  tokens?: TokenUsage;
  costUsd?: number;
  metadata: Record<string, unknown>;
  attributes: Record<string, unknown>;
}

export class Tracer {
  private spans: Span[] = [];
  private serviceName: string;
  private endpoint?: string;
  private apiKey?: string;

  constructor(options: {
    serviceName?: string;
    endpoint?: string;
    apiKey?: string;
  } = {}) {
    this.serviceName = options.serviceName || "llm-observatory";
    this.endpoint = options.endpoint;
    this.apiKey = options.apiKey;
  }

  startTrace(name: string, attributes: Record<string, unknown> = {}): Span {
    const span: Span = {
      id: randomUUID(),
      traceId: randomUUID(),
      name,
      spanType: "trace",
      startTime: Date.now() / 1000,
      status: "unset",
      metadata: {},
      attributes,
    };
    this.spans.push(span);
    return span;
  }

  startSpan(
    name: string,
    options: {
      spanType?: string;
      parent?: Span;
      attributes?: Record<string, unknown>;
    } = {}
  ): Span {
    const span: Span = {
      id: randomUUID(),
      traceId: options.parent?.traceId || randomUUID(),
      parentId: options.parent?.id,
      name,
      spanType: options.spanType || "generic",
      startTime: Date.now() / 1000,
      status: "unset",
      metadata: {},
      attributes: options.attributes || {},
    };
    this.spans.push(span);
    return span;
  }

  export(): Record<string, unknown>[] {
    return this.spans.map((span) => ({
      id: span.id,
      trace_id: span.traceId,
      parent_id: span.parentId,
      name: span.name,
      span_type: span.spanType,
      start_time: span.startTime,
      end_time: span.endTime,
      status: span.status,
      input: span.input,
      output: span.output,
      tokens: span.tokens || null,
      cost_usd: span.costUsd,
      metadata: span.metadata,
      attributes: span.attributes,
    }));
  }

  clear(): void {
    this.spans = [];
  }
}

// Global tracer instance
let globalTracer: Tracer | null = null;

export function getTracer(): Tracer {
  if (!globalTracer) {
    globalTracer = new Tracer();
  }
  return globalTracer;
}

export function setTracer(tracer: Tracer): void {
  globalTracer = tracer;
}

export function trace<T>(
  name: string,
  fn: (span: Span) => T,
  options: { spanType?: string } = {}
): T {
  const tracer = getTracer();
  const span = tracer.startSpan(name, { spanType: options.spanType });

  try {
    const result = fn(span);
    span.status = "ok";
    return result;
  } catch (error) {
    span.status = "error";
    span.attributes["error.message"] =
      error instanceof Error ? error.message : String(error);
    throw error;
  } finally {
    span.endTime = Date.now() / 1000;
  }
}
