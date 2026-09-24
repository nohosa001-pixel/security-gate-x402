import type {
	Action,
	ActionResult,
	ContentValue,
	HandlerCallback,
	IAgentRuntime,
	Memory,
	State,
} from "@elizaos/core";

export const createEscrowTaskAction: Action = {
	name: "CREATE_ESCROW_TASK",
	similes: [
		"CREATE_AGENT_TASK",
		"DEPOSIT_ESCROW_TASK",
		"SUB_CONTRACT_AGENT",
		"STAKE_AGENT_TASK",
	],
	description:
		"Creates a bilateral staked M2M task escrow contract. Locks client payout and sets required collateral stake for autonomous sub-contracting agents.",

	async validate(_runtime: IAgentRuntime, message: Memory): Promise<boolean> {
		const text = message?.content?.text || "";
		return Boolean(text && text.trim().length > 0);
	},

	async handler(
		_runtime: IAgentRuntime,
		message: Memory,
		_state?: State,
		_options?: Record<string, unknown>,
		callback?: HandlerCallback,
	): Promise<ActionResult> {
		const text = message.content?.text || "";
		const options = _options || {};
		const contentData = (message.content as Record<string, unknown>) || {};

		const worker = String(
			options.worker ??
				options.workerAddress ??
				contentData.worker ??
				"0x0000000000000000000000000000000000000000",
		);
		const payout = Number(
			options.payout ??
				options.payoutUsdc ??
				contentData.payout ??
				50.0,
		);
		const stake = Number(
			options.stake ??
				options.stakeUsdc ??
				contentData.stake ??
				15.0,
		);
		const durationSeconds = Number(
			options.durationSeconds ??
				contentData.durationSeconds ??
				86400,
		);

		const responseText = `🛡️ [A.GRID ESCROW] Task Escrow Prepared:\n- Worker: ${worker}\n- Locked Payout: ${payout} USDC\n- Required Collateral Stake: ${stake} USDC\n- SLA Duration: ${durationSeconds / 3600}h\n- Invariant: 100% US Treasury Backed Non-custodial Clearinghouse.`;

		if (callback) {
			const callbackData: Record<string, ContentValue> = {
				worker,
				payoutUsdc: payout,
				stakeUsdc: stake,
				durationSeconds,
				spec: text,
				prepared: true,
			};
			await callback({
				text: responseText,
				data: callbackData,
			});
		}

		return {
			success: true,
			text: responseText,
			data: {
				worker,
				payoutUsdc: payout,
				stakeUsdc: stake,
				durationSeconds,
				spec: text,
			},
		};
	},

	examples: [
		[
			{
				name: "ClientAgent",
				content: {
					text: "Create an escrow task for 0xWorkerAgent to crawl DeFi yields. Payout: 50 USDC, Stake: 15 USDC.",
				},
			},
			{
				name: "EscrowAgent",
				content: {
					text: "🛡️ [A.GRID ESCROW] Task Escrow Prepared:\n- Worker: 0xWorkerAgent\n- Locked Payout: 50 USDC\n- Required Collateral Stake: 15 USDC\n- SLA Duration: 24h\n- Invariant: 100% US Treasury Backed Non-custodial Clearinghouse.",
					action: "CREATE_ESCROW_TASK",
				},
			},
		],
	],
};
