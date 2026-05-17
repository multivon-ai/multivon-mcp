"""Safety MCP tools — toxicity and bias detection.

Wraps multivon-eval's QAG-graded ``Toxicity`` and ``Bias`` evaluators. Both
ask a judge model a small set of yes/no questions about the output and
return a fraction of safety-checks that passed. Score 1.0 = safe.
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register safety tools on the FastMCP server."""

    @mcp.tool()
    def eval_toxicity(
        output: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Detect harmful, offensive, or inappropriate content in an LLM output.

        QAG-graded — the judge answers four yes/no questions about whether
        the output is free of hate speech, threats, harmful instructions,
        and disrespectful tone. Score is the fraction of questions that
        pass; 1.0 = not toxic, 0.0 = toxic.

        Use this for guardrails on generated content, chatbot turns,
        or any user-facing LLM output where harmful content is a risk.

        Args:
            output: The LLM-generated text to evaluate.
            judge_model: Provider:model for the QAG judge, e.g.
                ``"anthropic:claude-haiku-4-5"`` (default), ``"openai:gpt-4o-mini"``,
                or ``"google:gemini-2.5-flash"``.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "toxicity"}``.
        """
        from multivon_eval import EvalCase, Toxicity

        judge = _parse_judge(judge_model)
        evaluator = Toxicity(judge=judge)
        case = EvalCase(input="")
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_bias(
        input: str,
        output: str,
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> dict[str, Any]:
        """Detect gender, racial, political, age, or socioeconomic bias.

        QAG-graded — the judge answers five yes/no questions about whether
        the response treats demographic groups equitably and stays
        politically neutral. Score 1.0 = no detectable bias,
        0.0 = significant bias.

        Use this for fairness audits on generated content, summarisation
        of user-submitted text, or hiring/lending-adjacent LLM pipelines.

        Args:
            input: The prompt the LLM was responding to. Bias evaluators
                use this to contextualise whether disparate treatment is
                justified (e.g. a medical question may legitimately
                discuss group-specific risk factors).
            output: The LLM-generated response.
            judge_model: Provider:model for the QAG judge.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "bias"}``.
        """
        from multivon_eval import Bias, EvalCase

        judge = _parse_judge(judge_model)
        evaluator = Bias(judge=judge)
        case = EvalCase(input=input)
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
