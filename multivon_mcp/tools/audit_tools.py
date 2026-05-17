"""Audit-pack MCP tool.

Wraps pdfhell's audit-pack generation. The agent calls this after a
pdfhell run to produce a procurement-ready ZIP with hash-chained
manifest, PDFs, answer keys, JUnit XML, and a human-readable README.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def register(mcp) -> None:
    """Register audit tools on the FastMCP server."""

    @mcp.tool()
    def eval_audit_pack(
        run_json_path: str,
        cases_dir: str,
        output_zip_path: str,
    ) -> dict[str, Any]:
        """Build a hash-chained audit ZIP from a pdfhell run.

        Combines the run JSON, the case PDFs + answer keys, JUnit XML,
        and a SHA-256 manifest into one downloadable ZIP. Suitable for
        attaching to a procurement diligence appendix.

        Args:
            run_json_path: Path to a pdfhell run JSON (from ``pdfhell run --out``).
            cases_dir: Directory containing the case PDFs + answer keys that
                were evaluated. Same dir the run used.
            output_zip_path: Where to write the audit ZIP.

        Returns:
            ``{"path": "/abs/path/to.zip", "size_bytes": N, "manifest": {...}}``.
            The manifest dict mirrors the one inside the ZIP — useful for
            an agent that wants to verify the contents without opening
            the ZIP itself.
        """
        from pdfhell.auditpack import build_audit_pack
        from pdfhell.scorer import SuiteReport, CaseScore

        run_path = Path(run_json_path).expanduser().resolve()
        if not run_path.is_file():
            return {"error": f"run JSON not found: {run_path}"}
        cases_path = Path(cases_dir).expanduser().resolve()
        if not cases_path.is_dir():
            return {"error": f"cases dir not found: {cases_path}"}

        # Reconstruct a SuiteReport from the JSON. We only need the fields
        # the audit-pack builder reads.
        raw = json.loads(run_path.read_text(encoding="utf-8"))
        cases = [
            CaseScore(
                case_id=c["case_id"],
                trap_family=c["trap_family"],
                correct=bool(c["correct"]),
                fell_for_trap=bool(c.get("fell_for_trap", False)),
                refused=bool(c.get("refused", False)),
                matched_expected=bool(c.get("matched_expected", False)),
                matched_forbidden=list(c.get("matched_forbidden", [])),
                model_output=c.get("model_output", ""),
                expected=c.get("expected", ""),
                failure_mode=c.get("failure_mode", ""),
            )
            for c in raw.get("cases", [])
        ]
        report = SuiteReport(
            model=raw["model"],
            suite=raw["suite"],
            n=raw["n"],
            pass_rate=raw["pass_rate"],
            per_trap_pass=raw.get("per_trap_pass", {}),
            per_trap_fell_for_trap=raw.get("per_trap_fell_for_trap", {}),
            refused_rate=raw.get("refused_rate", 0.0),
            cases=cases,
            suite_version=raw.get("suite_version", ""),
            suite_hash=raw.get("suite_hash", ""),
        )

        out_path = Path(output_zip_path).expanduser().resolve()
        build_audit_pack(report, cases_path, out_path)

        # Return a compact manifest summary the agent can use directly.
        import zipfile
        with zipfile.ZipFile(out_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        return {
            "path": str(out_path),
            "size_bytes": out_path.stat().st_size,
            "manifest": {
                "pdfhell_version": manifest["pdfhell_version"],
                "model": manifest["model"],
                "suite": manifest["suite"],
                "suite_version": manifest.get("suite_version", ""),
                "suite_hash": manifest.get("suite_hash", ""),
                "n": manifest["n"],
                "passed": manifest["passed"],
                "pass_rate": manifest["pass_rate"],
                "pass_rate_ci_95": manifest.get("pass_rate_ci_95", []),
                "file_count": len(manifest["files"]),
            },
        }
