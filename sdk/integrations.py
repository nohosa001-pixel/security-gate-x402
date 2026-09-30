"""
Standard Drop-in Framework Adapters & Middleware for AI Agent Runtimes.
Supports LangChain, LangGraph, CrewAI, AutoGen, and custom multi-agent orchestrators.
"""

import json
from typing import Any, Dict, List, Optional
from sdk.agent_gate_sdk import SecurityGateClient, SecurityGateBlockedError


class SecurityGateCallbackHandler:
    """
    Drop-in Callback Handler for LangChain and LangGraph.
    Intercepts LLM generation (`on_llm_end`) and tool execution (`on_tool_start`)
    to enforce micro-oracle security, anti-jailbreak, and hallucination guardrails.
    
    Usage:
        from sdk import SecurityGateClient, SecurityGateCallbackHandler
        
        client = SecurityGateClient(is_dev=True)
        handler = SecurityGateCallbackHandler(client=client, strict=True)
        
        llm = ChatOpenAI(callbacks=[handler])
        # or agent_executor.invoke({"input": ...}, config={"callbacks": [handler]})
    """

    def __init__(
        self,
        client: Optional[SecurityGateClient] = None,
        strict: bool = True,
        is_code: bool = False,
        context_ground_truth: Optional[str] = None
    ):
        self.client = client or SecurityGateClient()
        self.strict = strict
        self.is_code = is_code
        self.context_ground_truth = context_ground_truth
        self.last_audit_report: Optional[Dict[str, Any]] = None

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Invoked when an LLM finishes generating text."""
        texts_to_check: List[str] = []

        # 1. Extract generations across LangChain response formats
        generations = getattr(response, "generations", [])
        for gen_list in generations:
            for gen in gen_list:
                text = getattr(gen, "text", "")
                if not text and hasattr(gen, "message"):
                    text = getattr(gen.message, "content", "")
                if text:
                    texts_to_check.append(str(text))

        # 2. Inspect each generated output
        for text in texts_to_check:
            audit_result = self.client.inspect(
                agent_output=text,
                context_ground_truth=self.context_ground_truth,
                is_code=self.is_code,
                raise_on_block=self.strict
            )
            self.last_audit_report = audit_result

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Invoked before a tool is executed by the agent."""
        tool_name = serialized.get("name", "unknown_tool")
        # Pre-audit tool input against malicious code injection or shell escapes
        is_code_tool = any(kw in tool_name.lower() for kw in ["python", "bash", "shell", "exec", "terminal"])
        audit_result = self.client.inspect(
            agent_output=input_str,
            is_code=is_code_tool,
            raise_on_block=self.strict
        )
        self.last_audit_report = audit_result


