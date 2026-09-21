import type {
	Action,
	ActionResult,
	ContentValue,
	HandlerCallback,
	IAgentRuntime,
	Memory,
	State,
} from "@elizaos/core";
import { inspectPayloadLocally, isCodePayload } from "../localSecurityGate.js";

declare const process: { env?: Record<string, string | undefined> } | undefined;

export const auditEscrowTaskAction: Action = {
	name: "AUDIT_ESCROW_TASK",
	similes: [
		"VERIFY_TASK_DELIVERABLE",
		"AUDIT_DELIVERABLE",
		"ESCROW_AUDIT",
		"SLASH_ESCROW_TASK",
	],
	description:
		"Audits an autonomous agent work deliverable for on-chain AgentEscrow settlement or slashing. Verifies against job specifications, detects prompt injections/code exploits, and produces EIP-712 cryptographic proofs.",

	async validate(_runtime: IAgentRuntime, message: Memory): Promise<boolean> {
		const text = message?.content?.text || "";
		return Boolean(text && text.trim().length > 0);
	},

	async handler(
		runtime: IAgentRuntime,
		message: Memory,
		_state?: State,
		_options?: Record<string, unknown>,
		callback?: HandlerCallback,
	): Promise<ActionResult> {
		const text = message.content?.text || "";
		const options = _options || {};
		const contentData = (message.content as Record<string, unknown>) || {};

		const jobId = Number(
			options.jobId ??
				options.job_id ??
				contentData.jobId ??
				contentData.job_id ??
				1,
		);
		const groundTruth = String(
			options.groundTruth ??
				options.ground_truth_spec ??
				contentData.groundTruth ??
				contentData.ground_truth_spec ??
				"",
		);
		const isCode =
			Boolean(
				options.isCode ??
					options.is_code ??
					contentData.isCode ??
					contentData.is_code,
			) || isCodePayload(text);

		// 1. Local deterministic inspection
		const localAudit = inspectPayloadLocally(text);

		const env = process?.env ?? {};
		const configuredGateUrl =
			runtime.getSetting("SECURITY_GATE_URL") ||
			env.SECURITY_GATE_URL ||
			"https://agent-security-gate-x402-212942243360.asia-northeast3.run.app";

		let attestation: Record<string, unknown> | null = null;
		let verdict = localAudit.verdict === "BLOCK" ? "BLOCKED" : "PASSED";
		let riskScore = localAudit.risk_score;
		let threats = localAudit.threats;

		// 2. Fetch signed EIP-712 attestation from micro-oracle
		if (configuredGateUrl) {
			try {
				const resp = await fetch(`${configuredGateUrl}/api/v1/escrow/audit`, {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...(env.SECURITY_GATE_API_KEY
							? { "X-API-Key": env.SECURITY_GATE_API_KEY }
							: {}),
					},
					body: JSON.stringify({
						job_id: jobId,
						deliverable: text,
						ground_truth_spec: groundTruth || undefined,
						is_code: isCode,
						chain_id: 137,
						verifying_contract: "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
					}),
					signal: AbortSignal.timeout(4000),
				});

				if (resp.ok) {
					const data = (await resp.json()) as {
						verdict?: string;
						risk_score?: number;
						threats?: string[];
						attestation?: Record<string, unknown>;
					};
					verdict = data.verdict || verdict;
					riskScore =
						typeof data.risk_score === "number"
							? Math.round(data.risk_score * 100)
							: riskScore;
					threats = data.threats || threats;
					attestation = data.attestation || null;
				}
			} catch (err) {
				console.warn(
					"[SecurityGate:Escrow] Remote oracle call failed, using local verdict:",
					err,
				);
			}
		}

		const isSafe = verdict === "PASSED" && riskScore <= 25;
		const responseText = isSafe
			? `✅ [ESCROW AUDIT: PASSED] Job #${jobId} deliverable verified safe (Risk: ${riskScore}%). Approved for on-chain completeJob() payout release.`
			: `🚨 [ESCROW AUDIT: SLASHED] Job #${jobId} deliverable rejected (Risk: ${riskScore}%). Threats: ${threats.join(", ") || "Safety Violation"}. Ready for on-chain slashJob() collateral forfeiture.`;

		if (callback) {
			const callbackData: Record<string, ContentValue> = {
				jobId,
				verdict,
				isSafe,
				riskScore,
				threats,
				hasAttestation: Boolean(attestation),
			};
			await callback({
				text: responseText,
				data: callbackData,
			});
		}

		return {
			success: isSafe,
			text: responseText,
			data: {
				jobId,
				verdict,
				isSafe,
				riskScore,
				threats,
				attestation,
			},
		};
	},

	examples: [
		[
			{
				name: "ClientAgent",
				content: {
					text: "Verify deliverable for Escrow Job #42: Polygon pool yield report.",
				},
			},
			{
				name: "SheriffAgent",
				content: {
					text: "✅ [ESCROW AUDIT: PASSED] Job #42 deliverable verified safe (Risk: 0%). Approved for on-chain completeJob() payout release.",
					action: "AUDIT_ESCROW_TASK",
				},
			},
		],
	],
};
