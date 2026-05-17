"""RAG-specific MCP tools — context precision and context recall.

These evaluate the *retrieval* half of a RAG pipeline (not the generation
half — for that, see ``eval_faithfulness`` / ``eval_hallucination``).

- ``eval_context_precision``: are the retrieved chunks on-topic?
- ``eval_context_recall``: does the retrieved context contain the
  information needed to answer correctly?
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register RAG retrieval-quality tools on the FastMCP server."""

    @mcp.tool()
    def eval_context_precision(
        input: str,
        context: list[str] | str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Measure whether retrieved RAG context chunks are relevant to the question.

        High precision = the retriever returned mostly on-topic chunks; low
        noise. The judge asks "is this chunk relevant?" for each chunk
        (up to 8) and scores precision = fraction marked relevant.

        Use this to diagnose retriever quality: if precision is low, your
        embedding model, chunk size, or reranker is returning noise.

        Args:
            input: The user's question.
            context: Either a list of retrieved chunks, or a single string
                with the full retrieved context (will be evaluated as one chunk).
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "context_precision"}``.
        """
        from multivon_eval import ContextPrecision, EvalCase

        judge = _parse_judge(judge_model)
        evaluator = ContextPrecision(judge=judge)
        case = EvalCase(input=input, context=context)
        result = evaluator.evaluate(case, output="")
        return _result_dict(result)

    @mcp.tool()
    def eval_context_recall(
        input: str,
        context: list[str] | str,
        expected_answer: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Measure whether retrieved context contains enough information to answer.

        High recall = the retriever found the information needed to derive
        the expected answer. The judge asks whether the expected answer
        could plausibly be reconstructed from the retrieved context alone.

        Use this when you have a labelled QA dataset and want to diagnose
        whether failures are retriever misses vs. generator errors.

        Args:
            input: The user's question.
            context: The retrieved context chunks (list or single string).
            expected_answer: The ground-truth answer the context should support.
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "context_recall"}``.
        """
        from multivon_eval import ContextRecall, EvalCase

        judge = _parse_judge(judge_model)
        evaluator = ContextRecall(judge=judge)
        case = EvalCase(
            input=input, context=context, expected_output=expected_answer
        )
        result = evaluator.evaluate(case, output="")
        return _result_dict(result)


def _parse_judge(spec: str):
    from multivon_eval import JudgeConfig

    if ":" not in spec:
        raise ValueError(
            f"judge_model must be 'provider:model', got {spec!r}. "
            "Example: anthropic:claude-haiku-4-5"
        )
    provider, model = spec.split(":", 1)
    return JudgeConfig(
        provider=provider.strip().lower(),
        model=model.strip(),
        temperature=0.0,
    )


def _result_dict(result) -> dict[str, Any]:
    return {
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
        "threshold": getattr(result, "threshold", None),
        "evaluator": result.evaluator,
    }
