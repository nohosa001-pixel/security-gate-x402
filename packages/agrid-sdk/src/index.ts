/**
 * 🌐 A.GRID Autonomous Agent SDK & Unified Ecosystem Suite
 *
 * Subpath Modules:
 * - agrid-sdk/security : Inbound/outbound prompt injection defense, task escrow, Safe session key guard.
 * - agrid-sdk/cleanweb : CleanWeb 87% token-compressed LLM scraping, ad/tracker removal, ground-truth signals.
 * - agrid-sdk/minerals : Critical minerals supply-chain verification, defense procurement (NDAA), battery passport.
 */

// Export namespaces
export * as security from "./security/index.js";
export * as cleanweb from "./cleanweb/index.js";
export * as minerals from "./minerals/index.js";

// Master top-level convenience exports
export { securityGatePlugin, inspectPayloadLocally } from "./security/index.js";
export { cleanWebPlugin, scrapeWebAction } from "./cleanweb/index.js";
export { MineralsOracleClient, createMineralsOracleTools } from "./minerals/index.js";
