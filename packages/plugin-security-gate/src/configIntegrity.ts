import { createHash } from "node:crypto";

export interface ConfigSeal {
	readonly baselineHash: string;
	readonly sealedAt: number;
	readonly keysSealed: string[];
}

export interface IntegrityCheckResult {
	isValid: boolean;
	status: "OK" | "TAMPER_DETECTED";
	tamperedKeys?: string[];
	message?: string;
}

/**
 * Computes deterministic SHA-256 hash of sorted key-value pairs.
 */
export function hashConfigObject(config: Record<string, unknown>): string {
	const sortedKeys = Object.keys(config).sort();
	const serialized = sortedKeys.map((k) => `${k}=${JSON.stringify(config[k])}`).join("::");
	return createHash("sha256").update(serialized).digest("hex");
}

/**
 * Creates an immutable ConfigSeal baseline for runtime integrity checking.
 * Prevents in-memory tampering of allowlists, budgets, and security gate URLs.
 */
export function sealConfig(config: Record<string, unknown>): ConfigSeal {
	const baselineHash = hashConfigObject(config);
	return Object.freeze({
		baselineHash,
		sealedAt: Date.now(),
		keysSealed: Object.keys(config).sort(),
	});
}

/**
 * Verifies live runtime configuration against the sealed baseline.
 * If any sealed key has been altered, deleted, or polluted, returns TAMPER_DETECTED.
 */
export function verifyConfigIntegrity(
	seal: ConfigSeal,
	currentConfig: Record<string, unknown>,
): IntegrityCheckResult {
	const currentHash = hashConfigObject(currentConfig);
	if (currentHash === seal.baselineHash) {
		return { isValid: true, status: "OK" };
	}

	const tamperedKeys: string[] = [];
	for (const key of seal.keysSealed) {
		if (
			JSON.stringify(currentConfig[key]) !==
			undefined &&
			// Compare against expected baseline by checking key presence
			!(key in currentConfig)
		) {
			tamperedKeys.push(`${key} (missing)`);
		}
	}

	// Check if any key differs
	const recomputedHash = hashConfigObject(currentConfig);
	if (recomputedHash !== seal.baselineHash && tamperedKeys.length === 0) {
		tamperedKeys.push("configuration_value_modified");
	}

	return {
		isValid: false,
		status: "TAMPER_DETECTED",
		tamperedKeys,
		message: `[SECURITY GATE ALERT] Configuration tampering detected! Expected seal ${seal.baselineHash.slice(0, 10)}... got ${currentHash.slice(0, 10)}...`,
	};
}
