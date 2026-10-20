import type { Plugin } from "@elizaos/core";
import { scrapeWebAction } from "./scrape.js";
import { groundTruthSignalEvaluator } from "./signal.js";
import { cleanWebIntelligenceProvider } from "./intelligence.js";

export * from "./scrape.js";
export * from "./signal.js";
export * from "./intelligence.js";

export const cleanWebPlugin: Plugin = {
  name: "cleanweb-intelligence",
  description: "CleanWeb 87% token-compressed ad-free web intelligence and Solana x402 micropayments.",
  actions: [scrapeWebAction as any],
  evaluators: [groundTruthSignalEvaluator as any],
  providers: [cleanWebIntelligenceProvider as any],
};

export default cleanWebPlugin;
