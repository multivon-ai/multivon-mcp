"""Tool modules. Each registers a small group of related MCP tools on
the FastMCP server instance passed in."""

from .audit_tools import register as register_audit
from .compare_tools import register as register_compare
from .compliance_tools import register as register_compliance
from .discover_tools import register as register_discover
from .eval_tools import register as register_eval
from .flexible_tools import register as register_flexible
from .generate_tools import register as register_generate
from .multimodal_tools import register as register_multimodal
from .pdfhell_tools import register as register_pdfhell
from .rag_tools import register as register_rag
from .safety_tools import register as register_safety
from .trace_tools import register as register_trace


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
    register_compare(mcp)
    register_generate(mcp)
    register_trace(mcp)


__all__ = ["register_all"]
