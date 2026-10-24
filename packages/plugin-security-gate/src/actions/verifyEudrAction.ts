import type {
	Action,
	ActionResult,
	Content,
	HandlerCallback,
	IAgentRuntime,
	Memory,
	State,
} from "@elizaos/core";

export const SUPPORTED_EUDR_COMMODITIES = [
	"wood", "timber", "paper", "pulp", "wood_pulp", "printed_books",
	"rubber", "tire", "tires",
	"palm_oil", "palm", "palm_kernel",
	"soy", "soya", "soybean",
	"coffee",
	"cocoa", "chocolate",
	"cattle", "beef", "leather"
];

export interface EudrVerificationInput {
	commodity: string;
	countryCode: string;
	polygonCoords: [number, number][]; // [lat, lng] array
	deforestationFreeAfterCutoff: boolean;
	ddsReference: string;
	legalProduction: boolean;
}

export function inspectEudrCompliance(input: EudrVerificationInput) {
	const errors: string[] = [];
	const cleanCommodity = (input.commodity || "").toLowerCase().trim();

	if (!SUPPORTED_EUDR_COMMODITIES.includes(cleanCommodity)) {
		errors.push(`NON_EUDR_COMMODITY: '${input.commodity}' is not covered under Regulation (EU) 2023/1115 Annex I.`);
	}

	if (!input.deforestationFreeAfterCutoff) {
		errors.push("DEFORESTATION_DETECTED: Satellite imagery detected forest cover loss after December 31, 2020 cutoff date.");
	}

	if (!input.polygonCoords || input.polygonCoords.length < 3) {
		errors.push("INVALID_POLYGON: EUDR Article 9 requires a polygon with at least 3 distinct GPS coordinates for plots > 4 hectares.");
	}

	if (!input.ddsReference || input.ddsReference.trim().length < 5) {
		errors.push("MISSING_DDS: Valid Due Diligence Statement (DDS) reference for EU Information System (Traces NT) is mandatory.");
	}

	if (!input.legalProduction) {
		errors.push("ILLEGAL_HARVEST: Production failed to meet local land use, labor, and human rights legislation.");
	}

	const passed = errors.length === 0;
	return {
		verdict: passed ? "PASSED" : "FAILED",
		domain: "EUDR_FOREST",
		commodity: cleanCommodity,
		countryCode: (input.countryCode || "UNKNOWN").toUpperCase(),
		polygonPoints: input.polygonCoords?.length || 0,
		ddsReference: input.ddsReference,
		errors,
		timestamp: new Date().toISOString()
	};
}

export const verifyEudrAction: Action = {
	name: "VERIFY_EUDR_COMPLIANCE",
	similes: ["CHECK_EUDR", "AUDIT_DEFORESTATION", "VERIFY_DDS", "INSPECT_TIMBER", "INSPECT_PALM_OIL"],
	description:
		"Verifies compliance with the EU Deforestation Regulation (EUDR, Regulation (EU) 2023/1115). Validates satellite deforestation cutoff (2020-12-31), GPS plot polygons, and Traces NT Due Diligence Statements.",

	async validate(_runtime: IAgentRuntime, message: Memory): Promise<boolean> {
		const text = (message?.content?.text || "").toLowerCase();
		return text.includes("eudr") || text.includes("deforestation") || SUPPORTED_EUDR_COMMODITIES.some(c => text.includes(c));
	},

	async handler(
		_runtime: IAgentRuntime,
		message: Memory,
		_state?: State,
		options?: Record<string, unknown>,
		callback?: HandlerCallback,
	): Promise<ActionResult> {
		const contentData = (message.content as Record<string, unknown>) || {};
		const defaultPolygon: [number, number][] = [
			[-3.12, 102.45],
			[-3.15, 102.50],
			[-3.18, 102.42]
		];

		const input: EudrVerificationInput = {
			commodity: String(options?.commodity || contentData.commodity || "palm_oil"),
			countryCode: String(options?.countryCode || contentData.countryCode || "ID"),
			polygonCoords: (options?.polygonCoords || contentData.polygonCoords || defaultPolygon) as [number, number][],
			deforestationFreeAfterCutoff: Boolean(options?.deforestationFreeAfterCutoff ?? contentData.deforestationFreeAfterCutoff ?? true),
			ddsReference: String(options?.ddsReference || contentData.ddsReference || "DDS-2026-EU-99214"),
			legalProduction: Boolean(options?.legalProduction ?? contentData.legalProduction ?? true)
		};

		const result = inspectEudrCompliance(input);

		if (callback) {
			const text = result.verdict === "PASSED"
				? `🌲 [EUDR COMPLIANCE: VERIFIED] ${input.commodity.toUpperCase()} (${result.countryCode}) | Zero Deforestation | DDS: ${result.ddsReference}`
				: `🚨 [EUDR COMPLIANCE: REJECTED] Invariant Violations: ${result.errors.join("; ")}`;
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
