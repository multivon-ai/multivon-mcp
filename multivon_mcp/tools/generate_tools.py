"""Eval case generation MCP tools.

Wraps :func:`multivon_eval.generate.generate_from_text` so an agent can
turn a chunk of source text (FAQ, docs, knowledge base) into a list of
ready-to-run :class:`EvalCase` JSONs without writing scaffolding code.

The judge model is configurable but defaults to a cheap, calibrated
default so a curious agent can fire-and-forget. This tool DOES make
LLM judge calls — callers need a provider API key in env (e.g.
``ANTHROPIC_API_KEY``).
"""
from __future__ import annotations

import os
from typing import Any


def register(mcp) -> None:
    """Register generation tools on the FastMCP server."""

    @mcp.tool()
    def eval_generate_cases(
        from_text: str,
        n: int = 10,
        task: str = "qa",
        judge_model: str = "anthropic:claude-haiku-4-5",
    ) -> list[dict[str, Any]]:
        """Generate synthetic eval cases from a source text.

        Calls multivon-eval's synthetic generator to produce ``n`` eval
        cases from raw text (docs, FAQ, knowledge base). Each case has
        an ``input`` (question), ``expected_output`` (ground-truth
        answer), and ``context`` (the source excerpt the answer was
        grounded in). Eliminates the cold-start problem when building
        a new eval suite from scratch.

        Requires a provider API key in env so the underlying judge can
        propose question/answer pairs.

        Args:
            from_text: Source text to generate cases from (e.g. FAQ,
                docs chunk, knowledge base article).
            n: Number of cases to generate. Default 10.
            task: One of ``"qa"`` (question/answer pairs — default),
                ``"summarization"`` (text + expected summary), or
                ``"hallucination"`` (faithful answer + ``expected_output
                = "faithful"`` for hallucination benchmarks).
            judge_model: Provider:model string used to *generate* the
                cases. The generator calls this judge under the hood;
                it does NOT need to match the judge you eventually use
                to evaluate the cases. Default
                ``"anthropic:claude-haiku-4-5"``.

        Returns:
            A list of dicts ``{"input", "expected_output", "context",
            "metadata"}`` ready to feed into ``EvalCase(**d)`` or to
            persist as a JSONL eval dataset.
        """
        # Lazy imports — keep the server importable when multivon-eval's
        # optional sub-deps aren't installed.
        from multivon_eval.generate import generate_from_text

        # The generator's underlying ``_judge_call`` resolves its judge
        # from the ``JUDGE_PROVIDER`` + ``JUDGE_MODEL`` env vars. Push
        # our caller-provided spec into those so the generator picks
        # them up, restoring on exit so we don't leak state into the
        # rest of the server process.
        if ":" not in judge_model:
            raise ValueError(
                f"judge_model must be 'provider:model', got {judge_model!r}. "
                "Example: anthropic:claude-haiku-4-5"
            )
        provider, model = judge_model.split(":", 1)
        prev_provider = os.environ.get("JUDGE_PROVIDER")
        prev_model = os.environ.get("JUDGE_MODEL")
        os.environ["JUDGE_PROVIDER"] = provider.strip().lower()
        os.environ["JUDGE_MODEL"] = model.strip()
        try:
            cases = generate_from_text(from_text, n=n, task=task)
        finally:
            _restore_env("JUDGE_PROVIDER", prev_provider)
            _restore_env("JUDGE_MODEL", prev_model)

        out: list[dict[str, Any]] = []
        for c in cases:
            out.append({
                "input": c.input,
                "expected_output": c.expected_output,
                "context": c.context_str() if c.context is not None else None,
                "metadata": dict(c.metadata or {}),
            })
        return out


def _restore_env(key: str, prev: str | None) -> None:
    """Restore an env var to its previous value (or remove if it was unset)."""
    if prev is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = prev
