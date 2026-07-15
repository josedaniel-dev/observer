/**
 * OTLP HTTP exporter for sending traces to observatory backend.
 */

import type { Span } from "../tracer";

export interface OTLPExporterOptions {
  endpoint?: string;
  apiKey?: string;
  timeout?: number;
  maxRetries?: number;
}

function spanToDict(span: Span): Record<string, unknown> {
  return {
    id: span.id,
    trace_id: span.traceId,
    parent_id: span.parentId ?? null,
    name: span.name,
    span_type: span.spanType,
    start_time: span.startTime,
    end_time: span.endTime ?? null,
    status: span.status,
    input: span.input ?? null,
    output: span.output ?? null,
    tokens_input: span.tokens?.input ?? null,
    tokens_output: span.tokens?.output ?? null,
    cost_usd: span.costUsd ?? null,
    metadata: span.metadata,
    attributes: span.attributes,
  };
}

export class OTLPExporter {
  private endpoint: string;
  private apiKey?: string;
  private timeout: number;
  private maxRetries: number;
  private buffer: Record<string, unknown>[] = [];

  constructor(options: OTLPExporterOptions = {}) {
    this.endpoint = (options.endpoint || "http://localhost:8000").replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 10000;
    this.maxRetries = options.maxRetries ?? 3;
  }

  export(spans: Span[]): void {
    const dicts = spans.map(spanToDict);
    this.buffer.push(...dicts);
    this.flush();
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0) return;

    const spans = this.buffer.splice(0);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(`${this.endpoint}/v1/traces/batch`, {
          method: "POST",
          headers,
          body: JSON.stringify({ spans }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const text = await response.text().catch(() => "");
          console.warn(
            `OTLP export failed (attempt ${attempt + 1}/${this.maxRetries}): ` +
            `HTTP ${response.status} - ${text}`
          );
          if (attempt === this.maxRetries - 1) {
            console.error(`OTLP export failed after ${this.maxRetries} attempts, dropping ${spans.length} spans`);
          }
          continue;
        }

        return;
      } catch (error) {
        console.warn(
          `OTLP export failed (attempt ${attempt + 1}/${this.maxRetries}): ${error}`
        );
        if (attempt === this.maxRetries - 1) {
          console.error(`OTLP export failed after ${this.maxRetries} attempts, dropping ${spans.length} spans`);
        }
      }
    }
  }
}
