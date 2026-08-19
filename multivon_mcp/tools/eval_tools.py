"""multivon-eval-specific MCP tools.

Five evaluators chosen as the highest-value agent-callable surface:

- ``eval_faithfulness`` — RAG output grounded in retrieved context?
- ``eval_hallucination`` — output contains content NOT in context?
- ``eval_relevance`` — output addresses the input question?
- ``eval_tool_call_accuracy`` — agent's tool call matches expected?
- ``eval_answer_accuracy`` — answer matches the expected ground truth?

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
        from multivon_eval import EvalCase, Faithfulness

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
        from multivon_eval import EvalCase, Hallucination

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
        from multivon_eval import EvalCase, Relevance

        judge = _parse_judge(judge_model)
        evaluator = Relevance(judge=judge)
        case = EvalCase(input=input)
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_tool_call_accuracy(
        expected_tool: str | None = None,
        actual_tool: str | None = None,
        expected_arguments: dict[str, Any] | None = None,
        actual_arguments: dict[str, Any] | None = None,
        expected_tool_calls: list[str] | None = None,
        agent_trace: list[dict[str, Any]] | None = None,
        require_order: bool = False,
        penalize_unexpected: bool = False,
    ) -> dict[str, Any]:
        """Evaluate whether an agent called the expected tool or tool sequence.

        Pure deterministic — no LLM judge needed. Two compatible modes:

        - Single-call mode compares ``expected_tool`` / ``actual_tool`` and
          optional argument dictionaries exactly.
        - Trace mode consumes ``expected_tool_calls`` plus the canonical
          ``agent_trace`` returned by ``eval_ingest_trace``. It can require
          order and optionally penalize unexpected calls.

        Args:
            expected_tool: Single tool name the agent should have called.
            actual_tool: Single tool name the agent actually called.
            expected_arguments: Expected arguments for single-call mode.
            actual_arguments: Actual arguments for single-call mode.
            expected_tool_calls: Expected names for trace mode. An empty list
                explicitly asserts that the agent should call no tools.
            agent_trace: Canonical step dictionaries returned by
                ``eval_ingest_trace``.
            require_order: In trace mode, require expected names in order.
            penalize_unexpected: In trace mode, lower the score for calls not
                present in ``expected_tool_calls``.

        Returns:
            ``{"score": float, "passed": bool, "reason": str,
            "evaluator": "tool_call_accuracy"}``, or an ``error`` dict when
            the arguments do not form either mode.
        """
        if agent_trace is not None or expected_tool_calls is not None:
            if expected_tool_calls is None:
                return {
                    "error": "trace mode requires expected_tool_calls; use [] to assert no tools",
                }
            from multivon_eval import EvalCase, ToolCallAccuracy

            from multivon_mcp.tools.trace_tools import _parse_canonical_steps

            case = EvalCase(
                input="",
                agent_trace=_parse_canonical_steps(agent_trace or []),
                expected_tool_calls=expected_tool_calls,
            )
            evaluator = ToolCallAccuracy(
                require_order=require_order,
                penalize_unexpected=penalize_unexpected,
            )
            return _result_dict(evaluator.evaluate(case, output=""))

        if expected_tool is None or actual_tool is None:
            return {
                "error": "single-call mode requires expected_tool and actual_tool",
            }

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
        from multivon_eval import AnswerAccuracy, EvalCase

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
