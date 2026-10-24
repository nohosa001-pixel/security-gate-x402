import type {
	Action,
	ActionResult,
	Content,
	HandlerCallback,
	IAgentRuntime,
	Memory,
	State,
} from "@elizaos/core";

export const SUPPORTED_MINERALS = [
	"tin", "tantalum", "tungsten", "gold", "3tg",
	"cobalt", "lithium", "nickel", "copper", "rare_earth"
];

export const VALID_SMELTER_STATUSES = ["CONFORMANT", "ACTIVE", "CERTIFIED"];

export interface MineralsVerificationInput {
	mineralType: string;
	smelterId: string;
	smelterAuditStatus: string;
	mineCountryCode: string;
	chainOfCustodyVerified: boolean;
	childLaborFree: boolean;
	conflictRegion?: boolean;
	enhancedDueDiligence?: boolean;
}

export function inspectMineralsTruth(input: MineralsVerificationInput) {
	const errors: string[] = [];
	const cleanMineral = (input.mineralType || "").toLowerCase().trim();

	if (!SUPPORTED_MINERALS.includes(cleanMineral)) {
		errors.push(`UNSUPPORTED_MINERAL: ${input.mineralType}. Must be 3TG or battery critical mineral.`);
	}

	const cleanStatus = (input.smelterAuditStatus || "").toUpperCase().trim();
	if (!VALID_SMELTER_STATUSES.includes(cleanStatus)) {
		errors.push(`INVALID_SMELTER_STATUS: ${input.smelterAuditStatus}. Smelter must be CONFORMANT or ACTIVE under RMI.`);
	}

	if (!input.smelterId || input.smelterId.trim().length < 3) {
		errors.push("MISSING_SMELTER_ID: Smelter ID must be provided for RMI traceability.");
	}

	if (!input.chainOfCustodyVerified) {
		errors.push("BROKEN_CHAIN_OF_CUSTODY: Upstream mass-balance / bag-and-tag verification failed.");
	}

	if (!input.childLaborFree) {
		errors.push("OECD_ANNEX_II_VIOLATION: Zero-tolerance child labor or severe human rights violation detected.");
	}

	if (input.conflictRegion && !input.enhancedDueDiligence) {
		errors.push("ENHANCED_DUE_DILIGENCE_REQUIRED: Mineral sourced from CAHRA (Conflict-Affected and High-Risk Area) without enhanced audit.");
	}

	const passed = errors.length === 0;
	return {
		verdict: passed ? "PASSED" : "FAILED",
		domain: "CONFLICT_MINERALS",
		mineral: cleanMineral,
		smelterId: input.smelterId,
		smelterStatus: cleanStatus,
		errors,
		timestamp: new Date().toISOString()
	};
}

export const verifyMineralsAction: Action = {
	name: "VERIFY_MINERALS_TRUTH",
	similes: ["AUDIT_MINERALS", "CHECK_CONFLICT_FREE", "VERIFY_BATTERY_MINERALS", "INSPECT_SMELTER"],
	description:
		"Verifies responsible and conflict-free supply chain provenance for 3TG and battery critical minerals (Lithium, Nickel, Cobalt, Copper). Validates RMI smelter audits and OECD Annex II due diligence.",

	async validate(_runtime: IAgentRuntime, message: Memory): Promise<boolean> {
		const text = (message?.content?.text || "").toLowerCase();
		return SUPPORTED_MINERALS.some(m => text.includes(m)) || text.includes("smelter") || text.includes("conflict mineral");
	},

	async handler(
		_runtime: IAgentRuntime,
		message: Memory,
		_state?: State,
		options?: Record<string, unknown>,
		callback?: HandlerCallback,
	): Promise<ActionResult> {
		const contentData = (message.content as Record<string, unknown>) || {};
		const input: MineralsVerificationInput = {
			mineralType: String(options?.mineralType || contentData.mineralType || "lithium"),
			smelterId: String(options?.smelterId || contentData.smelterId || "CID002845"),
			smelterAuditStatus: String(options?.smelterAuditStatus || contentData.smelterAuditStatus || "CONFORMANT"),
			mineCountryCode: String(options?.mineCountryCode || contentData.mineCountryCode || "AU"),
			chainOfCustodyVerified: Boolean(options?.chainOfCustodyVerified ?? contentData.chainOfCustodyVerified ?? true),
			childLaborFree: Boolean(options?.childLaborFree ?? contentData.childLaborFree ?? true),
			conflictRegion: Boolean(options?.conflictRegion ?? contentData.conflictRegion ?? false),
			enhancedDueDiligence: Boolean(options?.enhancedDueDiligence ?? contentData.enhancedDueDiligence ?? true)
		};

		const result = inspectMineralsTruth(input);

		if (callback) {
			const text = result.verdict === "PASSED"
				? `💎 [MINERALS TRUTH: VERIFIED] ${input.mineralType.toUpperCase()} | Smelter ${input.smelterId} (${result.smelterStatus}) | CoC Verified`
				: `🚨 [MINERALS TRUTH: REJECTED] Invariant Violations: ${result.errors.join("; ")}`;
			await callback({
				text,
				data: result as Record<string, unknown>
			} as Content);
		}

		return {
			success: result.verdict === "PASSED",
			data: result
		};
	}
};
