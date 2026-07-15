import { describe, it, expect, beforeEach } from "vitest";
import {
  Tracer,
  Span,
  trace,
  asyncTrace,
  getTracer,
  setTracer,
  getCurrentSpan,
} from "../src/index";

describe("Tracer", () => {
  let tracer: Tracer;

  beforeEach(() => {
    tracer = new Tracer({ serviceName: "test" });
  });

  it("creates a trace with correct properties", () => {
    const span = tracer.startTrace("test-trace");
    expect(span.name).toBe("test-trace");
    expect(span.spanType).toBe("trace");
    expect(span.id).toBeDefined();
    expect(span.traceId).toBeDefined();
    expect(span.status).toBe("unset");
  });

  it("creates a span with parent", () => {
    const root = tracer.startTrace("root");
    const child = tracer.startSpan("child", { parent: root });
    expect(child.traceId).toBe(root.traceId);
    expect(child.parentId).toBe(root.id);
  });

  it("exports spans in backend format", () => {
    const span = tracer.startTrace("test");
    span.endTime = span.startTime + 1;
    span.tokens = { input: 100, output: 50, total: 150 };

    const exported = tracer.export();
    expect(exported).toHaveLength(1);
    expect(exported[0].trace_id).toBe(span.traceId);
    expect(exported[0].tokens_input).toBe(100);
    expect(exported[0].tokens_output).toBe(50);
    // Should NOT have nested tokens object
    expect(exported[0].tokens).toBeUndefined();
  });

  it("clears spans", () => {
    tracer.startTrace("test");
    expect(tracer.export()).toHaveLength(1);
    tracer.clear();
    expect(tracer.export()).toHaveLength(0);
  });
});

describe("trace function", () => {
  it("wraps sync function", () => {
    const result = trace("test", (span) => {
      span.attributes["key"] = "value";
      return 42;
    });
    expect(result).toBe(42);
  });

  it("captures errors", () => {
    expect(() => {
      trace("test", () => {
        throw new Error("test error");
      });
    }).toThrow("test error");
  });

  it("sets status ok on success", () => {
    let capturedSpan: Span | undefined;
    trace("test", (span) => {
      capturedSpan = span;
      return 42;
    });
    expect(capturedSpan!.status).toBe("ok");
    expect(capturedSpan!.endTime).toBeDefined();
  });
});

describe("asyncTrace function", () => {
  it("wraps async function", async () => {
    const result = await asyncTrace("test", async (span) => {
      span.attributes["key"] = "value";
      return 42;
    });
    expect(result).toBe(42);
  });

  it("captures async errors", async () => {
    await expect(
      asyncTrace("test", async () => {
        throw new Error("async error");
      })
    ).rejects.toThrow("async error");
  });

  it("propagates context via AsyncLocalStorage", async () => {
    let innerSpan: Span | undefined;
    await asyncTrace("outer", async (outerSpan) => {
      expect(getCurrentSpan()?.id).toBe(outerSpan.id);
      await asyncTrace("inner", async (innerSpanArg) => {
        innerSpan = innerSpanArg;
        expect(innerSpanArg.parentId).toBe(outerSpan.id);
        expect(innerSpanArg.traceId).toBe(outerSpan.traceId);
      });
    });
    expect(innerSpan).toBeDefined();
  });
});

describe("Global tracer", () => {
  it("creates default tracer", () => {
    const t = getTracer();
    expect(t).toBeInstanceOf(Tracer);
  });

  it("allows setting custom tracer", () => {
    const custom = new Tracer({ serviceName: "custom" });
    setTracer(custom);
    expect(getTracer()).toBe(custom);
    // Reset
    setTracer(new Tracer());
  });
});
