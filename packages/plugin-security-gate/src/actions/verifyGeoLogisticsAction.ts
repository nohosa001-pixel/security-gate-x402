import type {
	Action,
	ActionResult,
	Content,
	HandlerCallback,
	IAgentRuntime,
	Memory,
	State,
} from "@elizaos/core";

export interface GeoLogisticsInput {
	containerId: string;
	currentCoords: [number, number]; // [lat, lng]
	targetCoords: [number, number];  // [lat, lng]
	maxGeofenceMeters?: number;
	currentTempCelsius?: number;
	minTempCelsius?: number;
	maxTempCelsius?: number;
	sealTampered?: boolean;
	eBlNumber?: string;
}

/**
 * Calculates great-circle distance between two GPS coordinates using Haversine formula (in meters)
 */
export function calculateHaversineMeters(
	coords1: [number, number],
	coords2: [number, number]
): number {
	const R = 6371000; // Earth radius in meters
	const lat1 = (coords1[0] * Math.PI) / 180;
	const lat2 = (coords2[0] * Math.PI) / 180;
	const dLat = ((coords2[0] - coords1[0]) * Math.PI) / 180;
	const dLng = ((coords2[1] - coords1[1]) * Math.PI) / 180;

	const a =
		Math.sin(dLat / 2) * Math.sin(dLat / 2) +
		Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
	const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

	return Math.round(R * c);
}

export function inspectGeoLogisticsTruth(input: GeoLogisticsInput) {
	const errors: string[] = [];
	const maxMeters = input.maxGeofenceMeters ?? 500;
	const distanceMeters = calculateHaversineMeters(input.currentCoords, input.targetCoords);

	if (distanceMeters > maxMeters) {
		errors.push(`OUTSIDE_GEOFENCE: Distance is ${distanceMeters}m, which exceeds arrival threshold of ${maxMeters}m.`);
	}

	if (input.sealTampered) {
		errors.push("E_SEAL_TAMPERED: Hardware Electronic Seal integrity violated during transit.");
	}

	if (typeof input.currentTempCelsius === "number") {
		if (typeof input.maxTempCelsius === "number" && input.currentTempCelsius > input.maxTempCelsius) {
			errors.push(`COLD_CHAIN_BREACH: Temp ${input.currentTempCelsius}°C exceeds maximum threshold ${input.maxTempCelsius}°C.`);
		}
		if (typeof input.minTempCelsius === "number" && input.currentTempCelsius < input.minTempCelsius) {
			errors.push(`COLD_CHAIN_BREACH: Temp ${input.currentTempCelsius}°C below minimum threshold ${input.minTempCelsius}°C.`);
		}
	}

	const passed = errors.length === 0;
	return {
		verdict: passed ? "PASSED" : "FAILED",
		domain: "LOGISTICS_POD_AND_GEO",
		containerId: input.containerId,
		distanceMeters,
		withinGeofence: distanceMeters <= maxMeters,
		sealSecure: !input.sealTampered,
		temperatureCelsius: input.currentTempCelsius,
		errors,
		timestamp: new Date().toISOString()
	};
}

export const verifyGeoLogisticsAction: Action = {
	name: "VERIFY_GEO_LOGISTICS",
	similes: ["VERIFY_POD", "CHECK_GEOFENCE", "AUDIT_COLD_CHAIN", "VERIFY_CONTAINER_ARRIVAL", "INSPECT_E_SEAL"],
	description:
		"Verifies autonomous mobility and logistics Proof-of-Delivery (PoD): Great-circle Haversine GNSS geofence arrival (<500m), hardware E-Seal tamper integrity, and cold-chain temperature telemetry.",

	async validate(_runtime: IAgentRuntime, message: Memory): Promise<boolean> {
		const text = (message?.content?.text || "").toLowerCase();
		return text.includes("geofence") || text.includes("gps") || text.includes("logistics") || text.includes("container") || text.includes("cold chain") || text.includes("pod");
	},

	async handler(
		_runtime: IAgentRuntime,
		message: Memory,
		_state?: State,
		options?: Record<string, unknown>,
		callback?: HandlerCallback,
	): Promise<ActionResult> {
		const contentData = (message.content as Record<string, unknown>) || {};
		const defaultPortCoords: [number, number] = [51.9244, 4.4777]; // Port of Rotterdam
		const defaultContainerCoords: [number, number] = [51.9250, 4.4780]; // ~80m away

		const input: GeoLogisticsInput = {
			containerId: String(options?.containerId || contentData.containerId || "MSKU9012345"),
			currentCoords: (options?.currentCoords || contentData.currentCoords || defaultContainerCoords) as [number, number],
			targetCoords: (options?.targetCoords || contentData.targetCoords || defaultPortCoords) as [number, number],
			maxGeofenceMeters: Number(options?.maxGeofenceMeters ?? contentData.maxGeofenceMeters ?? 500),
			currentTempCelsius: Number(options?.currentTempCelsius ?? contentData.currentTempCelsius ?? -19.5),
			maxTempCelsius: Number(options?.maxTempCelsius ?? contentData.maxTempCelsius ?? -18.0),
			minTempCelsius: Number(options?.minTempCelsius ?? contentData.minTempCelsius ?? -25.0),
			sealTampered: Boolean(options?.sealTampered ?? contentData.sealTampered ?? false),
			eBlNumber: String(options?.eBlNumber || contentData.eBlNumber || "EBL-DCSA-2026-0091")
		};

		const result = inspectGeoLogisticsTruth(input);

		if (callback) {
			const text = result.verdict === "PASSED"
				? `🚚 [GEO LOGISTICS: VERIFIED] Container ${input.containerId} | ${result.distanceMeters}m from Destination | Seal Secure | Temp: ${input.currentTempCelsius}°C`
				: `🚨 [GEO LOGISTICS: REJECTED] Invariant Violations: ${result.errors.join("; ")}`;
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
