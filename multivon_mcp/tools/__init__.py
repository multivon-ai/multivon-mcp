"""Tool modules. Each registers a small group of related MCP tools on
the FastMCP server instance passed in."""

from .pdfhell_tools import register as register_pdfhell
from .eval_tools import register as register_eval
from .audit_tools import register as register_audit
from .discover_tools import register as register_discover
from .compliance_tools import register as register_compliance
from .safety_tools import register as register_safety
from .rag_tools import register as register_rag
from .flexible_tools import register as register_flexible
from .multimodal_tools import register as register_multimodal


def register_all(mcp) -> None:
    """Register every tool group on the FastMCP server."""
    register_pdfhell(mcp)
    register_eval(mcp)
    register_audit(mcp)
    register_discover(mcp)
    register_compliance(mcp)
    register_safety(mcp)
    register_rag(mcp)
    register_flexible(mcp)
    register_multimodal(mcp)


__all__ = ["register_all"]
