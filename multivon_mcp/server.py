"""FastMCP server entry point.

``multivon-mcp`` (the console script) starts this server in stdio
transport mode — exactly what Claude Desktop / Cursor / Cline expect
when configured via ``mcpServers``.

22 tools register across 6 surfaces (pdfhell · core eval · RAG · safety ·
agent workflow · multimodal · compliance · flexible · discovery). The
full list and per-tool docs come from ``eval.discover`` at runtime — that
is the source of truth, this comment is just orientation.

Why these 22 (not all 42+ evaluators in multivon-eval): the curated set
is the surface AI coding agents actually need mid-edit. The full evaluator
catalog stays available via ``eval.discover`` for agents that want to
inspect everything.
"""
from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from . import __version__
from .tools import register_all


def build_server() -> FastMCP:
    """Build and configure the FastMCP server. Factored out for tests
    that want to introspect the registered tools without actually
    serving."""
    mcp = FastMCP(
        name="multivon-mcp",
        instructions=(
            "Multivon's evaluation toolkit for AI agents. Use eval.discover() "
            "at session start to see every available evaluator + trap family. "
            "For RAG outputs, prefer eval.faithfulness + eval.hallucination. "
            "For agent traces, use eval.tool_call_accuracy. For document AI, "
            "use pdfhell.run with a vision model. All judge calls require "
            "the matching provider's API key in env "
            "(ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY)."
        ),
    )
    register_all(mcp)
    return mcp


def main() -> None:
    """Console-script entry point. Runs the server over stdio.

    For local dev / debugging, you can also run ``mcp dev multivon_mcp.server``
    which opens the MCP Inspector UI on a local port.
    """
    if "--version" in sys.argv:
        print(f"multivon-mcp {__version__}")
        return
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    main()
