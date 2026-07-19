/**
 * Auto-instrumentation for LLM libraries
 */

import { instrument as instrumentOpenAI, uninstrument as uninstrumentOpenAI } from "./openai";
import { instrument as instrumentAnthropic, uninstrument as uninstrumentAnthropic } from "./anthropic";

export interface InstrumentOptions {
  openai?: boolean;
  anthropic?: boolean;
}

export function instrument(options: InstrumentOptions = {}): void {
  if (options.openai === true) {
    instrumentOpenAI();
  }
  if (options.anthropic === true) {
    instrumentAnthropic();
  }
}

export function uninstrument(options: InstrumentOptions = {}): void {
  if (options.openai === true) {
    uninstrumentOpenAI();
  }
  if (options.anthropic === true) {
    uninstrumentAnthropic();
  }
}
