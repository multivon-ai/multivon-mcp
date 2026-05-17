"""FastMCP server entry point.

``multivon-mcp`` (the console script) starts this server in stdio
transport mode — exactly what Claude Desktop / Cursor / Cline expect
when configured via ``mcpServers``.

The 8 tools registered:

  pdfhell.run                     — evaluate a vision model on the suite
  pdfhell.make                    — generate one trap PDF + answer key
  eval.faithfulness               — QAG-graded RAG faithfulness
  eval.hallucination              — QAG-graded hallucination detection
  eval.relevance                  — QAG-graded answer-vs-question relevance
  eval.tool_call_accuracy         — agent tool-call correctness (no LLM judge)
  eval.answer_accuracy            — QAG-graded semantic-equivalence
  eval.audit_pack                 — build a hash-chained audit ZIP from a run
  eval.discover                   — full machine-readable capability catalog

Why 8 (not 43): the narrow set is the surface AI coding agents actually
need mid-edit. The full evaluator catalog stays available via
``eval.discover`` for the agents that want to inspect everything.
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
