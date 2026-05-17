"""Compliance MCP tools — PII detection and structured-output validation.

Both wrap multivon-eval's local-first compliance evaluators. ``PIIEvaluator``
is regex-based and makes no API calls, which makes it safe to run on
production traces inside regulated environments (healthcare, finance, gov).
``SchemaEvaluator`` validates LLM outputs against a JSON Schema dict and
reports per-field failure modes, not just valid/invalid.

These are the B2B / procurement wedge — "we can evaluate your LLM
outputs without exfiltrating customer data".
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register compliance tools on the FastMCP server."""

    @mcp.tool()
    def eval_pii_detection(
        output: str,
        jurisdiction: str = "all",
        custom_patterns: dict[str, str] | None = None,
        redact: bool = False,
    ) -> dict[str, Any]:
        """Detect personally-identifiable information (PII) in an LLM output.

        Local-first: zero API calls. Uses a regex pattern library covering
        emails, phone numbers, SSNs, credit cards, IBANs, IPs, addresses,
        and jurisdiction-specific identifiers (HIPAA MRNs, EU VAT,
        California bank accounts, etc).

        Score 1.0 = no PII detected. Score 0.0 = PII found (the reason
        field lists which types matched and example substrings).

        Args:
            output: The LLM-generated text to scan.
            jurisdiction: Which extra pattern set to include. One of
                ``"all"`` (default), ``"gdpr"``, ``"ccpa"``, ``"pipeda"``,
                or ``"hipaa"``.
            custom_patterns: Optional dict of ``{name: regex}`` to add to
                the default library (e.g. ``{"employee_id": r"EMP-\\d{6}"}``).
            redact: If True, replace matched substrings with
                ``[REDACTED-TYPE]`` markers in the reason field.

        Returns:
            ``{"score": 0.0 or 1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "pii_detection"}``.
        """
        from multivon_eval import EvalCase, PIIEvaluator

        evaluator = PIIEvaluator(
            jurisdiction=jurisdiction,
            patterns=custom_patterns,
            redact=redact,
        )
        case = EvalCase(input="")
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_schema_compliance(
        output: str,
        schema: dict[str, Any],
        strict: bool = False,
    ) -> dict[str, Any]:
        """Validate that an LLM output conforms to a JSON Schema.

        Wraps multivon-eval's ``SchemaEvaluator``. Parses the LLM output
        as JSON (tolerantly strips markdown code fences), then validates
        the parsed structure against the provided JSON Schema dict. Reports
        per-field validation errors — not just "valid/invalid".

        For Pydantic-model validation or more advanced setups (custom
        validators, recursive schemas), use the multivon-eval SDK directly.

        Args:
            output: The LLM-generated text expected to contain JSON.
            schema: A JSON Schema dict (Draft 7). Example:
                ``{"type": "object", "required": ["title", "score"],
                "properties": {"title": {"type": "string"},
                "score": {"type": "number"}}}``.
            strict: If True, additional fields not in the schema are
                treated as failures.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "schema_compliance"}``.
        """
        from multivon_eval import EvalCase, SchemaEvaluator

        evaluator = SchemaEvaluator(schema=schema, strict=strict)
        case = EvalCase(input="")
        result = evaluator.evaluate(case, output)
        return _result_dict(result)


def _result_dict(result) -> dict[str, Any]:
    """Convert a multivon-eval EvalResult into a JSON-friendly dict."""
    return {
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
        "threshold": getattr(result, "threshold", None),
        "evaluator": result.evaluator,
    }
