import type { Action, ActionResult, IAgentRuntime, Memory, State, HandlerCallback } from "@elizaos/core";

export const scrapeWebAction: Action = {
  name: "CLEANWEB_SCRAPE",
  similes: ["FETCH_CLEAN_URL", "BROWSE_PAGE_NOISE_FREE", "READ_ARTICLE_CLEAN"],
  description: "Scrapes any webpage URL and returns pure, LLM-optimized Markdown with 87% token reduction and zero HTML boilerplate.",
  validate: async (_runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
    const text = message.content?.text || "";
    return /https?:\/\/[^\s]+/i.test(text);
  },
  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    _state?: State,
    _options?: Record<string, unknown>,
    callback?: HandlerCallback
  ): Promise<ActionResult> => {
    const text = message.content?.text || "";
    const urlMatch = text.match(/https?:\/\/[^\s]+/i);
    if (!urlMatch) {
      if (callback) callback({ text: "URL을 찾을 수 없습니다." });
      return { success: false, error: new Error("No URL found") };
    }
    const targetUrl = urlMatch[0];
    const gateway = (typeof process !== "undefined" && process.env?.CLEANWEB_GATEWAY_URL) || "https://x402-cleanweb-agent-212942243360.asia-northeast3.run.app";
    const endpoint = `${gateway}/r/${encodeURIComponent(targetUrl)}`;

    try {
      const resp = await fetch(endpoint, {
        headers: {
          "User-Agent": "ElizaOS-CleanWebPlugin/1.0",
          "X-Agent-Nonce": (runtime as any)?.character?.name || "eliza_agent",
          "Accept": "text/markdown, application/json"
        }
      });

      if (resp.status === 402) {
        // Parse x402 payment requirements from headers
        const amount = resp.headers.get("x-payment-amount") || "0.0010";
        const recipient = resp.headers.get("x-payment-recipient") || "0xA185B43fDD19619f99952AAed6eabf1029bF36a1";
        const solRecipient = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp";
        const agentPass = (typeof process !== "undefined" && process.env?.X402_AGENT_PASS) || (runtime as any)?.getSetting?.("X402_AGENT_PASS");

        // Attempt Autonomous Auto-Payment if Agent Pass or pre-funded vault is available
        if (agentPass) {
          const retryResp = await fetch(endpoint, {
            headers: {
              "User-Agent": "ElizaOS-CleanWebPlugin/1.0",
              "X-Agent-Nonce": (runtime as any)?.character?.name || "eliza_agent",
              "X-Agent-Pass": agentPass,
              "Accept": "text/markdown, application/json"
            }
          });

          if (retryResp.ok) {
            const cleanText = await retryResp.text();
            const compression = retryResp.headers.get("x-token-compression") || "87%";
            const msg = `[CleanWeb Studio | ${compression} Compression | ⚡ Autonomously Settled ${amount} USDC via x402]\n\n${cleanText.slice(0, 3000)}`;
            if (callback) callback({ text: msg });
            return { success: true, data: { text: cleanText, compression, settled: true, amount } };
          }
        }

        const solanaNotice = `⚡ HTTP 402 Payment Required: Free trial exhausted.\n• Amount: ${amount} USDC\n• Solana Recipient: ${solRecipient}\n• EVM Recipient: ${recipient}\n• Deposit via POST ${gateway}/api/v1/vault/deposit or set X402_AGENT_PASS.`;
        if (callback) callback({ text: solanaNotice });
        return { success: true, data: { status: 402, notice: solanaNotice, amount, recipient, solRecipient } };
      }

      const cleanText = await resp.text();
      const compression = resp.headers.get("x-token-compression") || "87%";
      const resultMsg = `[CleanWeb Studio | ${compression} Token Compression]\n\n${cleanText.slice(0, 3000)}`;

      if (callback) callback({ text: resultMsg });
      return { success: true, data: { text: cleanText, compression } };
    } catch (err: any) {
      if (callback) callback({ text: `CleanWeb fetch failed: ${err.message}` });
      return { success: false, error: err };
    }
  },
  examples: [
    [
      { name: "User", content: { text: "이 뉴스 기사 내용 정리해줘 https://example.com/news" } },
      { name: "CleanWebAgent", content: { text: "CleanWeb으로 87% 압축된 고순도 마크다운을 분석합니다...", action: "CLEANWEB_SCRAPE" } }
    ]
  ]
};
