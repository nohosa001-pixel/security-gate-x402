export const cleanWebIntelligenceProvider = {
  get: async (runtime: any, message: any, state: any) => {
    const gateway = process.env.CLEANWEB_GATEWAY_URL || "https://x402-cleanweb-agent-212942243360.asia-northeast3.run.app";
    return {
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
    };
  }
};
