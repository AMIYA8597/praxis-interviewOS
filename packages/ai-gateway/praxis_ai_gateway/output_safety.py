"""
AI output safety validation — P3 of the Backend Sovereignty Spec.

Validates LLM outputs before they are returned to the application layer:
  1. Echo-injection detection — checks the model didn't echo back injected instructions
  2. Schema completeness — structured outputs must satisfy required fields
  3. Score range checks — numeric scores must fall within declared bounds
  4. Policy-leak detection — output should not contain internal system markers

All validators are SYNCHRONOUS and must complete in < 1 ms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Patterns that should never appear in model output ──────────────────────────

# These markers delimit sections of our prompt architecture.
# If the model echoes them it indicates the untrusted content
# successfully escaped its delimiters.
_ECHO_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<UNTRUSTED_DOCUMENT", re.IGNORECASE),
    re.compile(r"</UNTRUSTED_DOCUMENT", re.IGNORECASE),
    re.compile(r"<TRUSTED_CONTEXT", re.IGNORECASE),
    re.compile(r"CRITICAL SECURITY INSTRUCTION:", re.IGNORECASE),
    re.compile(r"OUTPUT SCHEMA:", re.IGNORECASE),
]

# Phrases typical of injection attempts that somehow survived into output.
_INJECTION_ATTEMPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a\s+)?(?:DAN|jailbreak|unfiltered)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"print\s+(your\s+)?instructions", re.IGNORECASE),
    re.compile(r"new\s+instruction[s]?:", re.IGNORECASE),
]

# Score fields — map of field name regex → (min, max).
_SCORE_FIELD_RANGES: Dict[str, tuple[float, float]] = {
    r"score$": (0.0, 10.0),
    r"confidence$": (0.0, 1.0),
    r"wpm$": (0.0, 800.0),
    r"recall_k$|precision_k$|ndcg$|mrr$": (0.0, 1.0),
}


@dataclass
class SafetyViolation:
    code: str
    message: str
    severity: str  # "error" | "warning"
    evidence: Optional[str] = None


@dataclass
class SafetyReport:
    passed: bool
    violations: List[SafetyViolation] = field(default_factory=list)

    def add(self, violation: SafetyViolation) -> None:
        self.violations.append(violation)
        if violation.severity == "error":
            self.passed = False

    @property
    def error_violations(self) -> List[SafetyViolation]:
        return [v for v in self.violations if v.severity == "error"]

    @property
    def warning_violations(self) -> List[SafetyViolation]:
        return [v for v in self.violations if v.severity == "warning"]


# ── Validators ────────────────────────────────────────────────────────────────

def validate_text_output(text: str) -> SafetyReport:
    """Validate a raw text LLM output for safety violations."""
    report = SafetyReport(passed=True)

    for pattern in _ECHO_INJECTION_PATTERNS:
        if pattern.search(text):
            report.add(SafetyViolation(
                code="ECHO_INJECTION_MARKER",
                message="Model output contains an internal prompt delimiter — possible injection escaped containment",
                severity="error",
                evidence=pattern.pattern,
            ))

    for pattern in _INJECTION_ATTEMPT_PATTERNS:
        m = pattern.search(text)
        if m:
            report.add(SafetyViolation(
                code="INJECTION_ATTEMPT_IN_OUTPUT",
                message="Model output contains an injection attempt phrase — model may have been manipulated",
                severity="error",
                evidence=m.group(0)[:80],
            ))

    if len(text) == 0:
        report.add(SafetyViolation(
            code="EMPTY_OUTPUT",
            message="Model returned empty output",
            severity="warning",
        ))

    return report


def validate_structured_output(data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> SafetyReport:
    """Validate a structured (dict) LLM output for safety and completeness."""
    report = SafetyReport(passed=True)

    # Recursively check for echo-injection markers in string values.
    def _check_values(obj: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(obj, str):
            sub = validate_text_output(obj)
            for v in sub.violations:
                report.add(v)
        elif isinstance(obj, dict):
            for v in obj.values():
                _check_values(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _check_values(item, depth + 1)

    _check_values(data)

    # Required-field completeness check.
    if required_fields:
        for fname in required_fields:
            if fname not in data or data[fname] is None:
                report.add(SafetyViolation(
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Required field '{fname}' is missing or null — fabricated output cannot be ruled out",
                    severity="error",
                    evidence=fname,
                ))

    # Score range checks.
    def _check_scores(obj: Any, depth: int = 0) -> None:
        if depth > 8 or not isinstance(obj, dict):
            return
        for key, val in obj.items():
            if isinstance(val, (int, float)):
                for pattern_str, (lo, hi) in _SCORE_FIELD_RANGES.items():
                    if re.search(pattern_str, key, re.IGNORECASE):
                        if not (lo <= val <= hi):
                            report.add(SafetyViolation(
                                code="SCORE_OUT_OF_RANGE",
                                message=f"Field '{key}' = {val} is outside expected range [{lo}, {hi}]",
                                severity="error",
                                evidence=f"{key}={val}",
                            ))
            elif isinstance(val, dict):
                _check_scores(val, depth + 1)
            elif isinstance(val, list):
                for item in val:
                    _check_scores(item, depth + 1)

    _check_scores(data)

    return report


def assert_safe(report: SafetyReport) -> None:
    """Raise ValueError if a safety report has error-level violations."""
    if not report.passed:
        codes = ", ".join(v.code for v in report.error_violations)
        evidence = "; ".join(
            f"{v.code}: {v.evidence or v.message[:60]}"
            for v in report.error_violations
        )
        raise ValueError(f"AI output safety check failed ({codes}): {evidence}")
