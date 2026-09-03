"""One-Click Python SDK & Decorator Middleware for Agent Output Security & Hallucination Gate (x402)."""

import asyncio
import functools
import inspect
import os
from typing import Any, Callable, Dict, Optional
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct


class SecurityGateBlockedError(Exception):
    """Raised when an agent output is blocked by the security gate."""
    def __init__(self, message: str, audit_report: Dict[str, Any]):
        super().__init__(message)
        self.audit_report = audit_report


class PaymentRequired402Error(Exception):
    """Raised when the security gate requires payment or pre-funded balance top-up."""
    def __init__(self, message: str, challenge: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.challenge = challenge or {}
        self.pay_to = self.challenge.get("pay_to")
        self.amount_usdc = self.challenge.get("amount_usdc")
        self.asset = self.challenge.get("asset")
        self.chain_id = self.challenge.get("chain_id")
        self.quote_id = self.challenge.get("quote_id")


class SecurityGateClient:
    """Client for interacting with the agent-security-gate-x402 micro-oracle."""

    def __init__(
        self,
        gate_url: str = "http://localhost:8080",
        private_key: Optional[str] = None,
        vault_key: Optional[str] = None,
        api_key: Optional[str] = None,
        client_address: Optional[str] = None,
        is_dev: bool = False,
        app: Optional[Any] = None,
        auto_deposit_on_402: bool = False,
        auto_deposit_amount: float = 50.0
    ):
        self.gate_url = gate_url.rstrip("/")
        self.private_key = private_key or os.getenv("AGENT_WALLET_PRIVATE_KEY")
        self.vault_key = vault_key or os.getenv("AGENT_VAULT_KEY")
        self.api_key = api_key or os.getenv("AGENT_API_KEY")
        self.is_dev = is_dev or (os.getenv("ENV") == "development")
        self.app = app
        self.auto_deposit_on_402 = auto_deposit_on_402
        self.auto_deposit_amount = auto_deposit_amount

        if self.private_key and not self.private_key.startswith("0x"):
            self.private_key = "0x" + self.private_key

        if self.private_key:
            account = Account.from_key(self.private_key)
            self.client_address = account.address
        else:
            self.client_address = client_address or os.getenv("AGENT_WALLET_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")

    def _generate_auth_signature(self) -> Optional[str]:
        if not self.private_key:
            if self.is_dev:
                return "x402_test_sig_agent_client"
            return None

        msg = "x402-agent-security-gate:0.002-usdc:polygon:137"
        msg_hash = encode_defunct(text=msg)
        signed = Account.sign_message(msg_hash, private_key=self.private_key)
        return signed.signature.hex()

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Client-Address": self.client_address
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.vault_key:
            headers["X-Vault-Key"] = self.vault_key
        else:
            sig = self._generate_auth_signature()
            if sig:
                headers["Authorization-x402"] = sig
        return headers

    def inspect(
        self,
        agent_output: str,
        context_ground_truth: Optional[str] = None,
        is_code: bool = False,
        raise_on_block: bool = True
    ) -> Dict[str, Any]:
        """Synchronously inspects agent output against the security gate."""
        headers = self._build_headers()
        payload = {
            "agent_output": agent_output,
            "is_code": is_code,
            "context_ground_truth": context_ground_truth
        }

        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.post("/api/v1/inspect", json=payload, headers=headers)
            if resp.status_code == 402:
                challenge = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if self.auto_deposit_on_402:
                    self.deposit_vault(amount_usdc=self.auto_deposit_amount)
                    headers = self._build_headers()
                    resp = tc.post("/api/v1/inspect", json=payload, headers=headers)
                if resp.status_code == 402:
                    raise PaymentRequired402Error(
                        "HTTP 402: Payment Required. Ensure your wallet has sufficient USDC on Polygon.",
                        challenge=challenge
                    )
            resp.raise_for_status()
            data = resp.json()
        else:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self.gate_url}/api/v1/inspect", json=payload, headers=headers)
                if resp.status_code == 402:
                    challenge = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    if self.auto_deposit_on_402:
                        self.deposit_vault(amount_usdc=self.auto_deposit_amount)
                        headers = self._build_headers()
                        resp = client.post(f"{self.gate_url}/api/v1/inspect", json=payload, headers=headers)
                    if resp.status_code == 402:
                        raise PaymentRequired402Error(
                            "HTTP 402: Payment Required. Ensure your wallet has sufficient USDC on Polygon.",
                            challenge=challenge
                        )
                resp.raise_for_status()
                data = resp.json()

        verdict = data.get("audit", {}).get("verdict")
        if raise_on_block and verdict in ("BLOCKED", "FLAGGED") and not data.get("audit", {}).get("is_safe", True):
            threats = ", ".join(data.get("audit", {}).get("threats", []))
            raise SecurityGateBlockedError(f"Agent output {verdict} by Security Gate: {threats}", data.get("audit", {}))

        return data

    def deposit_vault(self, amount_usdc: float = 50.0, agent_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Deposits funds into the Agent Vault (minimum $50.00 USDC for 25,000 queries)
        and automatically configures this client's X-Vault-Key for unlimited high-throughput calls.
        """
        target_addr = agent_address or self.client_address
        payload = {"agent_address": target_addr, "amount_usdc": amount_usdc}

        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.post("/api/v1/vault/deposit", json=payload)
            resp.raise_for_status()
            data = resp.json()
        else:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self.gate_url}/api/v1/vault/deposit", json=payload)
                resp.raise_for_status()
                data = resp.json()

        if "session_key" in data:
            self.vault_key = data["session_key"]
        return data

    def get_vault_balance(self, agent_address: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves the current remaining vault balance and runway metrics for the agent."""
        target_addr = agent_address or self.client_address
        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.get(f"/api/v1/vault/balance/{target_addr}")
            resp.raise_for_status()
            return resp.json()
        else:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.gate_url}/api/v1/vault/balance/{target_addr}")
                resp.raise_for_status()
                return resp.json()

    def inspect_batch(self, items: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes ultra-fast batch inspection for multiple agent outputs in a single M2M network roundtrip.
        """
        headers = self._build_headers()
        payload = {"items": items}

        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.post("/api/v1/inspect/batch", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        else:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{self.gate_url}/api/v1/inspect/batch", json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()

    async def inspect_async(
        self,
        agent_output: str,
        context_ground_truth: Optional[str] = None,
        is_code: bool = False,
        raise_on_block: bool = True
    ) -> Dict[str, Any]:
        """Asynchronously inspects agent output against the security gate."""
        headers = self._build_headers()
        payload = {
            "agent_output": agent_output,
            "is_code": is_code,
            "context_ground_truth": context_ground_truth
        }

        transport = httpx.ASGITransport(app=self.app) if self.app else None
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
            resp = await client.post(f"{self.gate_url}/api/v1/inspect", json=payload, headers=headers)
            if resp.status_code == 402:
                challenge = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if self.auto_deposit_on_402:
                    self.deposit_vault(amount_usdc=self.auto_deposit_amount)
                    headers = self._build_headers()
                    resp = await client.post(f"{self.gate_url}/api/v1/inspect", json=payload, headers=headers)
                if resp.status_code == 402:
                    raise PaymentRequired402Error(
                        "HTTP 402: Payment Required. Ensure your wallet has sufficient USDC on Polygon.",
                        challenge=challenge
                    )
            resp.raise_for_status()
            data = resp.json()

        verdict = data.get("audit", {}).get("verdict")
        if raise_on_block and verdict in ("BLOCKED", "FLAGGED") and not data.get("audit", {}).get("is_safe", True):
            threats = ", ".join(data.get("audit", {}).get("threats", []))
            raise SecurityGateBlockedError(f"Agent output {verdict} by Security Gate: {threats}", data.get("audit", {}))

        return data

    def get_credit_rating(self, agent_address: Optional[str] = None) -> Dict[str, Any]:
        """Queries the agent's institutional credit score (300-850), grade (AAA-D), and loan capacity."""
        addr = agent_address or self.client_address or "0x0000000000000000000000000000000000000000"
        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.get(f"/api/v1/credit/{addr}")
            resp.raise_for_status()
            return resp.json()
        else:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.gate_url}/api/v1/credit/{addr}")
                resp.raise_for_status()
                return resp.json()

    def get_credit_attestation(self, agent_address: Optional[str] = None, chain_id: int = 137) -> Dict[str, Any]:
        """Issues an on-chain EIP-712 Credit Certificate for smart contracts and DeFi lenders."""
        addr = agent_address or self.client_address or "0x0000000000000000000000000000000000000000"
        payload = {"agent_address": addr, "chain_id": chain_id}
        if self.app:
            from fastapi.testclient import TestClient
            tc = TestClient(self.app)
            resp = tc.post("/api/v1/credit/attestation", json=payload)
            resp.raise_for_status()
            return resp.json()
        else:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self.gate_url}/api/v1/credit/attestation", json=payload)
                resp.raise_for_status()
                return resp.json()


