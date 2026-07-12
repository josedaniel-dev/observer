/**
 * OpenAI auto-instrumentation
 */

import { getTracer, type Span } from "../tracer";

let originalCreate: ((...args: unknown[]) => unknown) | null = null;

export function instrument(): void {
  try {
    // Dynamic import to avoid hard dependency
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const openai = require("openai");
    if (openai?.OpenAI) {
      const client = new openai.OpenAI();
      originalCreate = client.chat.completions.create.bind(client.chat.completions);
      client.chat.completions.create = patchedCreate;
    }
  } catch {
    // OpenAI not available, skip instrumentation
  }
}

async function patchedCreate(...args: unknown[]): Promise<unknown> {
  const tracer = getTracer();
  const options = args[0] as Record<string, unknown> | undefined;
  const model = (options?.model as string) || "unknown";
  const messages = options?.messages || [];

  const span: Span = tracer.startSpan("openai.chat.completions.create", {
    spanType: "llm",
    attributes: { model, messages },
  });

  try {
    const result = await originalCreate?.(...args);

    // Extract token usage
    if (result && typeof result === "object") {
      const usage = (result as Record<string, unknown>).usage as Record<
        string,
        unknown
      > | undefined;
      if (usage) {
        span.tokens = {
          input: (usage.prompt_tokens as number) || 0,
          output: (usage.completion_tokens as number) || 0,
          total: (usage.total_tokens as number) || 0,
        };
      }

      span.attributes["model"] = model;
      span.attributes["response_id"] = (result as Record<string, unknown>).id;
      span.status = "ok";
    }

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

export function uninstrument(): void {
  // Restore original if needed
  originalCreate = null;
}
