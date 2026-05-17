"""Server-level tests — tool registration, schema correctness, version.

We don't spin up the stdio transport in tests (that's an integration
concern). We verify the registered tools have correct names and
schemas via FastMCP's introspection API.
"""
from __future__ import annotations

import asyncio

import pytest

from multivon_mcp.server import build_server


EXPECTED_TOOLS = {
    "pdfhell_run",
    "pdfhell_make",
    "eval_faithfulness",
    "eval_hallucination",
    "eval_relevance",
    "eval_tool_call_accuracy",
    "eval_answer_accuracy",
    "eval_audit_pack",
    "eval_discover",
    # 0.2.0 — compliance
    "eval_pii_detection",
    "eval_schema_compliance",
    # 0.2.0 — safety
    "eval_toxicity",
    "eval_bias",
    # 0.2.0 — RAG retrieval quality
    "eval_context_precision",
    "eval_context_recall",
    # 0.2.0 — flexible / user-defined
    "eval_g_eval",
    "eval_custom_rubric",
    # 0.2.0 — multimodal
    "eval_vqa_faithfulness",
    "eval_document_grounding",
    # 0.3.0 — agent workflows
    "eval_compare_runs",
    "eval_generate_cases",
    "eval_ingest_trace",
}


def _tools():
    mcp = build_server()
    return asyncio.run(mcp.list_tools())


def test_all_expected_tools_registered():
    names = {t.name for t in _tools()}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {missing}"


def test_every_tool_has_a_description():
    for t in _tools():
        assert t.description, f"tool {t.name} has no description"
        # Each description must be more than a single line — agents use
        # this to decide whether to call the tool.
        assert len(t.description) > 60, (
            f"tool {t.name} description is suspiciously short ({len(t.description)} chars)"
        )


def test_eval_discover_executes_locally():
    """eval_discover doesn't need provider API keys — it should run
    end-to-end and return a populated catalog."""
    from multivon_mcp.tools.discover_tools import register
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("test")
    register(mcp)
    # Call the underlying impl directly by looking up the tool function.
    # FastMCP wraps tools in metadata; we just invoke the registered fn.
    tools = asyncio.run(mcp.list_tools())
    discover = next(t for t in tools if t.name == "eval_discover")
    assert discover is not None
    # Invoke via the call_tool API.
    result = asyncio.run(mcp.call_tool("eval_discover", {}))
    # FastMCP returns a list of content blocks (TextContent) — pull the JSON
    # payload out of the first block.
    import json
    # Newer FastMCP returns (content, structured_data) tuple; older returns just content.
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        catalog = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        catalog = json.loads(text)
    assert "evaluators" in catalog
    assert "traps" in catalog
    assert "suites" in catalog
    assert len(catalog["evaluators"]) >= 30  # we ship 43+
    assert len(catalog["traps"]) == 3
    # Suites should include both smoke + mini with versioned names.
    suite_names = {s["name"] for s in catalog["suites"]}
    assert "smoke" in suite_names
    assert "mini" in suite_names


