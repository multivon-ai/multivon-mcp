"""Agent trace ingestion MCP tools.

Wraps multivon-eval's tracer adapters so an agent can score its OWN
runtime traces. Common workflow:

  1. Agent executes a tool-using trajectory (LangGraph, OpenAI Agents
     SDK, or any custom framework).
  2. Agent serialises that trajectory to a JSON-friendly dict.
  3. Agent calls ``eval_ingest_trace(trace_json, framework="langgraph")``
     to convert it into a JSON-friendly :class:`EvalCase` payload.
  4. Agent then runs the eval (e.g. ``eval_tool_call_accuracy``) over
     the resulting case.

The trace is accepted as a plain dict (not a Python object) so the tool
is safe to call over MCP's JSON transport.

Canonical universal trace shape (works for every framework):

    {
      "input": "<user prompt>",
      "expected_output": "<optional ground truth>",
      "context": "<optional retrieved context, or list of strings>",
      "expected_tool_calls": ["search", "summarize"],   # optional
      "steps": [
        {
          "thought": "...",
          "tool_calls": [
            {"name": "search", "arguments": {...}, "result": "..."}
          ],
          "output": "..."
        }
      ],
      "output": "<final assistant text — optional convenience>"
    }

Per-framework alternate shapes:

  - ``framework="langgraph"`` — accepts the canonical shape directly.
    LangGraph traces are produced live by ``LangGraphTracer`` against
    LangChain callback events; replaying those events from JSON would
    require re-instantiating LangChain message types. Pre-canonicalised
    step dicts are the honest input.

  - ``framework="openai_agents"`` — accepts either the canonical shape
    OR ``{"new_items": [...]}`` where each item is ``{"type":
    "MessageOutputItem", "raw_item": {...}}``. The ``new_items`` path
    routes through :func:`multivon_eval.integrations.openai_agents._items_to_steps`
    so the same step-segmentation rules apply.

  - ``framework="manual"`` — accepts the canonical shape. The manual
    tracer is a hand-rolled API so its "native" format IS the
    canonical step list.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any


_VALID_FRAMEWORKS = ("langgraph", "openai_agents", "manual")


def register(mcp) -> None:
    """Register trace-ingestion tools on the FastMCP server."""

    @mcp.tool()
    def eval_ingest_trace(
        trace_json: dict[str, Any],
        framework: str = "langgraph",
    ) -> dict[str, Any]:
        """Convert a JSON agent trace into a JSON-friendly EvalCase payload.

        Parses a serialised agent trajectory and returns the
        :class:`EvalCase` shape the rest of the eval pipeline (and the
        other ``eval_*`` MCP tools) expect. Use this when your agent
        has just finished a trajectory at runtime and you want to
        score that trajectory immediately — no need to re-run anything.

        Supports three frameworks:

          - ``"langgraph"`` (default): canonical universal step list
          - ``"openai_agents"``: canonical OR ``{"new_items": [...]}``
            from a ``RunResult`` you serialised
          - ``"manual"``: canonical step list

        Args:
            trace_json: The trace as a JSON-friendly dict. Must include
                ``input``; ``steps`` (or ``new_items`` for
                openai_agents) is strongly recommended.
            framework: One of ``"langgraph"``, ``"openai_agents"``,
                ``"manual"``. Defaults to ``"langgraph"``.

        Returns:
            A dict with ``input``, ``expected_output``, ``context``,
            ``expected_tool_calls``, ``agent_trace`` (list of step
            dicts), and ``metadata`` — ready to feed back into other
            ``eval_*`` MCP tools or to persist as part of an eval
            dataset.
        """
        if framework not in _VALID_FRAMEWORKS:
            return {
                "error": f"unknown framework: {framework!r}",
                "valid_frameworks": list(_VALID_FRAMEWORKS),
            }

        # openai_agents has an alternate native shape — route to its
        # parser so identical step-segmentation rules apply.
        if framework == "openai_agents" and "new_items" in trace_json:
            steps = _parse_openai_agents_new_items(trace_json["new_items"])
        else:
            steps = _parse_canonical_steps(trace_json.get("steps") or [])

        return {
            "input": trace_json.get("input", ""),
            "expected_output": trace_json.get("expected_output"),
            "context": trace_json.get("context"),
            "expected_tool_calls": trace_json.get("expected_tool_calls"),
            "agent_trace": [_step_to_dict(s) for s in steps],
            "output": trace_json.get("output", ""),
            "metadata": dict(trace_json.get("metadata") or {}),
            "framework": framework,
        }


# ─── parsers ────────────────────────────────────────────────────────────


def _parse_canonical_steps(raw_steps: list[dict[str, Any]]):
    """Parse the universal ``{thought, tool_calls, output}`` step list.

    Returns a list of :class:`AgentStep` objects (lazy-imported so the
    server can boot even if multivon-eval's optional sub-deps aren't
    installed in some sub-tree).
    """
    from multivon_eval.case import AgentStep, ToolCall

    steps = []
    for rs in raw_steps:
        tcs = []
        for tc in rs.get("tool_calls") or []:
            tcs.append(ToolCall(
                name=tc.get("name", "unknown"),
                arguments=tc.get("arguments") or {},
                result=tc.get("result"),
            ))
        steps.append(AgentStep(
            thought=rs.get("thought", "") or "",
            tool_calls=tcs,
            output=rs.get("output", "") or "",
        ))
    return steps


def _parse_openai_agents_new_items(items: list[dict[str, Any]]):
    """Parse a serialised OpenAI Agents ``RunResult.new_items`` list.

    ``_items_to_steps`` matches item classes by ``type(item).__name__``,
    so we wrap each dict in a dynamically-named SimpleNamespace
    subclass and let the SDK-aware parser do the rest.
    """
    from multivon_eval.integrations.openai_agents import _items_to_steps

    wrapped = []
    for raw in items:
        cls_name = raw.get("type") or raw.get("class") or "Unknown"
        # Carry every field except the discriminator onto the stub so
        # the parser sees raw.raw_item / raw.output / etc.
        attrs = {k: _wrap_value(v) for k, v in raw.items() if k not in ("type", "class")}
        StubCls = type(cls_name, (SimpleNamespace,), {})
        wrapped.append(StubCls(**attrs))
    return _items_to_steps(wrapped)


def _wrap_value(value: Any) -> Any:
    """Recursively turn JSON dicts into SimpleNamespace objects.

    The openai_agents parser reads BOTH attribute and dict access via
    its ``_attr_or_key`` helper, so dicts technically pass through —
    but nested attribute access (``raw.content[0].text``) needs real
    object attributes. Lists pass through with each element wrapped.
    """
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _wrap_value(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_wrap_value(v) for v in value]
    return value


def _step_to_dict(step) -> dict[str, Any]:
    """Convert an :class:`AgentStep` to a JSON-friendly dict."""
    return {
        "thought": step.thought,
        "tool_calls": [
            {"name": tc.name, "arguments": tc.arguments, "result": tc.result}
            for tc in step.tool_calls
        ],
        "output": step.output,
    }
