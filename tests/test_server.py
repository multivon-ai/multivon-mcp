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
