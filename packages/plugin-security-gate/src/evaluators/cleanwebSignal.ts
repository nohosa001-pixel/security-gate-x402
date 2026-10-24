import type {
	Evaluator,
	EvaluatorPromptContext,
	EvaluatorRunContext,
	JsonValue,
} from "@elizaos/core";

export const groundTruthSignalEvaluator: Evaluator<JsonValue> = {
	name: "GROUND_TRUTH_EVALUATOR",
	similes: ["EVALUATE_WORLD_SIGNAL", "ASSESS_CAUSALITY_IMPACT"],
	description:
		"Evaluates incoming conversations and intelligence streams for critical policy shifts, trade disruptions, and economic invariants.",
	schema: {
		type: "object",
		properties: {
			evaluated: { type: "boolean" },
			priority: { type: "string" },
			syncToAGrid: { type: "boolean" },
			timestamp: { type: "string" },
		},
		required: ["evaluated", "priority", "timestamp"],
	},
	async shouldRun(context: EvaluatorRunContext): Promise<boolean> {
		const text = (context.message?.content?.text || "").toLowerCase();
		return [
			"eudr",
			"mineral",
			"deforestation",
			"port congestion",
			"export ban",
			"strike",
			"power grid",
		].some((k) => text.includes(k));
	},
	prompt(context: EvaluatorPromptContext): string {
		const text = context.message?.content?.text || "";
		return `Assess economic truth invariant impact for: ${text}`;
	},
	processors: [
		{
			name: "cleanwebSignalRecorder",
			async process(_context) {
				return {
					success: true,
					data: {
						evaluated: true,
						priority: "HIGH_GROUND_TRUTH",
						syncToAGrid: true,
						timestamp: new Date().toISOString(),
					},
				};
			},
		},
	],
};
