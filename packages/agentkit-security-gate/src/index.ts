/**
 * agentkit-security-gate
 * Official Coinbase AgentKit Action Provider for A.GRID Security Gate & Base Universal Escrow
 */

export interface SecurityGateAuditParams {
  jobId: number;
  deliverable: string;
  groundTruthSpec: string;
  isCode?: boolean;
}

export interface SecurityGateAuditResponse {
  verdict: "PASSED" | "REJECTED";
  riskScore: number;
  threats: string[];
  proofHash: string;
  attestation?: {
    jobId: number;
    verdict: string;
    expiresAt: number;
    signature: string;
  };
}

export const BASE_ESCROW_CORE = "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278" as const;
export const DEFAULT_SECURITY_GATE_API = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app";

/**
 * Audit an agent deliverable before initiating or settling an on-chain transfer.
 */
export async function auditDeliverable(
  params: SecurityGateAuditParams,
  gateUrl: string = DEFAULT_SECURITY_GATE_API
): Promise<SecurityGateAuditResponse> {
  const response = await fetch(`${gateUrl}/api/v1/escrow/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_id: params.jobId,
      deliverable: params.deliverable,
      ground_truth_spec: params.groundTruthSpec,
      is_code: params.isCode ?? false,
      chain_id: 8453,
      verifying_contract: BASE_ESCROW_CORE,
    }),
  });

  if (!response.ok) {
    throw new Error(`Security Gate API returned ${response.status}: ${await response.text()}`);
  }

  return (await response.json()) as SecurityGateAuditResponse;
}

/**
 * Prepares Base Mainnet Universal Escrow deposit with worker collateral.
 */
export function prepareBaseEscrowJob(
  jobId: number,
  workerAddress: `0x${string}`,
  amountUsdc: number,
  workerStakeBps: number = 1500
) {
  const amountRaw = BigInt(Math.round(amountUsdc * 1_000_000));
  const requiredStake = (amountRaw * BigInt(workerStakeBps)) / 10000n;
  const protocolFee = (amountRaw * 25n) / 10000n; // 0.25%

  return {
    contract: BASE_ESCROW_CORE,
    chainId: 8453,
    method: "createJob",
    args: [BigInt(jobId), workerAddress, amountRaw, requiredStake],
    feeSummary: {
      amountUsdc,
      workerStakeUsdc: Number(requiredStake) / 1_000_000,
      protocolFeeUsdc: Number(protocolFee) / 1_000_000,
    },
  };
}