def test_pdfhell_make_executes_locally():
    """pdfhell_make doesn't need provider keys either. Tests the tool
    can be invoked through the MCP machinery, not just imported."""
    import json
    mcp = build_server()
    result = asyncio.run(
        mcp.call_tool(
            "pdfhell_make",
            {"trap": "hidden_ocr_mismatch", "seed": 42},
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        case = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        case = json.loads(text)
    assert case["trap_family"] == "hidden_ocr_mismatch"
    assert case["seed"] == 42
    assert case["expected_answer"]
    assert case["pdf_size_bytes"] > 1000


def test_eval_tool_call_accuracy_no_api_key_needed():
    """tool_call_accuracy is deterministic — no LLM. Should work in any
    environment, including CI without provider keys."""
    import json
    mcp = build_server()
    result = asyncio.run(
        mcp.call_tool(
            "eval_tool_call_accuracy",
            {
                "expected_tool": "search_loads",
                "actual_tool": "search_loads",
                "expected_arguments": {"region": "midwest"},
                "actual_arguments": {"region": "midwest"},
            },
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        out = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        out = json.loads(text)
    assert out["score"] == 1.0
    assert out["passed"] is True


def test_eval_compare_runs_executes_locally(tmp_path):
    """eval_compare_runs only reads JSON files + computes a structured
    diff — no API key needed. Feed it two minimal reports and verify
    the diff dict shape."""
    import json
    baseline = {
        "suite": "baseline",
        "model": "test-model",
        "cases": [
            {
                "input": "Q1", "output": "A1", "status": "passed",
                "passed": True, "score": 1.0, "score_std": 0.0,
                "all_scores": [1.0], "run_pass_rate": 1.0, "is_flaky": False,
                "runs": 1, "retry_attempts": 0, "retry_errors": [],
                "latency_ms": 0.0, "tags": [], "skipped": False,
                "evaluators": [{"name": "fake", "score": 1.0, "passed": True, "reason": ""}],
            },
            {
                "input": "Q2", "output": "A2", "status": "passed",
                "passed": True, "score": 1.0, "score_std": 0.0,
                "all_scores": [1.0], "run_pass_rate": 1.0, "is_flaky": False,
                "runs": 1, "retry_attempts": 0, "retry_errors": [],
                "latency_ms": 0.0, "tags": [], "skipped": False,
                "evaluators": [{"name": "fake", "score": 1.0, "passed": True, "reason": ""}],
            },
        ],
    }
    proposal = {
        "suite": "proposal",
        "model": "test-model",
        "cases": [
            {
                "input": "Q1", "output": "A1", "status": "passed",
                "passed": True, "score": 1.0, "score_std": 0.0,
                "all_scores": [1.0], "run_pass_rate": 1.0, "is_flaky": False,
                "runs": 1, "retry_attempts": 0, "retry_errors": [],
                "latency_ms": 0.0, "tags": [], "skipped": False,
                "evaluators": [{"name": "fake", "score": 1.0, "passed": True, "reason": ""}],
            },
            {
                # Q2 regressed: pass → fail
                "input": "Q2", "output": "wrong", "status": "failed",
                "passed": False, "score": 0.0, "score_std": 0.0,
                "all_scores": [0.0], "run_pass_rate": 0.0, "is_flaky": False,
                "runs": 1, "retry_attempts": 0, "retry_errors": [],
                "latency_ms": 0.0, "tags": [], "skipped": False,
                "evaluators": [{"name": "fake", "score": 0.0, "passed": False, "reason": ""}],
            },
        ],
    }
    baseline_path = tmp_path / "baseline.json"
    proposal_path = tmp_path / "proposal.json"
    baseline_path.write_text(json.dumps(baseline))
    proposal_path.write_text(json.dumps(proposal))

    mcp = build_server()
    result = asyncio.run(
        mcp.call_tool(
            "eval_compare_runs",
            {
                "baseline_json_path": str(baseline_path),
                "new_json_path": str(proposal_path),
            },
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        out = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        out = json.loads(text)

    assert "pass_rate_delta" in out
    assert "avg_score_delta" in out
    assert "regressions" in out
    assert "improvements" in out
    # Q2 regressed in our fixture.
    assert len(out["regressions"]) == 1
    assert out["regressions"][0]["input"] == "Q2"
    assert out["pass_rate_delta"] < 0  # got worse
    assert out["paired_count"] == 2


def test_eval_ingest_trace_manual_executes_locally():
    """eval_ingest_trace is pure parsing — no API key needed. Feed it
    a minimal canonical trace dict and verify the AgentStep shape."""
    import json
    mcp = build_server()
    trace = {
        "input": "What's the weather in Chicago?",
        "expected_output": "It's sunny.",
        "steps": [
            {
                "thought": "I should call the weather tool.",
                "tool_calls": [
                    {"name": "get_weather", "arguments": {"city": "Chicago"}, "result": "sunny, 72F"},
                ],
                "output": "It's sunny in Chicago, 72F.",
            },
        ],
        "output": "It's sunny in Chicago, 72F.",
    }
    result = asyncio.run(
        mcp.call_tool(
            "eval_ingest_trace",
            {"trace_json": trace, "framework": "manual"},
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        out = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        out = json.loads(text)

    assert out["input"] == "What's the weather in Chicago?"
    assert out["framework"] == "manual"
    assert len(out["agent_trace"]) == 1
    step = out["agent_trace"][0]
    assert step["thought"] == "I should call the weather tool."
    assert len(step["tool_calls"]) == 1
    assert step["tool_calls"][0]["name"] == "get_weather"
    assert step["tool_calls"][0]["arguments"] == {"city": "Chicago"}
    assert step["tool_calls"][0]["result"] == "sunny, 72F"


def test_eval_ingest_trace_unknown_framework_returns_error():
    """Bad framework name should be a clean error, not an exception."""
    import json
    mcp = build_server()
    result = asyncio.run(
        mcp.call_tool(
            "eval_ingest_trace",
            {"trace_json": {"input": "x"}, "framework": "not_a_real_framework"},
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        out = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        out = json.loads(text)
    assert "error" in out
    assert "valid_frameworks" in out


def test_eval_generate_cases_registered():
    """eval_generate_cases requires an LLM call to actually generate
    cases — we can't run it offline. Just verify it's registered with
    a non-trivial description so an agent can decide whether to call it.
    """
    tools = _tools()
    gen = next((t for t in tools if t.name == "eval_generate_cases"), None)
    assert gen is not None, "eval_generate_cases not registered"
    assert "generate" in gen.description.lower()
    assert len(gen.description) > 60


def test_pdfhell_make_unknown_trap_returns_error_dict():
    import json
    mcp = build_server()
    result = asyncio.run(
        mcp.call_tool(
            "pdfhell_make",
            {"trap": "not_a_real_trap", "seed": 1},
        )
    )
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        out = structured
    else:
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        out = json.loads(text)
    assert "error" in out
    assert "available_traps" in out
