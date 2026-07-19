/**
 * Core tracing engine for LLM Observatory
 */

import { randomUUID } from "crypto";
import { AsyncLocalStorage } from "async_hooks";

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

export interface SpanExporter {
  export(spans: Span[]): void;
  flush?(): Promise<void>;
}

// Context propagation using AsyncLocalStorage
const spanStorage = new AsyncLocalStorage<Span>();

export function getCurrentSpan(): Span | undefined {
  return spanStorage.getStore();
}

export class Tracer {
  private spans: Span[] = [];
  private exporters: SpanExporter[] = [];
  private serviceName: string;

  constructor(options: { serviceName?: string } = {}) {
    this.serviceName = options.serviceName || "llm-observatory";
  }

  addExporter(exporter: SpanExporter): void {
    this.exporters.push(exporter);
  }

  removeExporter(exporter: SpanExporter): void {
    const idx = this.exporters.indexOf(exporter);
    if (idx >= 0) this.exporters.splice(idx, 1);
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
    const parentSpan = options.parent || getCurrentSpan();
    const span: Span = {
      id: randomUUID(),
      traceId: parentSpan?.traceId || randomUUID(),
      parentId: parentSpan?.id,
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

  /** Called when a span ends - auto-exports to all registered exporters. */
  private onSpanEnd(span: Span): void {
    if (this.exporters.length > 0) {
      for (const exporter of this.exporters) {
        try {
          exporter.export([span]);
        } catch {
          // Don't let exporter errors break tracing
        }
      }
    }
  }

  /** Mark a span as ended and trigger export. */
  endSpan(span: Span): void {
    if (!span.endTime) {
      span.endTime = Date.now() / 1000;
    }
    this.onSpanEnd(span);
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
      tokens_input: span.tokens?.input ?? null,
      tokens_output: span.tokens?.output ?? null,
      cost_usd: span.costUsd,
      metadata: span.metadata,
      attributes: span.attributes,
    }));
  }

  async flush(): Promise<void> {
    for (const exporter of this.exporters) {
      if (exporter.flush) {
        await exporter.flush();
      }
    }
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

/**
 * Synchronous trace decorator.
 * For async functions, use asyncTrace instead.
 */
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
    tracer.endSpan(span);
  }
}

/**
 * Async trace decorator with context propagation.
 */
export async function asyncTrace<T>(
  name: string,
  fn: (span: Span) => Promise<T>,
  options: { spanType?: string } = {}
): Promise<T> {
  const tracer = getTracer();
  const span = tracer.startSpan(name, { spanType: options.spanType });

  try {
    const result = await spanStorage.run(span, () => fn(span));
    span.status = "ok";
    return result;
  } catch (error) {
    span.status = "error";
    span.attributes["error.message"] =
      error instanceof Error ? error.message : String(error);
    throw error;
  } finally {
    tracer.endSpan(span);
  }
}
