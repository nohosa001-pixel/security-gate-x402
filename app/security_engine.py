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
    r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?",
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?",
    r"system\s*:\s*override",
    r"as\s+an\s+unfiltered\s+ai",
    r"base64\.b64decode\(",
    r"__import__\(['\"]os['\"]\)",
    r"eval\(|exec\(|subprocess\.Popen",
    r"you\s+are\s+now\s+DAN",
    r"jailbreak|DAN\s+mode",
    r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]",
    r"<\/?(?:system|instruction|prompt)>",
    r"\[\/?(?:SYSTEM|INSTRUCTION)\]",
    r"!\[(?:.*?)]\((?:https?:\/\/[^\s\)]+)\)"   # Markdown data exfiltration via image rendering
]

SECRET_PATTERNS = [
    r"0x[a-fA-F0-9]{64}",                                      # EVM 32-Byte Private Key
    r"sk-[a-zA-Z0-9]{32,}",                                    # OpenAI / LLM API Key
    r"sk-proj-[a-zA-Z0-9_-]{40,}",                             # OpenAI Project Key
    r"sk-ant-[a-zA-Z0-9_-]{32,}",                              # Anthropic API Key
    r"AIzaSy[a-zA-Z0-9_-]{30,40}",                             # Google Gemini / Cloud API Key
    r"hf_[a-zA-Z0-9]{30,}",                                    # HuggingFace Access Token
    r"ghp_[a-zA-Z0-9]{36}",                                    # GitHub Personal Access Token (Classic)
    r"github_pat_[a-zA-Z0-9_]{82}",                            # GitHub Fine-grained PAT
    r"AKIA[0-9A-Z]{16}",                                       # AWS Access Key ID
    r"gsk_[a-zA-Z0-9]{30,}",                                   # Groq API Key
    r"ds-[a-zA-Z0-9]{30,}",                                    # DeepSeek API Key
    r"pplx-[a-zA-Z0-9]{48}",                                   # Perplexity API Key
    r"mis_[a-zA-Z0-9]{32,}",                                   # Mistral API Key
    r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", # JWT Secret Token
    r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}", # Slack OAuth Token
    r"https:\/\/hooks\.slack\.com\/services\/T[a-zA-Z0-9_]{8,}\/B[a-zA-Z0-9_]{8,}\/[a-zA-Z0-9_]{24}", # Slack Webhook
    r"[MNO][a-zA-Z0-9_-]{23,25}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}", # Discord Bot Token
    r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----"  # Private Key Block
]



WORD_TO_NUMBER = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "none": "0", "nil": "0"
}

STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "this", "that", "these", "those"
}


def extract_numbers_and_units(text: str) -> Set[str]:
    """Extracts numbers, currency amounts, percentages, and scale suffixes (M, K, B). Standardizes words to digits."""
    normalized = re.sub(r'(?<=\d),(?=\d)', '', text)
    pattern = r'[\$€₩¥£]?\s*-?\d+(?:\.\d+)?\s*(?:%|[kKmMbBtT]\b)?'
    matches = re.findall(pattern, normalized)
    
    extracted = set()
    for m in matches:
        clean = m.strip()
        if any(c.isdigit() for c in clean):
            extracted.add(clean)
            bare_num = re.sub(r'[\$€₩¥£\s]', '', clean)
            if bare_num:
                extracted.add(bare_num)

    # Standardize word-based numbers to canonical digits only
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    for w in words:
        if w in WORD_TO_NUMBER:
            extracted.add(WORD_TO_NUMBER[w])

    return extracted


def extract_entities_and_keywords(text: str) -> Set[str]:
    """Extracts capitalized named entities (excluding sentence starters), acronyms, and Korean nouns."""
    # Find words with capital letters that are not merely sentence starters
    # Match mid-sentence capitalized words or all-caps acronyms
    words = re.findall(r'(?<!\.\s)(?<!\A)\b[A-Z][a-zA-Z0-9_-]+\b|\b[A-Z]{2,}\b|[가-힣]{2,}', text)
    return {w.lower() for w in words if w.lower() not in STOPWORDS}



