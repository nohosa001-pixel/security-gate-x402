import Safe from "@safe-global/protocol-kit";
import {
  encodeAbiParameters,
  parseAbiParameters,
  concatHex,
  keccak256,
  encodePacked,
  Hex,
  Address,
} from "viem";

// ============================================================================
// 1. Type Definitions (1:1 mapping with Solidity SafetyAttestation struct)
// ============================================================================

export interface SafetyAttestation {
  payloadHash: Hex;
  agentWallet: Address;
  targetAddress: Address;
  maxAllowedSpend: bigint;
  expiry: bigint;
  riskScore: number;
  nonce: Hex;
}

export interface GateAttestationResponse {
  attestation: SafetyAttestation;
  signature: Hex; // 65-byte EIP-712 signature from security-gate-x402
}

// ============================================================================
// 2. Signature Tail Encoder & Guarded Safe Transaction Engine
// ============================================================================

export class GuardedSafeExecutor {
  private safeSdk: Safe;
  private gateApiUrl: string;
  private sessionVoucherHeader?: string;

  constructor(safeSdk: Safe, gateApiUrl: string = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app") {
    this.safeSdk = safeSdk;
    this.gateApiUrl = gateApiUrl;
  }

  /**
   * Set pre-signed cumulative voucher header for zero-gas session billing.
   */
  public setSessionVoucher(voucherJson: string): void {
    this.sessionVoucherHeader = voucherJson;
  }

  /**
   * Generates payload hash matching Solidity keccak256(abi.encodePacked(to, value, data)).
   */
  public computePayloadHash(to: Address, value: bigint, data: Hex): Hex {
    return keccak256(
      encodePacked(["address", "uint256", "bytes"], [to, value, data])
    );
  }

  /**
   * Step 1: Request AST/DLP inspection and EIP-712 proof from security-gate-x402.
   */
  public async requestGateAttestation(
    to: Address,
    value: bigint,
    data: Hex,
    toolContext?: Record<string, unknown>
  ): Promise<GateAttestationResponse> {
    const safeAddress = (await this.safeSdk.getAddress()) as Address;
    const payloadHash = this.computePayloadHash(to, value, data);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.sessionVoucherHeader) {
      headers["X-402-Voucher"] = this.sessionVoucherHeader;
    }

    const res = await fetch(`${this.gateApiUrl}/api/v1/escrow/audit`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        job_id: 1,
        deliverable: JSON.stringify({
          agentWallet: safeAddress,
          targetAddress: to,
          value: value.toString(),
          calldata: data,
          payloadHash,
          toolContext,
        }),
        ground_truth_spec: "Deterministic AST & DLP verification with bounded wallet",
        is_code: false,
        chain_id: 8453,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`[SecurityGate Blocked] Status ${res.status}: ${errText}`);
    }

    const raw = await res.json();
    const att = raw.attestation || {};

    return {
      attestation: {
        payloadHash: (att.payloadHash || payloadHash) as Hex,
        agentWallet: (att.agentWallet || safeAddress) as Address,
        targetAddress: (att.targetAddress || to) as Address,
        maxAllowedSpend: BigInt(att.maxAllowedSpend || value.toString()),
        expiry: BigInt(att.expiry || Math.floor(Date.now() / 1000) + 300),
        riskScore: Number(att.riskScore || 0),
        nonce: (att.nonce || "0x" + "00".repeat(32)) as Hex,
      },
      signature: (att.signature || raw.proof_hash || "0x") as Hex,
    };
  }

  /**
   * Step 2: Encodes (SafetyAttestation, gateSignature) to match Solidity abi.decode(gateBundle, (SafetyAttestation, bytes)).
   */
  public encodeGateTail(
    attestation: SafetyAttestation,
    gateSignature: Hex
  ): Hex {
    const abiParams = parseAbiParameters(
      "(bytes32 payloadHash, address agentWallet, address targetAddress, uint256 maxAllowedSpend, uint256 expiry, uint8 riskScore, bytes32 nonce), bytes"
    );

    return encodeAbiParameters(abiParams, [
      {
        payloadHash: attestation.payloadHash,
        agentWallet: attestation.agentWallet,
        targetAddress: attestation.targetAddress,
        maxAllowedSpend: attestation.maxAllowedSpend,
        expiry: attestation.expiry,
        riskScore: attestation.riskScore,
        nonce: attestation.nonce,
      },
      gateSignature,
    ]);
  }

  /**
   * Step 3: Concat Safe owner signature (65 bytes) + Gate Tail bundle and execute via Safe contract.
   */
  public async executeGuardedTransaction(
    to: Address,
    value: bigint,
    data: Hex,
    toolContext?: Record<string, unknown>
  ): Promise<string> {
    // 1. Fetch deterministic Security Gate EIP-712 proof
    const { attestation, signature: gateSig } =
      await this.requestGateAttestation(to, value, data, toolContext);

    // 2. Build standard Safe transaction and sign with agent private key
    const safeTransaction = await this.safeSdk.createTransaction({
      transactions: [
        {
          to,
          value: value.toString(),
          data,
          operation: 0, // EnumOperation.Call fixed (DelegateCall blocked by Guard)
        },
      ],
    });

    const signedSafeTx = await this.safeSdk.signTransaction(safeTransaction);
    const ownerSigBytes = signedSafeTx.encodedSignatures() as Hex;

    // 3. Append Gate Tail bundle to Safe owner signature
    const gateTailHex = this.encodeGateTail(attestation, gateSig);
    const combinedSignatures = concatHex([ownerSigBytes, gateTailHex]);

    // 4. Submit directly to Safe contract execTransaction
    const contractManager = await this.safeSdk.getContractManager();
    const safeContract = contractManager.safeContract as any;
    if (!safeContract) throw new Error("Safe contract instance not initialized");

    const txData = safeTransaction.data;
    const txResponse = await safeContract.execTransaction(
      txData.to,
      txData.value,
      txData.data,
      txData.operation,
      txData.safeTxGas,
      txData.baseGas,
      txData.gasPrice,
      txData.gasToken,
      txData.refundReceiver,
      combinedSignatures
    );

    return txResponse.hash || txResponse;
  }
}
