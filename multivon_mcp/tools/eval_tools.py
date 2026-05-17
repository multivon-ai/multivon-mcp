"""multivon-eval-specific MCP tools.

Five evaluators chosen as the highest-value agent-callable surface:

- ``eval.faithfulness`` — RAG output grounded in retrieved context?
- ``eval.hallucination`` — output contains content NOT in context?
- ``eval.relevance`` — output addresses the input question?
- ``eval.tool_call_accuracy`` — agent's tool call matches expected?
- ``eval.answer_accuracy`` — answer matches the expected ground truth?

These map to ~5 lines of Python the agent would otherwise write itself.
Wrapping them as MCP tools means the agent calls them by name instead
of generating + executing scaffolding code, which is faster, more
auditable, and matches our calibration data automatically.
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register eval tools on the FastMCP server."""

    @mcp.tool()
    def eval_faithfulness(
        input: str,
        context: str,
        output: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Evaluate whether an LLM output is grounded in the retrieved context.

        Uses multivon-eval's QAG-graded Faithfulness evaluator. Extracts
        factual claims from the output and verifies each one against the
        context. Score is the fraction of claims supported.

        Use this when a RAG pipeline returned an answer and you want to
        check the LLM didn't invent facts not present in retrieved
        documents.

        Args:
            input: The user's question.
            context: The retrieved context the LLM was given.
            output: The LLM's answer being evaluated.
            judge_model: Provider:model for the QAG judge.
                Default ``"anthropic:claude-haiku-4-5"`` (cheap + calibrated).

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str, "threshold": float}``.
        """
        from multivon_eval import EvalCase, Faithfulness, JudgeConfig

        judge = _parse_judge(judge_model)
        evaluator = Faithfulness(judge=judge)
        case = EvalCase(input=input, context=context)
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_hallucination(
        output: str,
        context: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Detect fabricated information not present in the context.

        Score 1.0 = no hallucination. Score 0.0 = significant hallucination.

        Args:
            output: The LLM output to check.
            context: The ground-truth context the output should be grounded in.
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str, "threshold": float}``.
        """
        from multivon_eval import EvalCase, Hallucination, JudgeConfig

        judge = _parse_judge(judge_model)
        evaluator = Hallucination(judge=judge)
        case = EvalCase(input="", context=context)
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_relevance(
        input: str,
        output: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Check whether an LLM output actually addresses the user's question.

        QAG-graded — generates yes/no questions about whether the output
        answers the input, stays on topic, contains relevant content.

        Args:
            input: The user's question.
            output: The LLM's response.
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str, "threshold": float}``.
        """
        from multivon_eval import EvalCase, Relevance, JudgeConfig

        judge = _parse_judge(judge_model)
        evaluator = Relevance(judge=judge)
        case = EvalCase(input=input)
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_tool_call_accuracy(
        expected_tool: str,
        actual_tool: str,
        expected_arguments: dict[str, Any] | None = None,
        actual_arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate whether an agent called the right tool with the right arguments.

        Pure deterministic — no LLM judge needed. Compares the actual tool
        name + arguments against expected.

        Args:
            expected_tool: Tool name the agent should have called.
            actual_tool: Tool name the agent actually called.
            expected_arguments: Dict of expected argument values (optional).
            actual_arguments: Dict of argument values the agent passed (optional).

        Returns:
            ``{"score": 0.0 or 1.0, "passed": bool, "reason": str}``.
        """
        tool_match = expected_tool == actual_tool
        arg_match = True
        reasons = []
        reasons.append(f"tool name: {'✓' if tool_match else '✗'} expected={expected_tool!r}, got={actual_tool!r}")
        if expected_arguments is not None or actual_arguments is not None:
            exp = expected_arguments or {}
            act = actual_arguments or {}
            for k, v in exp.items():
                if act.get(k) != v:
                    arg_match = False
                    reasons.append(f"arg {k!r}: ✗ expected={v!r}, got={act.get(k)!r}")
                else:
                    reasons.append(f"arg {k!r}: ✓")
        score = 1.0 if (tool_match and arg_match) else 0.0
        return {
            "score": score,
            "passed": score >= 0.5,
            "reason": "\n".join(reasons),
            "evaluator": "tool_call_accuracy",
        }

    @mcp.tool()
    def eval_answer_accuracy(
        expected_answer: str,
        actual_answer: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Evaluate whether an answer is semantically equivalent to the ground truth.

        QAG-graded — generates yes/no questions about whether the actual
        answer matches the meaning of the expected answer. Useful when
        string match is too strict (e.g. paraphrased correct answers).

        Args:
            expected_answer: Ground-truth answer.
            actual_answer: The LLM's answer.
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str}``.
        """
        from multivon_eval import AnswerAccuracy, EvalCase, JudgeConfig

        judge = _parse_judge(judge_model)
        evaluator = AnswerAccuracy(judge=judge)
        case = EvalCase(input="", expected_output=expected_answer)
        result = evaluator.evaluate(case, actual_answer)
        return _result_dict(result)


# ─── helpers ───────────────────────────────────────────────────────────────


def _parse_judge(spec: str):
    """Parse ``provider:model`` into a JudgeConfig.

    Mirrors pdfhell.runner.parse_model_spec but kept local so the eval
    tools work standalone if pdfhell isn't installed.
    """
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
    """Convert a multivon-eval EvalResult into a JSON-friendly dict."""
    return {
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
        "threshold": getattr(result, "threshold", None),
        "evaluator": result.evaluator,
    }
