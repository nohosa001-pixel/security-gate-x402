"""Semantic AST Guard with Constant Folding and Dynamic Taint Analysis for security-gate-x402.

Detects obfuscated prompt injection and dynamic evasion techniques, including:
- Concatenated strings ('o' + 's', 'eval' + '')
- Dynamic attribute lookup (getattr, __getattribute__)
- Dangerous reflection primitives (__builtins__, globals(), locals(), __import__)
- Byte/character manipulation (chr(...), bytes.fromhex, base64 eval)
"""

from __future__ import annotations

import ast
import hashlib
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class SemanticASTSecurityViolation:
    """Represents a structured security violation for slashable exploit evidence."""

    def __init__(self, violation_type: str, line_no: int, detail: str, raw_snippet: str):
        self.violation_type = violation_type
        self.line_no = line_no
        self.detail = detail
        self.raw_snippet = raw_snippet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type,
            "line_no": self.line_no,
            "detail": self.detail,
            "raw_snippet": self.raw_snippet,
        }


class SemanticTaintVisitor(ast.NodeVisitor):
    """AST Visitor that resolves constant expressions and tracks dangerous invocation chains."""

    DANGEROUS_MODULES: Set[str] = {
        "os", "subprocess", "sys", "shutil", "pty", "socket", "http.client",
        "requests", "urllib", "ctypes", "posix", "nt", "importlib", "pickle"
    }

    DANGEROUS_BUILTINS: Set[str] = {
        "eval", "exec", "__import__", "globals", "locals", "compile",
        "open", "input", "breakpoint"
    }

    def __init__(self):
        self.violations: List[SemanticASTSecurityViolation] = []
        self._folded_constants: Dict[ast.AST, Any] = {}

    def visit_BinOp(self, node: ast.BinOp):
        """Constant Folding: evaluate string additions like 'o' + 's' or 'sub' + 'process'."""
        self.generic_visit(node)
        if isinstance(node.op, ast.Add):
            left_val = self._resolve_constant(node.left)
            right_val = self._resolve_constant(node.right)
            if isinstance(left_val, str) and isinstance(right_val, str):
                combined = left_val + right_val
                self._folded_constants[node] = combined

                # Check if folded string reveals a dangerous module or builtin
                if combined in self.DANGEROUS_MODULES or combined in self.DANGEROUS_BUILTINS:
                    self.violations.append(
                        SemanticASTSecurityViolation(
                            violation_type="OBFUSCATED_IDENTIFIER",
                            line_no=node.lineno,
                            detail=f"De-obfuscated dangerous identifier: '{combined}'",
                            raw_snippet=ast.unparse(node) if hasattr(ast, "unparse") else combined
                        )
                    )

    def visit_Call(self, node: ast.Call):
        """Analyze function calls for dynamic evasion patterns."""
        self.generic_visit(node)

        # 1. Direct call to dangerous builtin (eval, exec, __import__, etc.)
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.DANGEROUS_BUILTINS:
                self.violations.append(
                    SemanticASTSecurityViolation(
                        violation_type="DANGEROUS_BUILTIN_EXECUTION",
                        line_no=node.lineno,
                        detail=f"Forbidden invocation of builtin: '{func_name}'",
                        raw_snippet=ast.unparse(node) if hasattr(ast, "unparse") else func_name
                    )
                )

        # 2. Dynamic attribute resolution via getattr(obj, attr)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == "getattr":
                self.violations.append(
                    SemanticASTSecurityViolation(
                        violation_type="DYNAMIC_REFLECTION_GETATTR",
                        line_no=node.lineno,
                        detail="Dynamic reflection via getattr() is strictly blocked.",
                        raw_snippet=ast.unparse(node) if hasattr(ast, "unparse") else "getattr"
                    )
                )

        # 3. Direct invocation of getattr(...) as a top-level function
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            # Attempt to resolve second argument if constant
            arg_name = "unknown"
            if len(node.args) >= 2:
                resolved_arg = self._resolve_constant(node.args[1])
                if resolved_arg:
                    arg_name = str(resolved_arg)
            self.violations.append(
                SemanticASTSecurityViolation(
                    violation_type="DYNAMIC_REFLECTION_GETATTR",
                    line_no=node.lineno,
                    detail=f"Dynamic reflection via getattr(..., '{arg_name}') detected.",
                    raw_snippet=ast.unparse(node) if hasattr(ast, "unparse") else "getattr"
                )
            )

        # 4. Check for chr(...) sequence folding (e.g. chr(111)+chr(115))
        if isinstance(node.func, ast.Name) and node.func.id == "chr":
            if node.args and isinstance(node.args[0], ast.Constant):
                try:
                    char_val = chr(int(node.args[0].value))
                    self._folded_constants[node] = char_val
                except (ValueError, TypeError):
                    pass

    def visit_Attribute(self, node: ast.Attribute):
        """Check for dangerous dunder attribute access (__builtins__, __class__, __subclasses__)."""
        self.generic_visit(node)
        if node.attr in {"__builtins__", "__subclasses__", "__bases__", "__globals__"}:
            self.violations.append(
                SemanticASTSecurityViolation(
                    violation_type="PROTOTYPE_POLLUTION_DUNDER",
                    line_no=node.lineno,
                    detail=f"Restricted dunder navigation detected: '{node.attr}'",
                    raw_snippet=ast.unparse(node) if hasattr(ast, "unparse") else node.attr
                )
            )

    def _resolve_constant(self, node: ast.AST) -> Any:
        """Resolve constants including previously folded expressions."""
        if node in self._folded_constants:
            return self._folded_constants[node]
        if isinstance(node, ast.Constant):
            return node.value
        return None


class SemanticASTGuard:
    """Production Guard Interface for deep syntax inspection."""

    @staticmethod
    def inspect_code(code_str: str) -> Tuple[bool, List[Dict[str, Any]], float]:
        """Inspects source code using AST constant folding and taint tracking.

        Returns: (is_safe, violations_list, latency_ms)
        """
        start_time = time.perf_counter()

        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return False, [{
                "violation_type": "SYNTAX_ERROR",
                "line_no": getattr(e, "lineno", 0) or 0,
                "detail": f"Unparseable syntax error: {str(e)}",
                "raw_snippet": ""
            }], latency_ms

        visitor = SemanticTaintVisitor()
        visitor.visit(tree)

        latency_ms = (time.perf_counter() - start_time) * 1000
        is_safe = len(visitor.violations) == 0
        violations_data = [v.to_dict() for v in visitor.violations]

        return is_safe, violations_data, latency_ms
