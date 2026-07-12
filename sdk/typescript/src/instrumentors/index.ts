/**
 * Auto-instrumentation for LLM libraries
 */

import { instrument as instrumentOpenAI } from "./openai";

export interface InstrumentOptions {
  openai?: boolean;
}

export function instrument(options: InstrumentOptions = {}): void {
  if (options.openai !== false) {
    instrumentOpenAI();
  }
}