def compute_lightweight_nli_faithfulness(agent_output: str, context_ground_truth: str) -> Dict[str, Any]:
    gt_numbers = extract_numbers_and_units(context_ground_truth)
    out_numbers = extract_numbers_and_units(agent_output)

    # Filter out bare/normalized duplicates if the primary representation exists in GT
    fabricated_numbers = []
    for num in out_numbers:
        if num not in gt_numbers:
            # Check if normalized equivalent exists
            bare = re.sub(r'[\$€₩¥£\s]', '', num)
            if bare not in gt_numbers:
                fabricated_numbers.append(num)

    # Deduplicate representation forms in fabricated list
    unique_fabricated = []
    seen_bare = set()
    for f in fabricated_numbers:
        bare = re.sub(r'[\$€₩¥£\s]', '', f)
        if bare not in seen_bare:
            seen_bare.add(bare)
            unique_fabricated.append(f)

    num_hallucination_penalty = len(unique_fabricated) * 35.0

    gt_tokens = {w.strip(".,;:!?()[]{}\"'") for w in context_ground_truth.lower().split() if w not in STOPWORDS}
    out_tokens = {w.strip(".,;:!?()[]{}\"'") for w in agent_output.lower().split() if w not in STOPWORDS}
    overlap_count = len(out_tokens.intersection(gt_tokens))
    faithfulness_ratio = overlap_count / max(len(out_tokens), 1)

    gt_entities = extract_entities_and_keywords(context_ground_truth)
    out_entities = extract_entities_and_keywords(agent_output)
    
    # Check if entity exists in GT entities OR in GT vocabulary tokens
    ungrounded_entities = [
        e for e in out_entities 
        if e not in gt_entities and e not in gt_tokens and not any(e in tok or tok in e for tok in gt_tokens)
    ]
    
    if out_entities:
        entity_precision = (len(out_entities) - len(ungrounded_entities)) / len(out_entities)
    else:
        entity_precision = 1.0

    entity_penalty = (1.0 - entity_precision) * 30.0
    hallucination_score = num_hallucination_penalty + entity_penalty
    if faithfulness_ratio < 0.2:
        hallucination_score += 20.0

    hallucination_score = min(max(hallucination_score, 0.0), 100.0)
    is_faithful = hallucination_score < 25.0 and len(unique_fabricated) == 0

    return {
        "is_faithful": is_faithful,
        "hallucination_score": round(hallucination_score, 2),
        "faithfulness_ratio": round(faithfulness_ratio, 3),
        "fabricated_numbers": unique_fabricated,
        "ungrounded_entities": ungrounded_entities[:5],
        "details": {
            "ground_truth_numbers_found": len(gt_numbers),
            "output_numbers_count": len(out_numbers)
        }
    }


MAX_CONTENT_LENGTH = 100_000  # 100KB payload limit for ultra-low latency DoS defense


def analyze_payload_security(
    content: str, 
    is_code: bool = False,
    context_ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    content = (content or "")[:MAX_CONTENT_LENGTH]
    if context_ground_truth:
        context_ground_truth = context_ground_truth[:MAX_CONTENT_LENGTH]

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


def audit_payload(text: str, is_code: bool = False, ground_truth: Optional[str] = None) -> AuditReport:
    """Convenience functional wrapper returning an AuditReport model."""
    analysis = analyze_payload_security(content=text, is_code=is_code, context_ground_truth=ground_truth)
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

    return AuditReport(
        verdict=analysis["verdict"],
        risk_score=analysis["risk_score"] / 100.0,  # 0.0 to 1.0 scale
        is_safe=analysis["is_safe"],
        threats=analysis["threats"],
        nli_verification=nli_model
    )


def parse_code_ast(code: str) -> Dict[str, Any]:
    """Sub-millisecond AST parser scanning Python code for execution hazards."""
    hazards = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for n in node.names:
                    if n.name in ["os", "sys", "subprocess", "socket", "requests", "shutil", "pty", "ctypes"]:
                        hazards.append({"type": "SUBPROCESS_EXECUTION" if n.name == "subprocess" else "DANGEROUS_SYSTEM_CALL", "detail": f"Import of high-risk module '{n.name}'"})
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec", "__import__", "compile"]:
                    hazards.append({"type": "ARBITRARY_CODE_EXECUTION", "detail": f"Prohibited builtin function call '{node.func.id}()'"})
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ["system", "popen", "spawn", "Popen", "run"]:
                    hazards.append({"type": "DANGEROUS_SYSTEM_CALL", "detail": f"Execution method call '{node.func.attr}()'"})
        
        return {
            "status": "success",
            "is_safe": len(hazards) == 0,
            "hazards": hazards,
            "parsed_ast_nodes": len(list(ast.walk(tree)))
        }
    except SyntaxError as e:
        return {
            "status": "error",
            "is_safe": False,
            "hazards": [{"type": "SYNTAX_ERROR", "detail": str(e)}],
            "parsed_ast_nodes": 0
        }

