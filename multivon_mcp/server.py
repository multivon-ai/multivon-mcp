"""FastMCP server entry point.

``multivon-mcp`` (the console script) starts this server in stdio
transport mode — exactly what Claude Desktop / Cursor / Cline expect
when configured via ``mcpServers``.

22 tools register across 9 surfaces (pdfhell · core eval · RAG · safety ·
agent workflow · multimodal · compliance · flexible · discovery). The
full list and per-tool docs come from ``eval_discover`` at runtime — that
is the source of truth, this comment is just orientation.

Why these 22 (not all 44 evaluators in multivon-eval): the curated set
is the surface AI coding agents actually need mid-edit. The full evaluator
catalog stays available via ``eval_discover`` for agents that want to
inspect everything.
"""
from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

# Absolute imports (not relative) so ``mcp dev multivon_mcp/server.py``
# can exec this file standalone — the Inspector loads it by file path,
# outside the package context, where relative imports would fail.
from multivon_mcp import __version__
from multivon_mcp.tools import register_all


def build_server() -> FastMCP:
    """Build and configure the FastMCP server. Factored out for tests
    that want to introspect the registered tools without actually
    serving."""
    mcp = FastMCP(
        name="multivon-mcp",
        instructions=(
            "Multivon's evaluation toolkit for AI agents. Use eval_discover() "
            "at session start to see every available evaluator + trap family. "
            "For RAG outputs, prefer eval_faithfulness + eval_hallucination. "
            "For agent traces, use eval_tool_call_accuracy. For document AI, "
            "use pdfhell_run with a vision model. All judge calls require "
            "the matching provider's API key in env "
            "(ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY)."
        ),
    )
    # FastMCP's constructor doesn't expose version, so serverInfo would
    # otherwise report the MCP SDK's version instead of ours.
    mcp._mcp_server.version = __version__
    register_all(mcp)
    return mcp


# Module-level server instance so ``mcp dev multivon_mcp/server.py`` works —
# the MCP Inspector's loader looks for a module-level ``mcp``/``server``/``app``
# variable. build_server() only constructs FastMCP and registers tool
# functions (lazy imports inside each tool), so this is import-cheap and
# side-effect free.
mcp = build_server()


def main() -> None:
    """Console-script entry point. Runs the server over stdio.

    For local dev / debugging, you can also run
    ``mcp dev multivon_mcp/server.py`` which opens the MCP Inspector UI on
    a local port.
    """
    if "--version" in sys.argv:
        print(f"multivon-mcp {__version__}")
        return
    mcp.run()


if __name__ == "__main__":
    main()
