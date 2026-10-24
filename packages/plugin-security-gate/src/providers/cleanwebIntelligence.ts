import type { IAgentRuntime, Memory, Provider, ProviderResult, State } from "@elizaos/core";

export const cleanWebIntelligenceProvider: Provider = {
  name: "cleanweb-intelligence",
  description: "Provides CleanWeb token-compressed web intelligence and A.GRID oracle integration status.",
  get: async (_runtime: IAgentRuntime, _message?: Memory, _state?: State): Promise<ProviderResult> => {
    const gateway = (typeof process !== "undefined" && process.env?.CLEANWEB_GATEWAY_URL) || "https://x402-cleanweb-agent-212942243360.asia-northeast3.run.app";
    return {
      text: "CleanWeb & A.GRID Global Intelligence: 87% Token Reduced Web Scraping, EUDR & Critical Mineral Ground-Truth Invariants, Solana Mainnet 0.4s x402 Micropayments",
      data: {
        provider: "CleanWeb & A.GRID Global Intelligence",
        capabilities: [
          "87% Token Reduced Web Scraping",
          "EUDR & Critical Mineral Ground-Truth Invariants",
          "Solana Mainnet 0.4s x402 Micropayments",
          "Merkle Proof Cryptographic Verification"
        ],
        gatewayUrl: gateway,
        treasuryRecipient: "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp",
        tokenMint: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
      }
    };
  }
};
