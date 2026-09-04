# 🚀 Ready-to-Publish Launch Copy Package (X Thread & Reddit Showcase)

> **"The Spend Firewall for Autonomous Agents: Verified data in. Signed policy out. Every payment auditable on-chain."**
> Prepared by Claude Opus-5 & Antigravity Engineering Team

---

# 1. 🧵 Global X (Twitter) Launch Thread (English)

### TWEET 1 — Hook (Pain & Fear)
```text
Every agent framework ships with:

✅ rate limits
✅ token budgets
✅ retry logic
✅ tracing

None of them ship with:

❌ a hard cap on how much MONEY your agent can spend

That's not a feature gap. That's a missing layer. 🧵
```

### TWEET 2 — Solution (1-Line Middleware)
```text
The fix is one line.

Same spend firewall. LangGraph, CrewAI, AutoGen.

from app.spend_guard import spend_guard

# 1-Line Spend Firewall
guard = spend_guard(daily_limit="$10.00", per_tx="$2.00")
auth = guard.authorize_spend(0.05, context="Agent web search")

Deny by default.
Every allow/deny decision is signed with EIP-712 and logged.
Zero config, runs local or remote.
```

### TWEET 3 — Differentiator (402 Self-Onboarding)
```text
Now the part nobody else is doing.

Your agent hits a paid tool. Gets a 402.
It reads the _agentGuide response. Pays via USDC/Vault. Continues.

No signup form. No API key email.
No human in the loop at all.

Because agents can't fill out pricing pages.

And here's why the firewall matters:
the moment your agent CAN pay on its own, you need something that decides whether it SHOULD.
```

### TWEET 4 — Call to Action (CTA)
```text
The Spend Firewall for Autonomous Agents.

→ 60s to first call, no wallet, no signup
→ 3 sandbox calls free out of the box
→ LangGraph / CrewAI / AutoGen / MCP
→ Self-hostable & open source

Glama: https://glama.ai/mcp/servers/nohosa001-pixel/x402-cleanweb-agent
Repo: https://github.com/nohosa001-pixel/x402-cleanweb-agent
Security Gate: https://github.com/nohosa001-pixel/security-gate-x402
PyPI: pip install x402-cleanweb-agent
```

### TWEET 5 — Countering Objections (Pre-emptive FAQ)
```text
"Why not just a try/except and a counter?"

Because the counter lives inside the thing you're trying to constrain.

An agent that can execute code, spawn subagents, or get prompt-injected can route around in-process limits.

Enforcement has to sit outside the agent. That's the whole design.
```

---

# 2. 🤖 Reddit Showcase (r/mcp)

**Title:**
`MCP servers are starting to charge money. Nothing in the stack caps what your agent can spend.`

**Body:**
```markdown
**Disclosure up front: I'm one of the authors. Code and middleware are open source (MIT), links at the bottom.**

## The problem

Paid MCP servers are becoming normal — 402-gated tools, per-call pricing, metered data. Which means for the first time your agent's failure modes include "spent actual money."

Here's what the current stack protects you from:
- **token budgets** → protects the LLM bill
- **rate limits** → protects the *server*
- **retries/backoff** → makes runaway loops MORE persistent, not less
- **tracing** → tells you what happened *after* the bill arrives

Here's what nothing protects you from:
- a retry loop hammering a paid tool a few thousand times overnight
- a prompt injection in a fetched web page instructing the agent to pay something
- a tool whose `description` changes after install and starts requesting paid transactions
- a subagent that inherits the parent's payment authority with none of its constraints

None of these throw an exception. From the framework's perspective, everything succeeded.

## Why in-process counters aren't enough

The obvious answer is "wrap the tool call in a counter." It breaks in three places:
1. **The counter is inside the blast radius.** An agent executing code or prompt-injected can route around in-process limits.
2. **It doesn't compose.** Multi-framework setups (LangGraph orchestrating CrewAI workers) each keep their own counter. Nobody has the global ceiling.
3. **It doesn't survive restarts.** Crash-loop an agent and your daily counter resets.

So enforcement moved outside the agent, and every decision is an auditable EIP-712 cryptographic attestation instead of just a console log.

## The one-liner

```python
# 1-Line Spend Firewall for your agent
from app.spend_guard import spend_guard

guard = spend_guard(daily_limit="$10.00", per_tx="$2.00")

# Decorator or direct check
@spend_guard(daily_limit="$10.00", per_tx="$2.00")
def execute_agent_tool(query):
    ...
```

**Behavior:**
- **Deny by default** — unknown tools/payees are blocked immediately.
- **Unbounded loop auto-brake** — halts runaway recursive agent loops before budget drain.
- **Prompt injection guard** — pre-screens inputs for injection and secret key leak patterns.
- **Zero-human 402 self-onboarding** — returns machine-readable `_agentGuide` so agents can autonomously self-pay via USDC vaults or EIP-712 permits.

## Setup & Links

Remote MCP endpoint, ~60s to first call, no wallet and no account required for the free sandbox tier (3 free calls out of the box).

- **Glama Registry**: https://glama.ai/mcp/servers/nohosa001-pixel/x402-cleanweb-agent
- **CleanWeb Repo**: https://github.com/nohosa001-pixel/x402-cleanweb-agent
- **Security Gate Repo**: https://github.com/nohosa001-pixel/security-gate-x402
- **PyPI**: `pip install x402-cleanweb-agent`

Happy to get feedback on the threat model — especially from anyone running autonomous agents with tool access in production!
```