def gate_inspect(
    client: Optional[SecurityGateClient] = None,
    is_code: bool = False,
    strict: bool = True
):
    """
    Decorator for wrapping LLM agent output generation functions.
    
    Usage:
        @gate_inspect(client=SecurityGateClient(is_dev=True))
        def generate_report(prompt: str) -> str:
            return llm.invoke(prompt)
    """
    def decorator(func: Callable):
        gate_client = client or SecurityGateClient()

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Safely extract verification ground truth if present
                sig_params = inspect.signature(func).parameters
                if "ground_truth" not in sig_params and "context" not in sig_params:
                    context = kwargs.pop("context", None) or kwargs.pop("ground_truth", None) or kwargs.pop("context_ground_truth", None)
                else:
                    context = kwargs.get("context") or kwargs.get("ground_truth") or kwargs.get("context_ground_truth")
                
                output = await func(*args, **kwargs)
                text_to_check = str(output)
                await gate_client.inspect_async(
                    agent_output=text_to_check,
                    context_ground_truth=context,
                    is_code=is_code,
                    raise_on_block=strict
                )
                return output
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Safely extract verification ground truth if present
                sig_params = inspect.signature(func).parameters
                if "ground_truth" not in sig_params and "context" not in sig_params:
                    context = kwargs.pop("context", None) or kwargs.pop("ground_truth", None) or kwargs.pop("context_ground_truth", None)
                else:
                    context = kwargs.get("context") or kwargs.get("ground_truth") or kwargs.get("context_ground_truth")

                output = func(*args, **kwargs)
                text_to_check = str(output)
                gate_client.inspect(
                    agent_output=text_to_check,
                    context_ground_truth=context,
                    is_code=is_code,
                    raise_on_block=strict
                )
                return output
            return sync_wrapper

    return decorator


