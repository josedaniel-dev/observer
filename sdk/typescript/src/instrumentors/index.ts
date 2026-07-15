/**
 * Auto-instrumentation for LLM libraries
 */

import { instrument as instrumentOpenAI, uninstrument as uninstrumentOpenAI } from "./openai";

export interface InstrumentOptions {
  openai?: boolean;
}

export function instrument(options: InstrumentOptions = {}): void {
  if (options.openai === true) {
    instrumentOpenAI();
  }
}

export function uninstrument(options: InstrumentOptions = {}): void {
  if (options.openai === true) {
    uninstrumentOpenAI();
  }
}
