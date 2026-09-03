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
