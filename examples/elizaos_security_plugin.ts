/**
 * 🛡️ ElizaOS (ai16z) Security Gate Plugin & Evaluator
 * Package: @security-gate/eliza-plugin (or standalone action)
 *
 * Provides real-time micro-oracle inspection (<10ms) for ElizaOS agents
 * preventing jailbreaks, rogue prompt injections, and unauthorized treasury draining.
 *
 * Live Micro-Oracle API:
 *   https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/inspect
 */

declare const process: { env?: Record<string, string | undefined> } | undefined;

export interface SecurityGateConfig {
  gateUrl?: string;
  apiKey?: string;
  vaultKey?: string;
  strict?: boolean;
}

export interface InspectionResult {
  status: "PASSED" | "FLAGGED" | "BLOCKED";
  verdict: string;
  risk_score: number;
  threats: string[];
  audit_proof?: {
    proof_hash: string;
    terms: string;
    signature: string;
    issuer: string;
  };
}

export class SecurityGateEvaluator {
  private gateUrl: string;
  private apiKey?: string;
  private vaultKey?: string;
  private strict: boolean;

  constructor(config: SecurityGateConfig = {}) {
    const env = typeof process !== "undefined" && process?.env ? process.env : {};
    this.gateUrl = config.gateUrl || "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app";
    this.apiKey = config.apiKey || env.AGENT_API_KEY;
    this.vaultKey = config.vaultKey || env.AGENT_VAULT_KEY;
    this.strict = config.strict !== undefined ? config.strict : true;
  }

  /**
   * Inspects agent response or proposed transaction before execution.
   */
  async inspect(agentOutput: string, contextGroundTruth?: string, isCode = false): Promise<InspectionResult> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.vaultKey) {
      headers["X-Vault-Key"] = this.vaultKey;
    } else if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }

    const payload = {
      agent_output: agentOutput,
      context_ground_truth: contextGroundTruth || null,
      is_code: isCode,
      raise_on_block: false,
    };

    const response = await fetch(`${this.gateUrl}/api/v1/inspect`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (response.status === 402) {
      const challenge = await response.json();
      throw new Error(`[402 Payment Required] x402 Micropayment required: ${JSON.stringify(challenge)}`);
    }

    if (!response.ok) {
      throw new Error(`Security Gate API returned error HTTP ${response.status}`);
    }

    const data = await response.json();
    const audit = data.audit || {};
    const result: InspectionResult = {
      status: audit.verdict === "BLOCK" ? "BLOCKED" : audit.verdict === "WARN" ? "FLAGGED" : "PASSED",
      verdict: audit.verdict || "ALLOW",
      risk_score: audit.risk_score || 0,
      threats: audit.threats || [],
      audit_proof: data.audit_proof,
    };

    if (this.strict && result.status === "BLOCKED") {
      throw new Error(`🚨 [Security Gate Blocked] Threat Detected: ${result.threats.join(", ")} (Risk: ${result.risk_score}%)`);
    }

    return result;
  }
}

// -----------------------------------------------------------------------------
// 🌟 ElizaOS Action / Plugin Wrapper Example
// -----------------------------------------------------------------------------
export const securityGatePlugin = {
  name: "security-gate-guard",
  description: "Protects autonomous ElizaOS agents from prompt injection and budget exhaustion.",
  evaluator: new SecurityGateEvaluator(),

  /**
   * Example handler intercepting an Eliza trade/swap action
   */
  async beforeAction(actionName: string, actionParams: Record<string, unknown>): Promise<boolean> {
    const summary = `Action: ${actionName} | Params: ${JSON.stringify(actionParams)}`;
    const check = await this.evaluator.inspect(summary);
    return check.status === "PASSED";
  },
};
