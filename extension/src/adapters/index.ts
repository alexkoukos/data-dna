import type { Adapter } from "./types";
import { chatgpt } from "./chatgpt";
import { claude } from "./claude";
import { gemini } from "./gemini";
import { mockAi } from "./mock";

export const ADAPTERS: Adapter[] = [mockAi, chatgpt, claude, gemini];

export function adapterFor(url: URL): Adapter | undefined {
  return ADAPTERS.find((a) => a.matches(url));
}
