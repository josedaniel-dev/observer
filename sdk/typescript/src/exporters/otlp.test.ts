import { describe, it, expect, beforeEach, vi } from "vitest";
import { OTLPExporter } from "./otlp";
import type { Span } from "../tracer";

function makeSpan(overrides: Partial<Span> = {}): Span {
  return {
    id: "span-1",
    traceId: "trace-1",
    name: "test",
    spanType: "llm",
    startTime: Date.now(),
    status: "ok",
    metadata: {},
    attributes: {},
    ...overrides,
  };
}

describe("OTLPExporter", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({ ok: true, text: () => Promise.resolve("") });
    vi.stubGlobal("fetch", fetchMock);
  });

  it("sends spans to /v1/traces/batch", async () => {
    const exporter = new OTLPExporter({ endpoint: "http://localhost:8000" });
    const span = makeSpan();
    exporter.export([span]);
    await exporter.flush();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/v1/traces/batch");
    expect(opts.method).toBe("POST");
    const body = JSON.parse(opts.body);
    expect(body.spans).toHaveLength(1);
    expect(body.spans[0].id).toBe("span-1");
  });

  it("includes Authorization header when api_key is set", async () => {
    const exporter = new OTLPExporter({
      endpoint: "http://localhost:8000",
      apiKey: "test-key",
    });
    exporter.export([makeSpan()]);
    await exporter.flush();

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer test-key");
  });

  it("retries on failure", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: false, status: 500, text: () => Promise.resolve("err") })
      .mockResolvedValueOnce({ ok: true, text: () => Promise.resolve("") });

    const exporter = new OTLPExporter({ endpoint: "http://localhost:8000", maxRetries: 2 });
    // Push directly to buffer and call flush to avoid race with void this.flush()
    exporter["buffer"].push(...[makeSpan()].map(s => ({ id: s.id, trace_id: s.traceId, name: s.name, span_type: s.spanType, start_time: s.startTime, status: s.status, metadata: s.metadata, attributes: s.attributes })));
    await exporter.flush();

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("drops spans after max retries exhausted", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, text: () => Promise.resolve("err") });

    const exporter = new OTLPExporter({ endpoint: "http://localhost:8000", maxRetries: 2 });
    exporter["buffer"].push({ id: "s1", trace_id: "t1", name: "test", span_type: "llm", start_time: 0, status: "ok", metadata: {}, attributes: {} });
    await exporter.flush();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(exporter["buffer"]).toHaveLength(0);
  });

  it("does not flush when buffer is empty", async () => {
    const exporter = new OTLPExporter();
    await exporter.flush();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("converts span fields correctly", async () => {
    const exporter = new OTLPExporter();
    const span = makeSpan({
      id: "s1",
      traceId: "t1",
      parentId: "p1",
      name: "llm-call",
      spanType: "llm",
      startTime: 1000,
      endTime: 2000,
      status: "ok",
      input: { prompt: "hello" },
      output: { text: "hi" },
      tokens: { input: 100, output: 50, total: 150 },
      costUsd: 0.001,
      metadata: { key: "val" },
      attributes: { attr: "a" },
    });

    exporter.export([span]);
    await exporter.flush();

    const [, opts] = fetchMock.mock.calls[0];
    const sent = JSON.parse(opts.body).spans[0];
    expect(sent.id).toBe("s1");
    expect(sent.trace_id).toBe("t1");
    expect(sent.parent_id).toBe("p1");
    expect(sent.span_type).toBe("llm");
    expect(sent.tokens_input).toBe(100);
    expect(sent.tokens_output).toBe(50);
    expect(sent.cost_usd).toBe(0.001);
    expect(sent.input).toEqual({ prompt: "hello" });
    expect(sent.output).toEqual({ text: "hi" });
  });
});
