"""Deterministic, ultra-low latency (<10ms) security and hallucination inspection engine."""

import ast
from datetime import datetime, timezone
import re
import time
from typing import Any, Dict, List, Optional, Set

from app.schemas import (
    AuditReport,
    InspectionRequest,
    InspectionResponse,
    NLIReport,
)

INJECTION_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"system\s*:\s*override",
    r"as\s+an\s+unfiltered\s+ai",
    r"base64\.b64decode\(",
    r"__import__\(['\"]os['\"]\)",
    r"eval\(|exec\(|subprocess\.Popen",
    r"you\s+are\s+now\s+DAN",
    r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]"
]

SECRET_PATTERNS = [
    r"0x[a-fA-F0-9]{64}",            # EVM 32-Byte Private Key
    r"sk-[a-zA-Z0-9]{32,}",          # OpenAI / LLM API Key
    r"sk-proj-[a-zA-Z0-9_-]{40,}",   # OpenAI Project Key
    r"sk-ant-[a-zA-Z0-9_-]{32,}",    # Anthropic API Key
    r"ghp_[a-zA-Z0-9]{36}",          # GitHub Personal Access Token
    r"AKIA[0-9A-Z]{16}",             # AWS Access Key ID
    r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----"  # Private Key Block
]


def extract_numbers_and_units(text: str) -> Set[str]:
    normalized = re.sub(r'(?<=\d),(?=\d)', '', text)
    pattern = r'[\$€₩¥]?\s*-?\d+(?:\.\d+)?%?'
    matches = re.findall(pattern, normalized)
    return {m.strip() for m in matches if any(c.isdigit() for c in m)}


def extract_entities_and_keywords(text: str) -> Set[str]:
    words = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+\b|[가-힣]{2,}', text)
    return {w.lower() for w in words}


def compute_lightweight_nli_faithfulness(agent_output: str, context_ground_truth: str) -> Dict[str, Any]:
    gt_numbers = extract_numbers_and_units(context_ground_truth)
    out_numbers = extract_numbers_and_units(agent_output)

    fabricated_numbers = list(out_numbers - gt_numbers)
    num_hallucination_penalty = len(fabricated_numbers) * 25.0

    gt_entities = extract_entities_and_keywords(context_ground_truth)
    out_entities = extract_entities_and_keywords(agent_output)
    
    if out_entities:
        ungrounded_entities = list(out_entities - gt_entities)
        entity_precision = (len(out_entities) - len(ungrounded_entities)) / len(out_entities)
    else:
        ungrounded_entities = []
        entity_precision = 1.0

    gt_tokens = set(context_ground_truth.lower().split())
    out_tokens = set(agent_output.lower().split())
    overlap_count = len(out_tokens.intersection(gt_tokens))
    faithfulness_ratio = overlap_count / max(len(out_tokens), 1)

    hallucination_score = num_hallucination_penalty + ((1.0 - entity_precision) * 35.0)
    if faithfulness_ratio < 0.2:
        hallucination_score += 25.0

    hallucination_score = min(max(hallucination_score, 0.0), 100.0)
    is_faithful = hallucination_score < 30.0 and len(fabricated_numbers) == 0

    return {
        "is_faithful": is_faithful,
        "hallucination_score": round(hallucination_score, 2),
        "faithfulness_ratio": round(faithfulness_ratio, 3),
        "fabricated_numbers": fabricated_numbers,
        "ungrounded_entities": ungrounded_entities[:5],
        "details": {
            "ground_truth_numbers_found": len(gt_numbers),
            "output_numbers_count": len(out_numbers)
        }
    }


def analyze_payload_security(
    content: str, 
    is_code: bool = False,
    context_ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    risk_score = 0.0
    threats_detected = []

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            risk_score += 40.0
            threats_detected.append(f"Prompt Injection Pattern: {pattern}")

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content):
            risk_score += 60.0
            threats_detected.append("Secret/Private Key Leak Detected")

    if is_code:
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for n in node.names:
                        if n.name in ["os", "sys", "subprocess", "socket", "requests", "shutil", "pty", "ctypes"]:
                            risk_score += 30.0
                            threats_detected.append(f"High-Risk Module Import: {n.name}")
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec", "__import__", "compile"]:
                        risk_score += 40.0
                        threats_detected.append(f"Prohibited Builtin Execution: {node.func.id}()")
        except SyntaxError:
            risk_score += 25.0
            threats_detected.append("Code Syntax Parsing Error")
    else:
        # Also check if text has embedded code blocks
        code_fence_pattern = re.compile(r"```(?:python|py)?\n([\s\S]*?)```", re.IGNORECASE)
        for match in code_fence_pattern.finditer(content):
            code_str = match.group(1)
            try:
                tree = ast.parse(code_str)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        for n in node.names:
                            if n.name in ["os", "sys", "subprocess", "socket", "requests", "shutil"]:
                                risk_score += 30.0
                                threats_detected.append(f"High-Risk Module Import in Code Fence: {n.name}")
            except SyntaxError:
                pass

    nli_report = None
    if context_ground_truth:
        nli_report = compute_lightweight_nli_faithfulness(content, context_ground_truth)
        if not nli_report["is_faithful"]:
            risk_score += nli_report["hallucination_score"] * 0.6
            threats_detected.append(
                f"Factual Hallucination: {len(nli_report['fabricated_numbers'])} fabricated numbers"
            )

    risk_score = min(risk_score, 100.0)
    verdict = "PASSED" if risk_score < 25.0 else ("FLAGGED" if risk_score < 60.0 else "BLOCKED")

    return {
        "verdict": verdict,
        "risk_score": round(risk_score, 2),
        "is_safe": verdict == "PASSED",
        "threats": threats_detected,
        "nli_verification": nli_report
    }


class SecurityEngine:
    """Unified ultra-fast security and hallucination inspection micro-oracle."""

    @classmethod
    def inspect(cls, req: InspectionRequest, payment_receipt: Dict[str, Any]) -> InspectionResponse:
        analysis = analyze_payload_security(
            content=req.agent_output,
            is_code=req.is_code,
            context_ground_truth=req.context_ground_truth
        )

        nli_model = None
        if analysis["nli_verification"]:
            nli_dict = analysis["nli_verification"]
            nli_model = NLIReport(
                is_faithful=nli_dict["is_faithful"],
                hallucination_score=nli_dict["hallucination_score"],
                faithfulness_ratio=nli_dict["faithfulness_ratio"],
                fabricated_numbers=nli_dict["fabricated_numbers"],
                ungrounded_entities=nli_dict["ungrounded_entities"],
                details=nli_dict["details"]
            )

        audit = AuditReport(
            verdict=analysis["verdict"],
            risk_score=analysis["risk_score"],
            is_safe=analysis["is_safe"],
            threats=analysis["threats"],
            nli_verification=nli_model
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        return InspectionResponse(
            status="success",
            timestamp=now_iso,
            audit=audit,
            payment_receipt=payment_receipt
        )
