/**
 * Deterministic local security & prompt injection analyzer.
 * Runs 100% locally with sub-millisecond execution time, zero external network calls.
 */

export interface LocalAuditResult {
	verdict: "ALLOW" | "WARN" | "BLOCK";
	risk_score: number;
	threats: string[];
	executionTimeMs: number;
}

const INJECTION_PATTERNS = [
	{
		pattern: /ignore\s+(all\s+)?(previous|prior)\s+instructions/i,
		threat: "Prompt Injection: Instruction Override",
		risk: 90,
	},
	{
		pattern: /you\s+are\s+now\s+(in\s+)?dan\s+mode/i,
		threat: "Jailbreak: DAN Mode Persona",
		risk: 95,
	},
	{
		pattern: /developer\s+mode\s+(enabled|activated)/i,
		threat: "Jailbreak: Developer Mode Override",
		risk: 85,
	},
	{
		pattern: /bypass\s+(safety|content|security)\s+filters?/i,
		threat: "Security Filter Bypass Attempt",
		risk: 90,
	},
	{
		pattern: /system\s*:\s*override/i,
		threat: "System Prompt Spoofing",
		risk: 85,
	},
	{
		pattern: /disregard\s+(all\s+)?(system|rules|guidelines)/i,
		threat: "System Rule Disregard",
		risk: 90,
	},
];

const CODE_HAZARD_PATTERNS = [
	{
		pattern: /\b(os\.system|subprocess\.(Popen|run|call)|exec\(|eval\()/i,
		threat: "Malicious Code Execution Pattern",
		risk: 95,
	},
	{
		pattern: /\b(rm\s+-rf|del\s+\/f|\bformat\s+[a-z]:)/i,
		threat: "Destructive File System Command",
		risk: 98,
	},
	{
		pattern: /powershell(\.exe)?\s+(-enc|-encodedcommand)/i,
		threat: "Obfuscated PowerShell Execution",
		risk: 95,
	},
	{
		pattern: /__import__\s*\(\s*['"]os['"]\s*\)/i,
		threat: "Dynamic Import Execution Pattern",
		risk: 95,
	},
];

const CREDENTIAL_LEAK_PATTERNS = [
	{
		pattern: /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/i,
		threat: "Private Key Disclosure Attempt",
		risk: 99,
	},
	{
		pattern: /\b0x[a-fA-F0-9]{64}\b/,
		threat: "Raw Hex Private Key / Seed Material Detected",
		risk: 95,
	},
];

/**
 * Distinguishes legitimate EVM public transaction hashes, block hashes, and Keccak-256 digests
 * from actual private key / seed leaks.
 */
export function isBenignBlockchainHash(
	matchStart: number,
	matchEnd: number,
	content: string,
	window: number = 70,
): boolean {
	const start = Math.max(0, matchStart - window);
	const end = Math.min(content.length, matchEnd + window);
	const ctx = content.slice(start, end).toLowerCase();

	// Explicit private key indicators take precedence (threat)
	const privateKeyMarkers = [
		"private_key",
		"privatekey",
		"privkey",
		"priv_key",
		"secret_key",
		"secretkey",
		"signer_key",
		"signerkey",
		"wallet_key",
		"deployer_key",
		"private key",
		"secret key",
		"seed phrase",
		"mnemonic",
		"my key is",
		"export private_key",
		"private-key",
	];
	if (privateKeyMarkers.some((marker) => ctx.includes(marker))) {
		return false; // Definite private key leak attempt
	}

	// Legitimate on-chain public hash markers (benign)
	const benignHashMarkers = [
		"tx",
		"tx_hash",
		"txhash",
		"transaction",
		"transactionhash",
		"receipt",
		"block",
		"blockhash",
		"block_hash",
		"hash",
		"digest",
		"topic",
		"merkle",
		"root",
		"scan",
		"explorer",
		"chain",
		"polygon",
		"arbitrum",
		"ethereum",
		"base",
		"event",
		"log",
		"call",
		"signature",
		"nonce",
		"contract",
		"deployed",
		"status",
		"etherscan",
		"polygonscan",
		"arbiscan",
		"basescan",
		"0x402",
		"settled",
		"payment",
		"submitted",
	];
	if (benignHashMarkers.some((marker) => ctx.includes(marker))) {
		return true; // Benign on-chain transaction/block hash
	}

	// Preceding field names in JSON or code like "hash": "0x..."
	const preceding = content
		.slice(Math.max(0, matchStart - 30), matchStart)
		.toLowerCase();
	const jsonKeyMarkers = [
		'"hash"',
		'"tx"',
		'"id"',
		'"transaction"',
		'"block"',
		"hash =",
		"tx =",
		"tx:",
	];
	if (jsonKeyMarkers.some((k) => preceding.includes(k))) {
		return true;
	}

	return false;
}

/**
 * Heuristically detects whether a given payload contains code structures or scripts.
 */
export function isCodePayload(content: string): boolean {
	if (!content) return false;
	// Markdown code fence blocks
	if (/```[\s\S]*?```/.test(content)) return true;
	// Common programming language declarations & patterns
	const codePatterns = [
		/(?:^|\n)\s*(?:import\s+|from\s+[\w.]+\s+import|export\s+|def\s+\w+\s*\(|class\s+\w+[:\s]|function\s+\w*\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=)/,
		/(?:os\.system|subprocess\.|exec\(|eval\(|console\.log|print\(|\bif\s*\(.*?\)\s*\{)/,
		/(?:^|\n)\s*(?:if\s+__name__\s*==\s*['"]__main__['"]|#!\/bin\/(?:ba)?sh|#!\/usr\/bin\/env)/,
	];
	return codePatterns.some((p) => p.test(content));
}

export function inspectPayloadLocally(content: string): LocalAuditResult {
	const startTime = Date.now();
	const rawText = content || "";
	// Google-grade defense: normalize evasion vectors (null bytes, zero-width chars) before pattern matching
	const text = rawText
		.replace(/\0/g, " ")
		.replace(/[\u200B-\u200D\uFEFF]/g, "");
	const threats: string[] = [];
	let maxRisk = 0;

	for (const { pattern, threat, risk } of INJECTION_PATTERNS) {
		if (pattern.test(text)) {
			threats.push(threat);
			maxRisk = Math.max(maxRisk, risk);
		}
	}

	for (const { pattern, threat, risk } of CODE_HAZARD_PATTERNS) {
		if (pattern.test(text)) {
			threats.push(threat);
			maxRisk = Math.max(maxRisk, risk);
		}
	}

	for (const { pattern, threat, risk } of CREDENTIAL_LEAK_PATTERNS) {
		const match = pattern.exec(text);
		if (match) {
			// If matching a 64-hex string, check if it's a benign on-chain identifier
			if (pattern.source.includes("0x[a-fA-F0-9]{64}")) {
				if (
					isBenignBlockchainHash(
						match.index,
						match.index + match[0].length,
						text,
					)
				) {
					continue; // Legitimate EVM transaction or block hash
				}
			}
			threats.push(threat);
			maxRisk = Math.max(maxRisk, risk);
		}
	}

	let verdict: "ALLOW" | "WARN" | "BLOCK" = "ALLOW";
	if (maxRisk >= 75) {
		verdict = "BLOCK";
	} else if (maxRisk >= 30) {
		verdict = "WARN";
	}

	return {
		verdict,
		risk_score: maxRisk,
		threats,
		executionTimeMs: Math.max(1, Date.now() - startTime),
	};
}
