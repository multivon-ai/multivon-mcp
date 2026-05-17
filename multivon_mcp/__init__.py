"""multivon-mcp — agent-callable evaluation tools.

Drop into Claude Desktop, Cursor, Cline, or any MCP-compatible agent
to give it direct access to multivon-eval + pdfhell tools without
shelling out to ``python -c`` or copy-pasting code.

Quickstart::

    pip install multivon-mcp

    # Claude Desktop / Claude Code config (mcpServers):
    {
      "mcpServers": {
        "multivon": {"command": "multivon-mcp"}
      }
    }

After registering, ask Claude:
    "use multivon to evaluate this RAG output for faithfulness"

The agent discovers the 8 available tools via the MCP capabilities
handshake and calls them directly.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
