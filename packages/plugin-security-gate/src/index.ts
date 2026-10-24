import type { Plugin } from "@elizaos/core";
import { auditEscrowTaskAction } from "./actions/auditEscrowTask.js";
import { createEscrowTaskAction } from "./actions/createEscrowTask.js";
import { inspectSafetyAction } from "./actions/inspectSafety.js";
import { executeGuardedOnchainAction } from "./actions/executeGuardedOnchainAction.js";
import { scrapeWebAction } from "./actions/cleanwebScrape.js";
import { verifyMineralsAction } from "./actions/verifyMineralsAction.js";
import { verifyEudrAction } from "./actions/verifyEudrAction.js";
import { verifyGeoLogisticsAction } from "./actions/verifyGeoLogisticsAction.js";

import { securityGateEvaluator } from "./evaluators/securityGateEvaluator.js";
import { groundTruthSignalEvaluator } from "./evaluators/cleanwebSignal.js";
import {
	type ChatPostHandler,
	securityGatePostHandler,
} from "./postHandlers/securityGatePostHandler.js";
import {
	type ChatPreHandler,
	securityGatePreHandler,
} from "./preHandlers/securityGatePreHandler.js";
import { securityStatusProvider } from "./providers/securityStatusProvider.js";
import { cleanWebIntelligenceProvider } from "./providers/cleanwebIntelligence.js";
import { unifiedTruthProvider } from "./providers/unifiedTruthProvider.js";

// Export All Actions
export * from "./actions/auditEscrowTask.js";
export * from "./actions/createEscrowTask.js";
export * from "./actions/inspectSafety.js";
export * from "./actions/executeGuardedOnchainAction.js";
export * from "./actions/cleanwebScrape.js";
export * from "./actions/verifyMineralsAction.js";
export * from "./actions/verifyEudrAction.js";
export * from "./actions/verifyGeoLogisticsAction.js";

// Export Core Logic & Helpers
export * from "./GuardedSafeExecutor.js";
export * from "./configIntegrity.js";
export * from "./constants.js";
export * from "./evaluators/securityGateEvaluator.js";
export * from "./evaluators/cleanwebSignal.js";
export * from "./localSecurityGate.js";
export * from "./postHandlers/securityGatePostHandler.js";
export * from "./preHandlers/securityGatePreHandler.js";
export * from "./providers/securityStatusProvider.js";
export * from "./providers/cleanwebIntelligence.js";
export * from "./providers/unifiedTruthProvider.js";

/**
 * 🌐 CleanWeb x A.GRID Web Intelligence Plugin
 */
export const cleanWebPlugin: Plugin = {
	name: "cleanweb-intelligence",
	description:
		"87% Token-compressed ad-free web intelligence, EUDR & mineral ground truth invariants, and Solana x402 autonomous micropayments.",
	actions: [scrapeWebAction as any],
	evaluators: [groundTruthSignalEvaluator as any],
	providers: [cleanWebIntelligenceProvider as any],
};

/**
 * 💎 Critical Minerals Truth Verification Plugin
 */
export const mineralsPlugin: Plugin = {
	name: "minerals-truth",
	description:
		"Responsible & conflict-free supply chain verification for 3TG and battery critical minerals (Lithium, Nickel, Cobalt, Copper, Rare Earths). RMI smelter and OECD Annex II audit verification.",
	actions: [verifyMineralsAction as any],
	providers: [unifiedTruthProvider as any],
};

/**
 * 🌲 EUDR Deforestation Compliance Plugin
 */
export const eudrPlugin: Plugin = {
	name: "eudr-compliance",
	description:
		"EU Deforestation Regulation (EUDR Regulation 2023/1115) physical truth verification: Satellite deforestation cutoff, GPS plot polygons, and Traces NT Due Diligence Statements.",
	actions: [verifyEudrAction as any],
	providers: [unifiedTruthProvider as any],
};

/**
 * 🚚 Geo & Logistics PoD Verification Plugin
 */
export const geoLogisticsPlugin: Plugin = {
	name: "geo-logistics-pod",
	description:
		"Autonomous mobility and multimodal delivery truth: Haversine GNSS geofence arrival (<500m), hardware E-Seal tamper integrity, and cold-chain temperature telemetry.",
	actions: [verifyGeoLogisticsAction as any],
	providers: [unifiedTruthProvider as any],
};

/**
 * 🛡️ Security Gate x402 Core Plugin
 */
export const securityGatePlugin: Plugin & {
	chatPreHandlers?: any[];
	chatPostHandlers?: any[];
} = {
	name: "security-gate",
	description:
		"Deterministic inbound prompt injection defense, outbound covert-channel DLP, config tamper detection, dangerous code pattern detection, autonomous task escrow auditing, Safe guard execution, and agent safety guardrails.",
	actions: [inspectSafetyAction, auditEscrowTaskAction, createEscrowTaskAction, executeGuardedOnchainAction],
	evaluators: [securityGateEvaluator],
	providers: [securityStatusProvider],
	chatPreHandlers: [securityGatePreHandler as any],
	chatPostHandlers: [securityGatePostHandler as any],
};

/**
 * 👑 Universal Sovereign Suite Plugin (All 6 Domains: Security, CleanWeb, Minerals, EUDR, Onchain, Geo)
 */
export const universalSovereignSuitePlugin: Plugin & {
	chatPreHandlers?: any[];
	chatPostHandlers?: any[];
} = {
	name: "security-gate-universal-suite",
	description:
		"Unified sovereign execution and clearinghouse suite for autonomous AI agents covering Security, CleanWeb, Minerals, EUDR, Onchain Safe/Solana Escrow, and Geo-Logistics PoD.",
	actions: [
		inspectSafetyAction,
		auditEscrowTaskAction,
		createEscrowTaskAction,
		executeGuardedOnchainAction,
		scrapeWebAction,
		verifyMineralsAction,
		verifyEudrAction,
		verifyGeoLogisticsAction,
	],
	evaluators: [securityGateEvaluator, groundTruthSignalEvaluator],
	providers: [securityStatusProvider, cleanWebIntelligenceProvider, unifiedTruthProvider],
	chatPreHandlers: [securityGatePreHandler as any],
	chatPostHandlers: [securityGatePostHandler as any],
};

export default universalSovereignSuitePlugin;
