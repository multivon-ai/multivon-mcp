"""Capability-discovery MCP tool.

``eval.discover`` returns the full machine-readable catalog of what
this server can do — every evaluator, every trap family, every default
threshold, every shipped calibration row. An agent calls this once at
session start to plan against the available surface, then calls the
specific tools as needed.

This is the "agent-readable evaluation spec" pattern: instead of an
agent parsing markdown docs to figure out what's available, it asks
the server for a JSON catalog.
"""
from __future__ import annotations

import inspect
from typing import Any


def register(mcp) -> None:
    """Register the discover tool on the FastMCP server."""

    @mcp.tool()
    def eval_discover() -> dict[str, Any]:
        """Return the full machine-readable capability catalog.

        Useful as a first call at session start — an agent can plan its
        evaluation strategy against the actual available evaluators
        rather than guessing or hallucinating tool names.

        Returns:
            A dict with three top-level keys:

            - ``evaluators``: every available multivon-eval evaluator,
              with its tier, what inputs it needs, and (when shipped)
              calibrated default thresholds per judge model.
            - ``traps``: every pdfhell trap family, the failure mode each
              elicits, and the expected_failure_mode metadata.
            - ``suites``: every named pdfhell suite, the (trap_family,
              seed_count) breakdown, and the suite_hash for the canonical
              version.
        """
        import multivon_eval
        from pdfhell.generators import GENERATORS, TRAP_FAMILIES
        from pdfhell.suite import SUITES

        # ─── Evaluators ───────────────────────────────────────────────────
        # Walk multivon-eval's __all__ and collect any name whose object is
        # an Evaluator subclass. Keep the introspection shallow — we want
        # JSON-friendly schema, not a full reflection dump.
        from multivon_eval.evaluators.base import Evaluator

        evaluators: list[dict[str, Any]] = []
        for name in dir(multivon_eval):
            obj = getattr(multivon_eval, name)
            try:
                is_eval = inspect.isclass(obj) and issubclass(obj, Evaluator) and obj is not Evaluator
            except TypeError:
                is_eval = False
            if not is_eval:
                continue
            entry = {
                "name": name,
                "import": f"from multivon_eval import {name}",
                "evaluator_id": getattr(obj, "name", name.lower()),
                "tier": _classify_tier(name),
                "doc": (obj.__doc__ or "").strip().split("\n")[0],
            }
            evaluators.append(entry)
        evaluators.sort(key=lambda e: (e["tier"], e["name"]))

        # ─── Trap families ────────────────────────────────────────────────
        traps: list[dict[str, Any]] = []
        for trap in TRAP_FAMILIES:
            # Materialise one example case so the agent sees the question
            # shape + expected-answer shape without having to call make().
            _, example_case = GENERATORS[trap](seed=1)
            traps.append({
                "name": trap,
                "example_question": example_case.question,
                "example_expected_answer": example_case.expected_answer,
                "failure_mode": example_case.metadata.get("expected_failure_mode", ""),
            })

        # ─── Suites ───────────────────────────────────────────────────────
        suites: list[dict[str, Any]] = []
        for spec in SUITES.values():
            suites.append({
                "name": spec.name,
                "version": spec.version,
                "suite_hash": spec.suite_hash,
                "total_cases": spec.total_cases,
                "traps": {trap: len(seeds) for trap, seeds in spec.traps.items()},
            })

        # ─── Calibration coverage ─────────────────────────────────────────
        # Surface what judges have calibrated thresholds shipped — agents
        # picking a judge should know which produce calibrated F1 numbers
        # vs which fall back to a generic 0.7 default.
        try:
            from multivon_eval.calibration import load_calibration
            calibration_entries = [
                {
                    "evaluator": e.evaluator,
                    "judge_model": e.judge_model,
                    "threshold": e.threshold,
                    "f1": e.f1,
                    "n": e.n,
                    "dataset": e.dataset,
                }
                for e in load_calibration().entries
            ]
        except Exception as exc:
            calibration_entries = [{"error": f"could not load calibration: {exc}"}]

        return {
            "server": "multivon-mcp",
            "evaluators": evaluators,
            "traps": traps,
            "suites": suites,
            "calibration": calibration_entries,
            "version": _versions(),
        }


def _classify_tier(name: str) -> str:
    """Group evaluators into the 5 tiers documented on /eval."""
    deterministic = {
        "NotEmpty", "ExactMatch", "Contains", "RegexMatch", "JSONSchemaEval",
        "WordCount", "Latency", "MaxLatency", "BLEU", "ROUGE", "StartsWith",
        "BERTScore", "Levenshtein", "ChrfScore",
    }
    llm_judge = {
        "Faithfulness", "Hallucination", "Relevance", "Coherence",
        "Toxicity", "Bias", "Summarization", "AnswerAccuracy",
        "ContextPrecision", "ContextRecall", "CustomRubric", "GEval",
        "CheckEvaluator",
    }
    agent = {
        "ToolCallAccuracy", "ToolArgumentAccuracy", "ToolCallNecessity",
        "TrajectoryEfficiency", "PlanQuality", "TaskCompletion",
        "AgentMemoryEval", "StepFaithfulness",
    }
    conversation = {
        "ConversationRelevance", "KnowledgeRetention",
        "ConversationCompleteness", "TurnConsistency",
    }
    compliance_or_multimodal = {
        "PIIEvaluator", "SchemaEvaluator", "VQAFaithfulness",
        "DocumentGrounding",
    }
    if name in deterministic:
        return "deterministic"
    if name in llm_judge:
        return "llm_judge_qag"
    if name in agent:
        return "agent_trace"
    if name in conversation:
        return "conversation"
    if name in compliance_or_multimodal:
        return "compliance_multimodal"
    return "other"


def _versions() -> dict[str, str]:
    """Return version info so an agent can pin against specific releases."""
    import multivon_eval
    import pdfhell
    from .. import __version__ as mcp_version
    return {
        "multivon_mcp": mcp_version,
        "multivon_eval": multivon_eval.__version__,
        "pdfhell": pdfhell.__version__,
    }
