"""Compare saved reports and apply the engine's explicit acceptance contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def register(mcp) -> None:
    """Register comparison tools on the FastMCP server."""

    @mcp.tool()
    def eval_compare_runs(
        baseline_json_path: str,
        new_json_path: str,
    ) -> dict[str, Any]:
        """Compare two multivon-eval report JSONs and return a structured diff.

        Loads both reports from disk (the JSON produced by
        ``EvalReport.to_json()``), pairs cases by stable ID and case digest, and
        returns pass-rate / average-score deltas plus the per-case
        ``regressions`` and ``improvements`` lists. Includes a McNemar
        p-value only when pairing evidence supports it. A large p-value
        does not establish equivalence. Legacy reports remain diagnostic.

        Use this when you've made a prompt / retrieval / model change
        and want to know if the new run actually improved over the
        baseline — not just on aggregate, but case-by-case.

        Args:
            baseline_json_path: Filesystem path to the baseline report
                JSON (e.g. ``"runs/baseline.json"``).
            new_json_path: Filesystem path to the new / proposal report
                JSON to compare against the baseline.

        Returns:
            A dict with:
              - ``pass_rate_delta``: float, new - baseline pass rate
              - ``avg_score_delta``: float, new - baseline average score
              - ``regressions``: list of dicts with ``input``,
                ``baseline_status``, ``proposal_status``,
                ``baseline_score``, ``proposal_score``
              - ``improvements``: same shape as regressions
              - ``mcnemar_p_value``: float or null — paired-test p-value
              - ``baseline`` / ``proposal``: summary blocks with
                ``name``, ``pass_rate``, ``avg_score``, ``errors``,
                ``flaky``
              - ``paired_count`` / ``added_count`` / ``removed_count``:
                pairing stats so the caller can see how many cases
                lined up vs. drifted between runs
        """
        from multivon_eval.compare import compare_reports
        from multivon_eval.result import EvalReport

        baseline = EvalReport.from_dict(
            json.loads(Path(baseline_json_path).read_text(encoding="utf-8"))
        )
        proposal = EvalReport.from_dict(
            json.loads(Path(new_json_path).read_text(encoding="utf-8"))
        )

        diff = compare_reports(baseline, proposal)
        d = diff.to_dict()

        # Flatten the multivon-eval ReportDiff into a shape that matches
        # this MCP tool's contract — agents shouldn't have to know about
        # ``deltas.pass_rate`` vs ``pass_rate_delta``.
        return {
            "pass_rate_delta": d["deltas"]["pass_rate"],
            "avg_score_delta": d["deltas"]["avg_score"],
            "errors_delta": d["deltas"]["errors"],
            "flaky_delta": d["deltas"]["flaky"],
            "regressions": d["regressions"],
            "improvements": d["improvements"],
            "mcnemar_p_value": d.get("mcnemar_p"),
            "identity_verified": d["identity_verified"],
            "identity_issues": d["identity_issues"],
            "interpretation": "Exploratory paired comparison, not an absolute acceptance decision",
            "baseline": d["baseline"],
            "proposal": d["proposal"],
            "paired_count": d["paired_count"],
            "added_count": d["added_count"],
            "removed_count": d["removed_count"],
        }

    @mcp.tool()
    def eval_acceptance_report(report_json_path: str, policy_json_path: str) -> dict[str, Any]:
        """Apply a versioned acceptance policy to saved evidence without model calls.

        Read a full EvalReport JSON and a multivon.policy/v1 JSON policy. Return
        accept, reject, or indeterminate, the policy digest, measured coverage,
        per-slice results and findings. Missing required checks or trials cannot
        pass. A known quality failure can reject even with incomplete evidence.
        The returned exit_code is the policy result, not the MCP process status.
        Input/configuration failures are MCP tool errors, never accepted reports.
        """
        from multivon_eval import AcceptancePolicy, EvalReport
        report = EvalReport.from_dict(json.loads(Path(report_json_path).read_text(encoding="utf-8")))
        policy = AcceptancePolicy.from_dict(json.loads(Path(policy_json_path).read_text(encoding="utf-8")))
        return policy.evaluate(report).to_dict()
