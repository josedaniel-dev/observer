/**
 * OpenAI auto-instrumentation
 */

import { getTracer, type Span } from "../tracer";

let originalSyncCreate: ((...args: unknown[]) => unknown) | null = null;
let originalAsyncCreate: ((...args: unknown[]) => unknown) | null = null;

// Pricing table (per 1M tokens)
const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  "gpt-4o": { input: 2.5, output: 10.0 },
  "gpt-4o-mini": { input: 0.15, output: 0.6 },
  "gpt-4-turbo": { input: 10.0, output: 30.0 },
  "gpt-4": { input: 30.0, output: 60.0 },
  "gpt-3.5-turbo": { input: 0.5, output: 1.5 },
  "o1": { input: 15.0, output: 60.0 },
  "o1-mini": { input: 3.0, output: 12.0 },
  "o3": { input: 10.0, output: 40.0 },
  "o3-mini": { input: 1.1, output: 4.4 },
};

function calculateCost(
  model: string,
  inputTokens: number,
  outputTokens: number
): number | null {
  const pricing = MODEL_PRICING[model];
  if (!pricing) return null;
  return (
    (inputTokens / 1_000_000) * pricing.input +
    (outputTokens / 1_000_000) * pricing.output
  );
}

function buildSpan(
  model: string,
  messages: unknown[]
): Span {
  const tracer = getTracer();
  const span = tracer.startSpan("openai.chat.completions.create", {
    spanType: "llm",
    attributes: {
      "gen_ai.system": "openai",
      "gen_ai.request.model": model,
      model,
      messages,
    },
  });
  span.input = { model, messages };
  return span;
}

function finishSpan(span: Span, result: unknown, model: string): void {
  if (result && typeof result === "object") {
    const obj = result as Record<string, unknown>;

    // Extract token usage
    const usage = obj.usage as Record<string, unknown> | undefined;
    if (usage) {
      const inputTokens = (usage.prompt_tokens as number) || 0;
      const outputTokens = (usage.completion_tokens as number) || 0;
      span.tokens = {
        input: inputTokens,
        output: outputTokens,
        total: (usage.total_tokens as number) || 0,
      };

      // Calculate cost
      const cost = calculateCost(model, inputTokens, outputTokens);
      if (cost !== null) {
        span.costUsd = cost;
      }
    }

    // Extract output
    const choices = obj.choices as Array<Record<string, unknown>> | undefined;
    if (choices && choices.length > 0) {
      const choice = choices[0];
      const message = choice.message as Record<string, unknown> | undefined;
      if (message) {
        span.output = {
          content: message.content,
          role: message.role,
        };
      }
    }

    span.attributes["response_id"] = obj.id;
    span.status = "ok";
  }

  span.endTime = Date.now() / 1000;
}

export function instrument(): void {
  try {
    // Dynamic import to avoid hard dependency
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const openai = require("openai");
    if (openai?.OpenAI) {
      const OpenAI = openai.OpenAI;

      // Patch the prototype so ALL instances are instrumented
      const proto = OpenAI.prototype;
      if (proto?.chat?.completions?.create) {
        originalSyncCreate = proto.chat.completions.create;
        proto.chat.completions.create = function (
          this: unknown,
          ...args: unknown[]
        ) {
          const options = args[0] as Record<string, unknown> | undefined;
          const model = (options?.model as string) || "unknown";
          const messages = (options?.messages as unknown[]) || [];

          const span = buildSpan(model, messages);

          try {
            const result = originalSyncCreate!.apply(this, args);
            finishSpan(span, result, model);
            return result;
          } catch (error) {
            span.status = "error";
            span.attributes["error.message"] =
              error instanceof Error ? error.message : String(error);
            span.endTime = Date.now() / 1000;
            throw error;
          }
        };
      }
    }
  } catch {
    // OpenAI not available, skip instrumentation
  }
}

export function uninstrument(): void {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const openai = require("openai");
    if (openai?.OpenAI && originalSyncCreate) {
      openai.OpenAI.prototype.chat.completions.create = originalSyncCreate;
    }
  } catch {
    // Ignore
  }
  originalSyncCreate = null;
  originalAsyncCreate = null;
}
