"""Actual stdio MCP handshake, tool schemas, results and error boundaries."""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from multivon_eval import AcceptancePolicy, CheckRequirement, EvalCase, EvalSuite, ExactMatch
from multivon_mcp import __version__


def test_stdio_evidence_workflow(tmp_path):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(AcceptancePolicy((CheckRequirement("exact_match"),)).to_dict()))
    report_paths = {}
    for label, answer in [("accept", "yes"), ("reject", "wrong")]:
        report = EvalSuite("contract").add_case(EvalCase("q", "yes")).add_evaluator(ExactMatch()).run(
            lambda _, value=answer: value, verbose=False)
        path = tmp_path / f"{label}.json"
        report.save_json(str(path))
        report_paths[label] = path
    incomplete = json.loads(report_paths["accept"].read_text())
    incomplete["cases"][0]["trials"] = []
    report_paths["indeterminate"] = tmp_path / "incomplete.json"
    report_paths["indeterminate"].write_text(json.dumps(incomplete))

    async def exercise():
        params = StdioServerParameters(command=sys.executable,
            args=["-m", "multivon_mcp.server"], cwd=str(Path(__file__).resolve().parent.parent))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=20)) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.version == __version__
                catalog = await session.list_tools()
                assert len(catalog.tools) == 23
                assert any(t.name == "eval_acceptance_report" for t in catalog.tools)
                for expected, path in report_paths.items():
                    result = await session.call_tool("eval_acceptance_report", {
                        "report_json_path": str(path), "policy_json_path": str(policy_path)})
                    assert not result.isError
                    assert result.structuredContent["decision"] == expected
                    assert result.structuredContent["exit_code"] == {"accept": 0, "reject": 1, "indeterminate": 2}[expected]
                invalid = await session.call_tool("eval_acceptance_report", {
                    "report_json_path": str(tmp_path / "missing.json"), "policy_json_path": str(policy_path)})
                assert invalid.isError
                comparison = await session.call_tool("eval_compare_runs", {
                    "baseline_json_path": str(report_paths["accept"]),
                    "new_json_path": str(report_paths["indeterminate"])})
                assert not comparison.isError
                assert comparison.structuredContent["identity_verified"] is False
                assert comparison.structuredContent["identity_issues"]
                assert comparison.structuredContent["mcnemar_p_value"] is None

                missing = await session.call_tool("eval_tool_call_accuracy", {"expected_tool_calls": []})
                assert not missing.isError
                assert missing.structuredContent["status"] == "skipped"
                assert missing.structuredContent["passed"] is None
                assert missing.structuredContent["score"] is None
                assert not missing.structuredContent["measured"]
                empty = await session.call_tool("eval_tool_call_accuracy", {"expected_tool_calls": [], "agent_trace": []})
                assert empty.structuredContent["passed"] is True
                assert empty.structuredContent["measured"] is True

                # A nonexistent argument is not an explicit null; extra args
                # and booleans substituted for numbers are also real mismatches.
                for expected, actual in [({"x": None}, {}), ({}, {"extra": 1}), ({"x": 1}, {"x": True})]:
                    accuracy = await session.call_tool("eval_tool_call_accuracy", {
                        "expected_tool": "write", "actual_tool": "write",
                        "expected_arguments": expected, "actual_arguments": actual})
                    assert not accuracy.isError
                    assert accuracy.structuredContent["passed"] is False
                absent = await session.call_tool("eval_ingest_trace", {"trace_json": {"input": "q"}, "framework": "manual"})
                assert absent.isError
    asyncio.run(exercise())
