"""pdfhell-specific MCP tools.

``pdfhell.run`` — evaluate a vision model against the adversarial PDF
suite. ``pdfhell.make`` — generate one trap PDF + its answer key for
inspection or downstream use.

Both tools call into pdfhell directly — same code that powers the CLI,
no shell-out. Outputs are JSON-friendly dicts so the calling agent can
parse them cleanly.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any


def register(mcp) -> None:
    """Register pdfhell tools on the FastMCP server."""

    @mcp.tool()
    def pdfhell_run(
        model: str,
        suite: str = "mini",
        workers: int = 4,
    ) -> dict[str, Any]:
        """Run the pdfhell adversarial-PDF benchmark against a vision model.

        Args:
            model: Provider:model spec, e.g. ``"anthropic:claude-sonnet-4-6"``,
                ``"openai:gpt-4o"``, ``"google:gemini-2.5-flash"``.
            suite: ``"smoke"`` (3 cases, ~10s) or ``"mini"`` (30 cases, ~$0.01
                on Flash). Default ``"mini"``.
            workers: Parallel API requests. Default 4.

        Returns:
            A dict with overall ``pass_rate``, Wilson 95% CI, per-trap-family
            pass rates and CIs, and per-case details. Suite version + hash
            included so consumers can verify the run measured the expected
            cases.

        Provider API keys come from environment variables
        (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, ``GOOGLE_API_KEY``) — not
        passed through this tool, never logged.
        """
        # Lazy-import so an env without the runner installed still loads the
        # server (the tool will surface a clear error when invoked).
        from pdfhell.runner import run_suite
        from pdfhell.suite import SUITES, build_suite

        if suite not in SUITES:
            return {
                "error": f"unknown suite {suite!r}; available: {sorted(SUITES.keys())}",
            }

        # Materialise the suite into a temp dir so we don't pollute the
        # caller's working directory. Cases for a given suite are
        # deterministic; building them every call is cheap relative to the
        # provider API spend.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cases_dir = Path(tmp) / suite
            build_suite(SUITES[suite], cases_dir)
            report = run_suite(
                cases_dir=cases_dir,
                model_spec=model,
                workers=workers,
                progress=False,
                suite_name=suite,
            )
        return report.to_dict()

    @mcp.tool()
    def pdfhell_make(
        trap: str,
        seed: int,
        return_pdf_bytes: bool = False,
    ) -> dict[str, Any]:
        """Generate one adversarial PDF + its answer key.

        Useful for an agent to inspect what a specific trap looks like
        before deciding to evaluate against it.

        Args:
            trap: Trap family. One of: ``"hidden_ocr_mismatch"``,
                ``"footnote_override"``, ``"split_table_across_pages"``.
            seed: Integer seed. Same seed → byte-identical PDF + identical
                answer key.
            return_pdf_bytes: If True, include the base64-encoded PDF bytes
                in the response. Default False — most agents want the
                question / expected answer, not the raw PDF.

        Returns:
            A dict with the case JSON (id, trap_family, question,
            expected_answer, forbidden_answers, metadata) and optionally
            the base64-encoded PDF bytes under ``pdf_base64``.
        """
        from pdfhell.generators import TRAP_FAMILIES, generate_case

        if trap not in TRAP_FAMILIES:
            return {
                "error": f"unknown trap family {trap!r}",
                "available_traps": list(TRAP_FAMILIES),
            }

        pdf_bytes, case = generate_case(trap, seed)
        result = case.to_dict()
        result["pdf_size_bytes"] = len(pdf_bytes)
        if return_pdf_bytes:
            result["pdf_base64"] = base64.b64encode(pdf_bytes).decode("ascii")
            result["pdf_mime"] = "application/pdf"
        return result
