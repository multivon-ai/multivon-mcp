"""Tool modules. Each registers a small group of related MCP tools on
the FastMCP server instance passed in."""

from .pdfhell_tools import register as register_pdfhell
from .eval_tools import register as register_eval
from .audit_tools import register as register_audit
from .discover_tools import register as register_discover


def register_all(mcp) -> None:
    """Register every tool group on the FastMCP server."""
    register_pdfhell(mcp)
    register_eval(mcp)
    register_audit(mcp)
    register_discover(mcp)


__all__ = ["register_all"]
