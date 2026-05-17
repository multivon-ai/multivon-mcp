"""Flexible / user-defined MCP evaluators — G-Eval and CustomRubric.

These let the agent (or its user) score an LLM output against an
arbitrary criterion. ``eval_g_eval`` does a holistic 0.0-1.0 score via
chain-of-thought rubric (good for fuzzy qualities like creativity or
style). ``eval_custom_rubric`` does QAG with user-defined yes/no
questions (good for compliance-style criteria with multiple aspects).
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register flexible / user-defined evaluation tools."""

    @mcp.tool()
    def eval_g_eval(
        input: str,
        output: str,
        criteria: str,
        name: str = "g_eval",
        runs: int = 2,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """G-Eval style holistic scoring against a plain-English criterion.

        The judge reads the criterion and the output, then returns a
        numeric score from 0.0 to 1.0 plus a short reason. To reduce
        single-sample variance the prompt is run twice by default and the
        scores averaged (position/framing bias mitigation per the
        original G-Eval paper).

        Best for fuzzy or holistic qualities: creativity, tone, style,
        helpfulness, conciseness. For criteria with multiple discrete
        aspects, prefer ``eval_custom_rubric``.

        Args:
            input: The prompt the LLM was responding to.
            output: The LLM-generated response to score.
            criteria: A plain-English description of what to score on,
                e.g. ``"Is the response concise, polite, and free of jargon?"``.
            name: Optional label for the evaluator instance (appears in
                the result dict's ``evaluator`` field).
            runs: How many independent judgements to average. Default 2.
            judge_model: Provider:model for the scoring judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": <name>}``.
        """
        from multivon_eval import EvalCase, GEval

        judge = _parse_judge(judge_model)
        evaluator = GEval(criteria=criteria, name=name, judge=judge, runs=runs)
        case = EvalCase(input=input)
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_custom_rubric(
        input: str,
        output: str,
        criteria: list[list[Any]],
        name: str = "custom_rubric",
        context: str | None = None,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Score an output against your own list of yes/no quality checks.

        Each criterion is a ``[question, expect_yes]`` pair. The judge
        answers each question with yes/no; the score is the fraction
        answered as expected. Best for compliance-style rubrics where
        each aspect should be auditable separately.

        Args:
            input: The prompt the LLM was responding to.
            output: The LLM-generated response.
            criteria: A list of ``[question_str, expect_yes_bool]`` pairs.
                Example: ``[["Does it cite a source?", true],
                ["Does it speculate beyond the source?", false]]``.
            name: Optional label for the rubric (appears in the result
                dict's ``evaluator`` field).
            context: Optional context string for the judge to consider
                (e.g. retrieved RAG context, source document).
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": <name>}``.
        """
        from multivon_eval import CustomRubric, EvalCase

        judge = _parse_judge(judge_model)
        # Normalise criteria — MCP JSON gives us lists, but CustomRubric
        # expects tuples. Validate shape while we're here.
        normalised: list[tuple[str, bool]] = []
        for entry in criteria:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise ValueError(
                    f"each criterion must be [question, expect_yes_bool]; "
                    f"got {entry!r}"
                )
            normalised.append((str(entry[0]), bool(entry[1])))
        evaluator = CustomRubric(
            criteria=normalised, name=name, judge=judge
        )
        case = EvalCase(input=input, context=context)
        result = evaluator.evaluate(case, output)
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
