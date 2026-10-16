import { Action, IAgentRuntime, Memory, State, HandlerCallback } from "@elizaos/core";
import Safe from "@safe-global/protocol-kit";
import { GuardedSafeExecutor } from "../GuardedSafeExecutor";
import { Address, Hex } from "viem";

export const executeGuardedOnchainAction: Action = {
  name: "EXECUTE_GUARDED_ONCHAIN_TX",
  similes: ["SEND_SAFE_TX", "SETTLE_ORACLE_ESCROW", "PAY_X402_RESOURCE"],
  description:
    "Executes an on-chain transaction via Safe{Wallet} protected by Security-Gate-x402 AST/DLP verification and EIP-712 proof-of-safety.",

  validate: async (runtime: IAgentRuntime, _message: Memory) => {
    return (
      Boolean(runtime.getSetting("SAFE_ADDRESS")) &&
      Boolean(runtime.getSetting("AGENT_SIGNER_PRIVATE_KEY"))
    );
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    _state?: State,
    options?: Record<string, unknown>,
    callback?: HandlerCallback
  ): Promise<any> => {
    try {
      const rpcUrl = String(runtime.getSetting("BASE_RPC_URL") || "https://mainnet.base.org");
      const safeAddress = String(runtime.getSetting("SAFE_ADDRESS") || "") as Address;
      const agentPrivateKey = String(runtime.getSetting("AGENT_SIGNER_PRIVATE_KEY") || "");
      const gateEndpoint = String(
        runtime.getSetting("SECURITY_GATE_URL") ||
        "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"
      );

      // Initialize Safe Protocol Kit
      const safeSdk = await Safe.init({
        provider: rpcUrl,
        signer: agentPrivateKey,
        safeAddress,
      });

      const executor = new GuardedSafeExecutor(safeSdk, gateEndpoint);

      const targetAddress = (options?.targetAddress as Address) || "0x0000000000000000000000000000000000000000";
      const valueWei = BigInt((options?.value as string) || "0");
      const calldata = ((options?.calldata as Hex) || "0x") as Hex;

      // Deterministic AST/DLP inspection + EIP-712 Signature Tail appending + Safe execution
      const txHash = await executor.executeGuardedTransaction(
        targetAddress,
        valueWei,
        calldata,
        {
          promptText: message.content?.text || "",
          requestedOptions: options,
        }
      );

      if (callback) {
        callback({
          text: `[Security-Gate-x402] Proof-of-Safety verified! Safe transaction executed on-chain. TxHash: ${txHash}`,
          content: { txHash, status: "GUARDED_SUCCESS" },
        });
      }
      return { success: true, txHash };
    } catch (error: any) {
      if (callback) {
        callback({
          text: `[Security-Gate-x402] Transaction blocked by on-chain/off-chain guard: ${error.message}`,
          content: { error: error.message, status: "BLOCKED_BY_GATE" },
        });
      }
      return { success: false, error: error.message };
    }
  },
  examples: [],
};
