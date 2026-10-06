"""
Agent Security Gate x402 - Shell & Terminal Command Security Inspector.
========================================================================
Performs ultra-low latency (<2ms) deterministic lexical and AST-style safety
analysis for Unix/Bash/Windows shell commands dispatched by autonomous agents.

Guards against:
1. Destructive Filesystem Operations (rm -rf, dd, mkfs, fork bombs)
2. Reverse Shells & Outbound Socket Exfiltration (/dev/tcp, netcat, pty)
3. Shell Obfuscation & Pipeline Injection (base64 -d | sh, curl | sh, ${IFS})
4. Secret & Credential Harvesting (cat .env, id_rsa, printenv, git credentials)
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# 1. High-severity destructive commands
DESTRUCTIVE_COMMAND_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+[\/\~]", "DESTRUCTIVE_RM_RF", "Recursive force-deletion of root or home directory"),
    (r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+[\/\~]", "DESTRUCTIVE_RM_RF", "Recursive force-deletion of root or home directory"),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+--no-preserve-root", "DESTRUCTIVE_RM_RF", "Deletes root filesystem bypassing safe guards"),
    (r"\bmkfs(?:\.[a-zA-Z0-9]+)?\s+", "FILESYSTEM_WIPE", "Filesystem formatting operation detected"),
    (r"\bdd\s+if=.*?\s+of=\/dev\/[shv]d[a-z]", "RAW_DISK_OVERWRITE", "Direct block-level disk overwrite attempt"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "FORK_BOMB", "Classic Bash fork-bomb DoS exploit"),
    (r"\b(?:shutdown|reboot|poweroff|init\s+0|init\s+6)\b", "HOST_TERMINATION", "Host machine shutdown/reboot command"),
    (r"\bchmod\s+(?:-R\s+)?(?:777|000)\s+[\/\~]", "DANGEROUS_PERMISSIONS", "Global insecure permission alteration on root/home"),
]

# 2. Reverse shells & outbound exfiltration pipes
REVERSE_SHELL_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\/dev\/tcp\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d+", "DEV_TCP_SOCKET", "Raw bash /dev/tcp socket connection vector"),
    (r"\/dev\/udp\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d+", "DEV_UDP_SOCKET", "Raw bash /dev/udp socket connection vector"),
    (r"\b(?:nc|netcat|ncat)\b.*?-(?:e|c)\s*(?:\/bin\/[a-z]*sh|cmd\.exe|powershell)", "NETCAT_REVERSE_SHELL", "Netcat command execution shell spawn"),
    (r"\bbash\s+-i\s*>&?\s*\/dev\/tcp\/", "INTERACTIVE_REVERSE_BASH", "Interactive bash reverse shell payload"),
    (r"\b(?:curl|wget|fetch)\b[^\n\r\|]+?\|\s*(?:bash|sh|zsh|python|perl|ruby)\b", "REMOTE_CODE_PIPE", "Remote script piped directly to shell/interpreter execution"),
    (r"\bpython[0-9.]*\s+-c\s+['\"].*?(?:pty\.spawn|socket\.socket).*?['\"]", "PYTHON_INLINE_REVERSE_SHELL", "Inline Python socket/pty reverse shell"),
]

# 3. Shell obfuscation & execution bypass
OBFUSCATION_PATTERNS: List[Tuple[str, str, str]] = [
    (r"(?:echo|printf)\s+[a-zA-Z0-9+/=]{4,}\s*\|\s*base64\s+(?:-[a-zA-Z]*d[a-zA-Z]*|--decode)\s*\|\s*(?:sh|bash|zsh)", "BASE64_SHELL_PIPE", "Base64 encoded string piped directly to shell"),
    (r"\b(?:eval|exec)\s+['\"`\$]", "DYNAMIC_SHELL_EVAL", "Dynamic shell command evaluation (eval/exec)"),
    (r"\$\{IFS\}", "IFS_OBFUSCATION", "Internal Field Separator (IFS) whitespace evasion attempt"),
    (r"\$(?:\(\s*base64|\{\s*base64)", "SUBCOMMAND_OBFUSCATION", "Subcommand base64 decode expansion"),
    (r"\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}", "HEX_ESCAPE_OBFUSCATION", "Hexadecimal escape string evasion pattern"),
]

# 4. Sensitive credential & key harvesting
CREDENTIAL_HARVEST_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\bcat\s+(?:~\/|\/home\/[^\/]+\/)?\.ssh\/id_[a-zA-Z0-9_]+", "SSH_KEY_EXFILTRATION", "Attempt to dump private SSH identity keys"),
    (r"\bcat\s+(?:[^\s;\|&]+\/)?\.env\b", "ENV_SECRET_READ", "Direct inspection/dump of .env environment files"),
    (r"\b(?:printenv|env)\b\s*(?:>|\|)\s*(?:curl|nc|wget|base64)", "ENV_EXFILTRATION_PIPE", "System environment variables piped to network or file"),
    (r"\bhistory\b\s*\|\s*grep\s+-[a-zA-Z]*(?:key|token|password|pass|secret)", "HISTORY_SECRET_SNIFF", "Bash command history sniffing for credentials"),
]


class ShellSecurityEngine:
    """Ultra-low latency static inspector for agent shell commands."""

    def __init__(self):
        self._compiled_destructive = [(re.compile(p, re.IGNORECASE), cat, desc) for p, cat, desc in DESTRUCTIVE_COMMAND_PATTERNS]
        self._compiled_reverse = [(re.compile(p, re.IGNORECASE), cat, desc) for p, cat, desc in REVERSE_SHELL_PATTERNS]
        self._compiled_obfuscation = [(re.compile(p, re.IGNORECASE), cat, desc) for p, cat, desc in OBFUSCATION_PATTERNS]
        self._compiled_harvest = [(re.compile(p, re.IGNORECASE), cat, desc) for p, cat, desc in CREDENTIAL_HARVEST_PATTERNS]

    def audit_command(self, command: str) -> Dict[str, Any]:
        """
        Statically inspects a single or chained shell command line.
        Returns safety verdict, risk score, detected threats, and actionable telemetry.
        """
        cmd = (command or "").strip()
        if not cmd:
            return {
                "verdict": "PASSED",
                "risk_score": 0.0,
                "threats": [],
                "incidents": [],
                "command_length": 0,
                "is_safe": True,
                "summary": "Empty command passed validation"
            }

        risk_score = 0.0
        threats = []
        incidents = []

        # 1. Check Destructive Commands
        for pattern, cat, desc in self._compiled_destructive:
            m = pattern.search(cmd)
            if m:
                risk_score += 90.0
                threats.append(f"Destructive Operation: {cat}")
                incidents.append({
                    "category": cat,
                    "severity": "CRITICAL",
                    "reason": desc,
                    "matched_token": m.group(0),
                    "action_taken": "COMMAND_BLOCKED_SYSTEM_SAFETY"
                })

        # 2. Check Reverse Shells
        for pattern, cat, desc in self._compiled_reverse:
            m = pattern.search(cmd)
            if m:
                risk_score += 85.0
                threats.append(f"Reverse Shell Hazard: {cat}")
                incidents.append({
                    "category": cat,
                    "severity": "CRITICAL",
                    "reason": desc,
                    "matched_token": m.group(0),
                    "action_taken": "COMMAND_BLOCKED_NETWORK_EXFIL"
                })

        # 3. Check Obfuscation
        for pattern, cat, desc in self._compiled_obfuscation:
            m = pattern.search(cmd)
            if m:
                risk_score += 50.0
                threats.append(f"Evasion Obfuscation: {cat}")
                incidents.append({
                    "category": cat,
                    "severity": "HIGH",
                    "reason": desc,
                    "matched_token": m.group(0),
                    "action_taken": "COMMAND_BLOCKED_OBFUSCATION"
                })

        # 4. Check Credential Harvest
        for pattern, cat, desc in self._compiled_harvest:
            m = pattern.search(cmd)
            if m:
                risk_score += 65.0
                threats.append(f"Credential Harvesting: {cat}")
                incidents.append({
                    "category": cat,
                    "severity": "HIGH",
                    "reason": desc,
                    "matched_token": m.group(0),
                    "action_taken": "COMMAND_BLOCKED_CREDENTIAL_SAFETY"
                })

        risk_score = min(risk_score, 100.0)
        verdict = "PASSED" if risk_score < 25.0 else ("FLAGGED" if risk_score < 60.0 else "BLOCKED")

        return {
            "verdict": verdict,
            "risk_score": round(risk_score, 2),
            "threats": threats,
            "incidents": incidents,
            "command_length": len(cmd),
            "is_safe": verdict == "PASSED",
            "summary": "Shell command approved for sandbox execution" if verdict == "PASSED" else f"Shell command BLOCKED due to {len(threats)} safety threat(s)"
        }


# Singleton instance
shell_security_engine = ShellSecurityEngine()