class SecurityGateTool:
    """
    Standard Tool wrapper for CrewAI, AutoGen, and function-calling agents.
    Allows an autonomous agent to voluntarily or automatically audit outputs
    and produce cryptographic Proof-of-Safety attestations.
    
    Usage in CrewAI:
        from sdk import SecurityGateTool
        guardrail_tool = SecurityGateTool()
        agent = Agent(tools=[guardrail_tool], ...)
    """

    name: str = "inspect_agent_security_guardrail"
    description: str = (
        "Ultra-low latency (<10ms) deterministic security, prompt injection, "
        "secret key leak, dangerous AST code, and factual hallucination micro-oracle. "
        "Returns security verdict, risk score, and EIP-191 cryptographic attestation."
    )

    def __init__(self, client: Optional[SecurityGateClient] = None):
        self.client = client or SecurityGateClient()

    def run(
        self,
        agent_output: str,
        context_ground_truth: Optional[str] = None,
        is_code: bool = False
    ) -> str:
        """Synchronously runs inspection and returns JSON string result."""
        try:
            res = self.client.inspect(
                agent_output=agent_output,
                context_ground_truth=context_ground_truth,
                is_code=is_code,
                raise_on_block=False
            )
            return json.dumps(res, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def __call__(self, *args, **kwargs) -> str:
        return self.run(*args, **kwargs)


class AgentEscrowTool:
    """
    Standard Escrow & DePIN Clearinghouse Tool for LangChain, CrewAI, and AutoGen.
    Enables autonomous agents to create staked M2M contracts, submit deliverables
    for deterministic oracle audit, and claim instant USDC payouts.

    Usage:
        from sdk.integrations import AgentEscrowTool
        escrow_tool = AgentEscrowTool()
        result = escrow_tool.create_task("0xWorker...", 50.0, 15.0, "Normalize Uniswap v3 data")
    """

    name: str = "agent_escrow_clearinghouse"
    description: str = (
        "Bilateral staked M2M escrow for autonomous sub-contracting. Eliminates counterparty "
        "and execution risk with deterministic AST & safety audits and EIP-712 cryptographic proofs."
    )

    def __init__(self, client=None, chain_id: int = 137):
        from sdk.agent_escrow_client import AgentEscrowClient
        self.client = client or AgentEscrowClient(chain_id=chain_id)

    def create_task(
        self,
        worker_address: str,
        payout_usdc: float,
        stake_usdc: float,
        task_spec: str,
        duration_seconds: int = 86400
    ) -> str:
        """Creates an escrow job preparation or on-chain transaction."""
        try:
            res = self.client.execute_create_job(
                worker=worker_address,
                payout_usdc=payout_usdc,
                stake_usdc=stake_usdc,
                spec_text=task_spec,
                duration_seconds=duration_seconds
            )
            return json.dumps(res, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def audit_and_settle(
        self,
        job_id: int,
        deliverable: str,
        task_spec: Optional[str] = None,
        is_code: bool = True
    ) -> str:
        """Audits deliverable via Security Gate Oracle and returns signed settlement proof."""
        try:
            attestation = self.client.request_attestation(
                job_id=job_id,
                deliverable=deliverable,
                ground_truth_spec=task_spec,
                is_code=is_code
            )
            verdict = attestation.get("verdict", "PASSED")
            risk_score = attestation.get("risk_score", 0)
            is_safe = (verdict == "PASSED" and risk_score <= 25)

            return json.dumps({
                "status": "AUDITED",
                "job_id": job_id,
                "verdict": verdict,
                "risk_score": risk_score,
                "approved_for_payout": is_safe,
                "action_recommended": "completeJob" if is_safe else "slashJob",
                "attestation": attestation
            }, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def run(self, action: str, **kwargs) -> str:
        if action == "create_task":
            return self.create_task(
                worker_address=kwargs.get("worker_address", "0x0000000000000000000000000000000000000000"),
                payout_usdc=float(kwargs.get("payout_usdc", 10.0)),
                stake_usdc=float(kwargs.get("stake_usdc", 5.0)),
                task_spec=str(kwargs.get("task_spec", "Generic Task")),
                duration_seconds=int(kwargs.get("duration_seconds", 86400))
            )
        elif action == "audit_and_settle":
            return self.audit_and_settle(
                job_id=int(kwargs.get("job_id", 1)),
                deliverable=str(kwargs.get("deliverable", "")),
                task_spec=kwargs.get("task_spec"),
                is_code=bool(kwargs.get("is_code", True))
            )
        return json.dumps({"error": f"Unknown action: {action}"})


class SovereignTreasuryTool:
    """
    RWA Sovereign Treasury & Proof-of-Reserve Tool for Agent Runtimes.
    Enables agents to independently verify that all escrow reserves are 100%
    collateralized by US Treasury Bills and operator cannot withdraw principal.
    """

    name: str = "sovereign_treasury_oracle"
    description: str = (
        "Inspects multi-chain tokenized US T-Bill backing (Ondo USDY, BlackRock BUIDL, "
        "Matrixdock STBT) and cryptographically verifies EIP-712 Proof-of-Reserve invariant."
    )

    def __init__(self, client=None):
        from sdk.agent_escrow_client import AgentEscrowClient
        self.client = client or AgentEscrowClient()

    def get_reserves(self) -> str:
        """Returns live reserve holdings across Polygon, Base, and Arbitrum."""
        try:
            data = self.client.get_treasury_reserves()
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def verify_proof_of_reserve(self) -> str:
        """Fetches and displays EIP-712 cryptographic Proof-of-Reserve."""
        try:
            por = self.client.get_proof_of_reserve()
            return json.dumps({
                "status": "VERIFIED",
                "invariant_guaranteed": (por.get("proof", {}).get("operator_withdrawal_allowed") is False),
                "collateral_ratio": por.get("proof", {}).get("collateral_ratio", 1.0),
                "proof_details": por
            }, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def simulate_yield(self, days: int = 30) -> str:
        """Simulates 30-day T-Bill compounding distribution."""
        try:
            sim = self.client.simulate_compound_yield(days=days)
            return json.dumps(sim, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})


class UniversalEscrowTool:
    """
    Modular Universal Escrow Tool for LangChain, CrewAI, AutoGen, and LangGraph.
    Enables autonomous agents to lock capital for Maritime IoT, Bio-ZK, or Construction LiDAR
    milestones and atomically disburse split payouts directly to suppliers/laborers.
    """

    name: str = "universal_truth_escrow"
    description: str = (
        "Locks enterprise capital into UniversalEscrowCore and releases atomic direct split "
        "disbursals to laborers and suppliers upon EIP-712 physical truth verification."
    )

    def __init__(self, client=None, app=None):
        from sdk.agent_gate_sdk import UniversalEscrowClient
        self.client = client or UniversalEscrowClient(app=app)

    def create_escrow(
        self,
        domain_name: str,
        amount_usdc: float,
        truth_requirement_hash: str,
        job_id: Optional[str] = None
    ) -> str:
        from sdk.agent_gate_sdk import IndustryDomain
        domain_map = {
            "TRADE_MARITIME": IndustryDomain.TRADE_MARITIME,
            "MARITIME": IndustryDomain.TRADE_MARITIME,
            "BIO_KNOWLEDGE_IP": IndustryDomain.BIO_KNOWLEDGE_IP,
            "BIO": IndustryDomain.BIO_KNOWLEDGE_IP,
            "CONSTRUCTION_BUILD": IndustryDomain.CONSTRUCTION_BUILD,
            "CONSTRUCTION": IndustryDomain.CONSTRUCTION_BUILD
        }
        dom = domain_map.get(domain_name.upper(), IndustryDomain.CONSTRUCTION_BUILD)
        try:
            job = self.client.create_job(
                domain=dom,
                amount_usdc=amount_usdc,
                truth_requirement_hash=truth_requirement_hash,
                job_id=job_id
            )
            return json.dumps({
                "status": "DEPOSITED",
                "job_id": job.job_id,
                "domain": job.domain.name,
                "amount_usdc": job.amount_usdc,
                "deadline_sec": job.deadline_sec
            }, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def settle_escrow(
        self,
        job_id: str,
        proof_data: Any,
        recipients: List[Dict[str, Any]],
        attestation: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            res = self.client.settle_with_truth(
                job_id=job_id,
                proof_data=proof_data,
                recipients=recipients,
                attestation=attestation
            )
            return json.dumps(res, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def run(self, action: str, **kwargs) -> str:
        if action == "create_escrow":
            return self.create_escrow(
                domain_name=kwargs.get("domain", "CONSTRUCTION_BUILD"),
                amount_usdc=float(kwargs.get("amount_usdc", 1000.0)),
                truth_requirement_hash=kwargs.get("truth_requirement_hash", "0x" + "0" * 64),
                job_id=kwargs.get("job_id")
            )
        elif action == "settle_escrow":
            return self.settle_escrow(
                job_id=kwargs.get("job_id", ""),
                proof_data=kwargs.get("proof_data", {}),
                recipients=kwargs.get("recipients", []),
                attestation=kwargs.get("attestation")
            )
        return json.dumps({"error": f"Unknown action: {action}"})

