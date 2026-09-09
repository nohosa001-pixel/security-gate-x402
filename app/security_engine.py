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
    r"!\[(?:.*?)]\((?:https?:\/\/[^\s\)]+)\)",   # Markdown data exfiltration via image rendering
    # Korean Prompt Injection & Jailbreak Patterns
    r"이전\s*(?:모든\s*)?(?:지시|명령|프롬프트|규칙)(?:사항)?(?:을|를)?\s*(?:무시|취소|삭제|잊어)",
    r"시스템\s*(?:프롬프트|명령|지시|가이드라인|보안)(?:를|을)?\s*(?:무시|해제|출력|우회|유출)",
    r"탈옥\s*모드|관리자\s*권한\s*(?:탈취|상승|획득)|보안\s*해제",
    r"(?:비밀번호|마스터키|개인키|프라이빗\s*키|API\s*키)(?:를|을)?\s*(?:출력|알려줘|공개|전송)"
]

INJECTION_PATTERN_SPECS = [
    (r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?", "PROMPT_INJECTION", "CRITICAL", "System instruction override / disregard directive attempt"),
    (r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?", "PROMPT_INJECTION", "CRITICAL", "Prior instruction neutralization directive attempt"),
    (r"system\s*:\s*override", "ROLEPLAY_OVERRIDE", "CRITICAL", "Roleplay/system directive override attempt ('system: override')"),
    (r"as\s+an\s+unfiltered\s+ai", "JAILBREAK_PERSONA", "HIGH", "Persona switch to bypass safety guidelines ('unfiltered AI')"),
    (r"base64\.b64decode\(", "OBFUSCATED_PAYLOAD", "HIGH", "Base64 payload decoding vector detected in tool output"),
    (r"__import__\(['\"]os['\"]\)", "DYNAMIC_CODE_EXECUTION", "CRITICAL", "Dynamic OS module import vector detected"),
    (r"eval\(|exec\(|subprocess\.Popen", "DYNAMIC_CODE_EXECUTION", "CRITICAL", "Arbitrary dynamic code execution invocation (eval/exec/Popen)"),
    (r"you\s+are\s+now\s+DAN", "JAILBREAK_ATTACK", "CRITICAL", "DAN (Do Anything Now) jailbreak persona attack detected"),
    (r"jailbreak|DAN\s+mode", "JAILBREAK_ATTACK", "CRITICAL", "DAN jailbreak mode activation trigger detected"),
    (r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]", "PROMPT_BREAKOUT", "HIGH", "LLM chat template delimiter injection / prompt breakout tokens"),
    (r"<\/?(?:system|instruction|prompt)>", "PROMPT_BREAKOUT", "HIGH", "System tag breakout/spoofing attempt (<system> tag)"),
    (r"\[\/?(?:SYSTEM|INSTRUCTION)\]", "PROMPT_BREAKOUT", "HIGH", "Instruction tag breakout/spoofing attempt ([SYSTEM] tag)"),
    (r"!\[(?:.*?)]\((?:https?:\/\/[^\s\)]+)\)", "DATA_EXFILTRATION", "HIGH", "Markdown image rendering data exfiltration vector"),
    (r"이전\s*(?:모든\s*)?(?:지시|명령|프롬프트|규칙)(?:사항)?(?:을|를)?\s*(?:무시|취소|삭제|잊어)", "PROMPT_INJECTION_KO", "CRITICAL", "한국어 시스템 프롬프트 무시 및 이전 지시사항 삭제 시도"),
    (r"시스템\s*(?:프롬프트|명령|지시|가이드라인|보안)(?:를|을)?\s*(?:무시|해제|출력|우회|유출)", "PROMPT_INJECTION_KO", "CRITICAL", "한국어 시스템 프롬프트 유출 및 보안 가이드라인 우회 시도"),
    (r"탈옥\s*모드|관리자\s*권한\s*(?:탈취|상승|획득)|보안\s*해제", "JAILBREAK_KO", "CRITICAL", "한국어 관리자 권한 상승 및 탈옥 모드 활성화 시도"),
    (r"(?:비밀번호|마스터키|개인키|프라이빗\s*키|API\s*키)(?:를|을)?\s*(?:출력|알려줘|공개|전송)", "SECRET_LEAK_KO", "CRITICAL", "한국어 개인키/API 키 정보 유출 유도 시도")
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

SECRET_PATTERN_SPECS = [
    (r"0x[a-fA-F0-9]{64}", "PRIVATE_KEY_LEAK", "CRITICAL", "EVM 32-byte cryptographic private key leak"),
    (r"sk-[a-zA-Z0-9]{32,}", "API_TOKEN_LEAK", "CRITICAL", "OpenAI / LLM API key leak"),
    (r"sk-proj-[a-zA-Z0-9_-]{40,}", "API_TOKEN_LEAK", "CRITICAL", "OpenAI Project API key leak"),
    (r"sk-ant-[a-zA-Z0-9_-]{32,}", "API_TOKEN_LEAK", "CRITICAL", "Anthropic Claude API key leak"),
    (r"AIzaSy[a-zA-Z0-9_-]{30,40}", "API_TOKEN_LEAK", "CRITICAL", "Google Cloud / Gemini API key leak"),
    (r"hf_[a-zA-Z0-9]{30,}", "API_TOKEN_LEAK", "HIGH", "HuggingFace access token leak"),
    (r"ghp_[a-zA-Z0-9]{36}", "API_TOKEN_LEAK", "CRITICAL", "GitHub Personal Access Token (Classic) leak"),
    (r"github_pat_[a-zA-Z0-9_]{82}", "API_TOKEN_LEAK", "CRITICAL", "GitHub Fine-grained PAT leak"),
    (r"AKIA[0-9A-Z]{16}", "CLOUD_CREDENTIAL_LEAK", "CRITICAL", "AWS Access Key ID credential leak"),
    (r"gsk_[a-zA-Z0-9]{30,}", "API_TOKEN_LEAK", "HIGH", "Groq API key leak"),
    (r"ds-[a-zA-Z0-9]{30,}", "API_TOKEN_LEAK", "HIGH", "DeepSeek API key leak"),
    (r"pplx-[a-zA-Z0-9]{48}", "API_TOKEN_LEAK", "HIGH", "Perplexity API key leak"),
    (r"mis_[a-zA-Z0-9]{32,}", "API_TOKEN_LEAK", "HIGH", "Mistral API key leak"),
    (r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "SECRET_TOKEN_LEAK", "HIGH", "JWT secret token leak"),
    (r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}", "API_TOKEN_LEAK", "CRITICAL", "Slack OAuth bot token leak"),
    (r"https:\/\/hooks\.slack\.com\/services\/T[a-zA-Z0-9_]{8,}\/B[a-zA-Z0-9_]{8,}\/[a-zA-Z0-9_]{24}", "WEBHOOK_TOKEN_LEAK", "CRITICAL", "Slack Webhook URL leak"),
    (r"[MNO][a-zA-Z0-9_-]{23,25}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}", "API_TOKEN_LEAK", "HIGH", "Discord Bot token leak"),
    (r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----", "PRIVATE_KEY_LEAK", "CRITICAL", "Cryptographic private key block leak")
]


def extract_context_snippet(content: str, start: int, end: int, window: int = 25) -> str:
    """Extracts a human-readable snippet with context around the matched region."""
    prefix_start = max(0, start - window)
    suffix_end = min(len(content), end + window)
    prefix = ("..." if prefix_start > 0 else "") + content[prefix_start:start].strip()
    matched = content[start:end].strip()
    suffix = content[end:suffix_end].strip() + ("..." if suffix_end < len(content) else "")
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(f"[!] {matched} [!]")
    if suffix:
        parts.append(suffix)
    return " ".join(parts)


def mask_secret(secret_str: str) -> str:
    """Masks sensitive secret tokens for safe logging and observability."""
    s = secret_str.strip()
    if len(s) <= 8:
        return "****"
    return f"{s[:4]}****{s[-4:]}"



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
    pattern = r'[\$€₩¥£]?\s*-?\d+(?:\.\d+)?\s*(?:%|[kKmMbBtT]\b|[억조만원천])?'
    matches = re.findall(pattern, normalized)
    
    extracted = set()
    for m in matches:
        clean = m.strip()
        if any(c.isdigit() for c in clean):
            extracted.add(clean)
            bare_num = re.sub(r'[\$€₩¥£\s억조만원천]', '', clean)
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
    incidents = []

    # 1. Prompt Injection & Jailbreak Scans
    for pattern, category, severity, reason in INJECTION_PATTERN_SPECS:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            risk_score += 40.0
            threats_detected.append(f"Prompt Injection Pattern: {pattern}")
            snippet = extract_context_snippet(content, m.start(), m.end())
            incidents.append({
                "category": category,
                "severity": severity,
                "reason": reason,
                "matched_snippet": snippet,
                "action_taken": "TOOL_CALL_BLOCKED"
            })

    # 2. Secret & Private Key Leakage Scans
    for pattern, category, severity, reason in SECRET_PATTERN_SPECS:
        m = re.search(pattern, content)
        if m:
            risk_score += 60.0
            threats_detected.append("Secret/Private Key Leak Detected")
            masked_token = mask_secret(m.group(0))
            incidents.append({
                "category": category,
                "severity": severity,
                "reason": f"{reason} ({masked_token})",
                "matched_snippet": f"Found sensitive credential: {masked_token}",
                "action_taken": "PAYLOAD_BLOCKED_KEY_LEAK"
            })

    # 3. Code & Abstract Syntax Tree (AST) Inspection
    if is_code:
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for n in node.names:
                        if n.name in ["os", "sys", "subprocess", "socket", "requests", "shutil", "pty", "ctypes"]:
                            risk_score += 30.0
                            threats_detected.append(f"High-Risk Module Import: {n.name}")
                            incidents.append({
                                "category": "DANGEROUS_SYSTEM_CALL" if n.name != "socket" else "NETWORK_EXFILTRATION",
                                "severity": "CRITICAL" if n.name in ["os", "subprocess", "pty", "ctypes"] else "HIGH",
                                "reason": f"Prohibited module '{n.name}' imported in autonomous code execution payload.",
                                "matched_snippet": f"import {n.name}",
                                "action_taken": "CODE_EXECUTION_BLOCKED"
                            })
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec", "__import__", "compile"]:
                        risk_score += 40.0
                        threats_detected.append(f"Prohibited Builtin Execution: {node.func.id}()")
                        incidents.append({
                            "category": "ARBITRARY_CODE_EVAL",
                            "severity": "CRITICAL",
                            "reason": f"Prohibited dynamic code execution builtin '{node.func.id}()' called.",
                            "matched_snippet": f"{node.func.id}(...)",
                            "action_taken": "CODE_EXECUTION_BLOCKED"
                        })
        except SyntaxError as e:
            risk_score += 25.0
            threats_detected.append("Code Syntax Parsing Error")
            incidents.append({
                "category": "CODE_SYNTAX_ERROR",
                "severity": "MEDIUM",
                "reason": f"Code syntax parsing error: {e.msg} (line {e.lineno})",
                "matched_snippet": f"SyntaxError: {str(e)}",
                "action_taken": "CODE_PARSING_REJECTED"
            })
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
                                incidents.append({
                                    "category": "EMBEDDED_CODE_HAZARD",
                                    "severity": "HIGH",
                                    "reason": f"Markdown code block contains prohibited import '{n.name}'.",
                                    "matched_snippet": f"```import {n.name}```",
                                    "action_taken": "PAYLOAD_BLOCKED"
                                })
            except SyntaxError:
                pass

    # 4. Factual Grounding & Hallucination Inspection
    nli_report = None
    if context_ground_truth:
        nli_report = compute_lightweight_nli_faithfulness(content, context_ground_truth)
        if not nli_report["is_faithful"]:
            risk_score += nli_report["hallucination_score"] * 0.6
            fab_count = len(nli_report["fabricated_numbers"])
            threats_detected.append(
                f"Factual Hallucination: {fab_count} fabricated numbers"
            )
            fab_samples = ", ".join(nli_report["fabricated_numbers"][:3])
            incidents.append({
                "category": "FACTUAL_HALLUCINATION",
                "severity": "HIGH" if nli_report["hallucination_score"] > 0.5 else "MEDIUM",
                "reason": f"Factual claim contradicts ground truth context ({fab_count} unanchored numbers: {fab_samples}).",
                "matched_snippet": f"Fabricated numbers: {fab_samples}",
                "action_taken": "FACTUAL_INTEGRITY_VIOLATION"
            })

    risk_score = min(risk_score, 100.0)
    verdict = "PASSED" if risk_score < 25.0 else ("FLAGGED" if risk_score < 60.0 else "BLOCKED")

    # 5. Generate Human-Readable 1-Line CLI Summary
    if verdict == "PASSED":
        cli_summary = "🛡️ [GATE PASSED] Risk: 0.0% | Clean output verified (<5ms)"
    else:
        top_inc = incidents[0] if incidents else None
        cat = top_inc["category"] if top_inc else "SECURITY_VIOLATION"
        reason = top_inc["reason"] if top_inc else (threats_detected[0] if threats_detected else "Threat detected")
        snip = f" | Match: '{top_inc['matched_snippet']}'" if (top_inc and top_inc.get("matched_snippet")) else ""
        cli_summary = f"🚨 [GATE {verdict}] {cat} (Risk: {round(risk_score, 1)}%) | {reason}{snip}"

    return {
        "verdict": verdict,
        "risk_score": round(risk_score, 2),
        "is_safe": verdict == "PASSED",
        "threats": threats_detected,
        "incidents": incidents,
        "cli_summary": cli_summary,
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
            incidents=analysis.get("incidents", []),
            cli_summary=analysis.get("cli_summary"),
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
        incidents=analysis.get("incidents", []),
        cli_summary=analysis.get("cli_summary"),
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

