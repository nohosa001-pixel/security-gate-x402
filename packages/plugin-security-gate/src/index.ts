import type { Plugin } from "@elizaos/core";
import { auditEscrowTaskAction } from "./actions/auditEscrowTask.js";
import { createEscrowTaskAction } from "./actions/createEscrowTask.js";
import { inspectSafetyAction } from "./actions/inspectSafety.js";
import { securityGateEvaluator } from "./evaluators/securityGateEvaluator.js";
import { securityGatePostHandler } from "./postHandlers/securityGatePostHandler.js";
import { securityGatePreHandler } from "./preHandlers/securityGatePreHandler.js";
import { securityStatusProvider } from "./providers/securityStatusProvider.js";

export * from "./actions/auditEscrowTask.js";
export * from "./actions/createEscrowTask.js";
export * from "./actions/inspectSafety.js";
export * from "./configIntegrity.js";
export * from "./constants.js";
export * from "./evaluators/securityGateEvaluator.js";
export * from "./localSecurityGate.js";
export * from "./postHandlers/securityGatePostHandler.js";
export * from "./preHandlers/securityGatePreHandler.js";
export * from "./providers/securityStatusProvider.js";

/**
 * 🛡️ Security Gate x402 Plugin for ElizaOS
 * Provides deterministic inbound prompt injection defense, dangerous code pattern detection,
 * outbound covert-channel DLP, config tamper detection, and agent safety guardrails.
 */
export const securityGatePlugin: Plugin = {
	name: "security-gate",
	description:
		"Deterministic inbound prompt injection defense, outbound covert-channel DLP, config tamper detection, dangerous code pattern detection, autonomous task escrow auditing, and agent safety guardrails.",
	actions: [inspectSafetyAction, auditEscrowTaskAction, createEscrowTaskAction],
	evaluators: [securityGateEvaluator],
	providers: [securityStatusProvider],
	chatPreHandlers: [securityGatePreHandler],
	chatPostHandlers: [securityGatePostHandler],
};


export default securityGatePlugin;