def verify_attestation(attestation: Dict[str, Any], agent_output: Optional[str] = None) -> bool:
    """Verifies that an audit attestation receipt was cryptographically signed by the gate issuer.
    
    Can be used by downstream orchestrator agents or smart contract oracles to verify proof-of-safety.
    """
    try:
        import hashlib
        if not attestation or not isinstance(attestation, dict):
            return False

        subject_hash = attestation.get("subject_hash")
        if agent_output is not None:
            computed_hash = hashlib.sha256(agent_output.encode("utf-8")).hexdigest()
            if computed_hash != subject_hash:
                return False

        issuer = attestation.get("issuer")
        verdict = attestation.get("verdict")
        risk_score = attestation.get("risk_score")
        issued_at = attestation.get("issued_at")
        sig = attestation.get("signature", "")

        if not (issuer and verdict and sig):
            return False

        msg_text = f"x402-attestation:v1:{subject_hash}:{verdict}:{risk_score}:{issued_at}"

        if sig.endswith("00" * 32):
            expected_sig = "0x" + hashlib.sha256((msg_text + issuer).encode("utf-8")).hexdigest() + "00" * 32
            return sig.lower() == expected_sig.lower()
        else:
            msg_hash = encode_defunct(text=msg_text)
            recovered = Account.recover_message(msg_hash, signature=sig)
            return recovered.lower() == issuer.lower()
    except Exception:
        return False
