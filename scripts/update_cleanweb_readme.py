import re
from pathlib import Path

path = Path(r"c:\workspace\x402-micro-agent\README.md")
content = path.read_text(encoding="utf-8")

needle = """| **npm** | [**`cleanweb-eliza-plugin`**](https://www.npmjs.com/package/cleanweb-eliza-plugin) | **ElizaOS v2 Plugin (Solana x402 Micropayments & A.GRID Priority 0 Feed)** | `npm install cleanweb-eliza-plugin` |"""

addition = """| **npm** | [**`cleanweb-eliza-plugin`**](https://www.npmjs.com/package/cleanweb-eliza-plugin) | **ElizaOS v2 Plugin (Solana x402 Micropayments & A.GRID Priority 0 Feed)** | `npm install cleanweb-eliza-plugin` |
| **npm** | [**`elizaos-plugin-security-gate`**](https://www.npmjs.com/package/elizaos-plugin-security-gate) | **Security Gate & Polygon OMS Spend Firewall (Prompt-Injection Defense)** | `npm install elizaos-plugin-security-gate` |"""

guide_needle = """> 💡 **Full-Stack Hybrid Pattern (Recommended)**: Run `pip install x402-cleanweb-agent` on your backend/MCP host for local Dual-Core Security Gate + Eliza Brain scrubbing, and connect your TypeScript agents via `npm install agentkit-cleanweb` or `npm install cleanweb-eliza-plugin`."""

guide_replacement = """> 💡 **Full-Stack Zero-Trust Pattern (Recommended)**:
> 1. Use **`cleanweb-eliza-plugin`** (or `x402-cleanweb-agent`) for 87% token-compressed, ad-free web ground truth.
> 2. Guard outbound transactions and web payloads via **`elizaos-plugin-security-gate`** with **Polygon Open Money Stack (OMS) spend controls** (`SecurityGateOMSPolicy.sol` verified on Polygon: `0x4A28F9A2E6D0DcB69791980560FC8364A514f205`) and sub-second **Solana (`501`) settlements**."""

if needle in content:
    content = content.replace(needle, addition)
    if guide_needle in content:
        content = content.replace(guide_needle, guide_replacement)
    path.write_text(content, encoding="utf-8")
    print("SUCCESS: CleanWeb README updated with Security Gate & Polygon OMS integration!")
else:
    print("WARNING: needle not found")

