/**
 * Anthropic auto-instrumentation
 */

import { getTracer, type Span } from "../tracer";
import { calculateCost } from "../pricing";

let originalMessagesCreate: ((...args: unknown[]) => unknown) | null = null;
let originalAsyncMessagesCreate: ((...args: unknown[]) => unknown) | null = null;

function buildSpan(model: string, messages: unknown[]): Span {
  const tracer = getTracer();
  const span = tracer.startSpan("anthropic.messages.create", {
    spanType: "llm",
    attributes: {
      "gen_ai.system": "anthropic",
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
      const inputTokens = (usage.input_tokens as number) || 0;
      const outputTokens = (usage.output_tokens as number) || 0;
      span.tokens = {
        input: inputTokens,
        output: outputTokens,
        total: inputTokens + outputTokens,
      };

      const cost = calculateCost(model, inputTokens, outputTokens);
      if (cost !== null) {
        span.costUsd = cost;
      }
    }

    // Extract output content
    const content = obj.content as Array<Record<string, unknown>> | undefined;
    if (content && content.length > 0) {
      const textBlocks = content
        .filter((b) => b.type === "text")
        .map((b) => b.text as string);
      span.output = {
        content: textBlocks.join("\n"),
        stop_reason: obj.stop_reason,
      };
    }

    span.attributes["response_id"] = obj.id;
    span.attributes["model"] = obj.model;
    span.status = "ok";
  }

  span.endTime = Date.now() / 1000;
}

export function instrument(): void {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const anthropic = require("anthropic");
    if (anthropic?.Anthropic) {
      const Anthropic = anthropic.Anthropic;
      const proto = Anthropic.prototype;

      if (proto?.messages?.create) {
        originalMessagesCreate = proto.messages.create;
        proto.messages.create = function (
          this: unknown,
          ...args: unknown[]
        ) {
          const options = args[0] as Record<string, unknown> | undefined;
          const model = (options?.model as string) || "unknown";
          const messages = (options?.messages as unknown[]) || [];

          const span = buildSpan(model, messages);

          try {
            const result = originalMessagesCreate!.apply(this, args);
            // Handle both sync and async
            if (result && typeof (result as Promise<unknown>).then === "function") {
              return (result as Promise<unknown>).then(
                (resolved: unknown) => {
                  finishSpan(span, resolved, model);
                  return resolved;
                },
                (error: Error) => {
                  span.status = "error";
                  span.attributes["error.message"] = error.message;
                  span.endTime = Date.now() / 1000;
                  throw error;
                }
              );
            }
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

      // Patch async client if available
      if (anthropic.AsyncAnthropic) {
        const asyncProto = anthropic.AsyncAnthropic.prototype;
        if (asyncProto?.messages?.create) {
          originalAsyncMessagesCreate = asyncProto.messages.create;
          asyncProto.messages.create = function (
            this: object,
            ...args: unknown[]
          ) {
            const options = args[0] as Record<string, unknown> | undefined;
            const model = (options?.model as string) || "unknown";
            const messages = (options?.messages as unknown[]) || [];

            const span = buildSpan(model, messages);
            const ctx = this;

            return (originalAsyncMessagesCreate!.apply(ctx, args) as Promise<unknown>).then(
              (result: unknown) => {
                finishSpan(span, result, model);
                return result;
              },
              (error: Error) => {
                span.status = "error";
                span.attributes["error.message"] = error.message;
                span.endTime = Date.now() / 1000;
                throw error;
              }
            );
          };
        }
      }
    }
  } catch {
    // Anthropic not available, skip instrumentation
  }
}

export function uninstrument(): void {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const anthropic = require("anthropic");
    if (anthropic?.Anthropic && originalMessagesCreate) {
      anthropic.Anthropic.prototype.messages.create = originalMessagesCreate;
    }
    if (anthropic?.AsyncAnthropic && originalAsyncMessagesCreate) {
      anthropic.AsyncAnthropic.prototype.messages.create = originalAsyncMessagesCreate;
    }
  } catch {
    // Ignore
  }
  originalMessagesCreate = null;
  originalAsyncMessagesCreate = null;
}
