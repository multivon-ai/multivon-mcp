# multivon-mcp

**MCP server that gives AI coding agents direct access to evaluation tools.** Drop into Claude Desktop, Claude Code, Cursor, Cline, or any [Model Context Protocol](https://modelcontextprotocol.io)–compatible agent.

When the agent is helping you build an LLM product, it can:

- Score a RAG output for hallucination without you writing the scaffolding
- Generate an adversarial PDF on demand to test your document AI
- Run the full pdfhell mini-suite against a model and analyse the results
- Produce a hash-chained audit pack for procurement diligence
- Discover the full evaluation capability catalog as JSON

No copy-paste, no `python -c "..."`, no asking the agent to figure out the SDK calls.

## Install

```bash
pip install multivon-mcp
```

Bare install pulls `multivon-eval`, `pdfhell`, and the MCP SDK. The provider SDKs (`anthropic`, `openai`, `google-genai`) come along too — bring your own API key in env.

## Configure your agent

### Claude Desktop / Claude Code

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "multivon": {
      "command": "multivon-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "OPENAI_API_KEY": "sk-proj-...",
        "GOOGLE_API_KEY": "AIza..."
      }
    }
  }
}
```

Restart Claude. The 9 tools become available; ask Claude `"use multivon to evaluate this RAG output"` and it figures out which tool to call.

### Cursor

`cursor.json` or via Settings → MCP:

```json
{ "mcpServers": { "multivon": { "command": "multivon-mcp" } } }
```

### Cline / OpenCode / any MCP-compatible agent

Same shape — point at the `multivon-mcp` console script.

### Local dev / debugging

```bash
mcp dev multivon_mcp.server
```

Opens the MCP Inspector UI in your browser. You can call any tool by name, see the JSON schemas, and watch the requests/responses.

## The 9 tools

| Tool | What it does | API key needed |
|---|---|---|
| `eval_discover` | Returns the full machine-readable capability catalog (evaluators, traps, suites, calibration data, versions). Call this first. | No |
| `pdfhell_make` | Generates one adversarial PDF + its answer key. Useful for inspecting what a trap looks like. | No |
| `pdfhell_run` | Runs the pdfhell adversarial-PDF benchmark against a vision model. Returns pass rate, per-trap CIs, suite hash. | Yes (vision provider) |
| `eval_faithfulness` | QAG-graded faithfulness — is a RAG output grounded in the retrieved context? | Yes (judge) |
| `eval_hallucination` | QAG-graded hallucination detection — does an output contain content NOT in context? | Yes (judge) |
| `eval_relevance` | QAG-graded answer-vs-question relevance. | Yes (judge) |
| `eval_answer_accuracy` | QAG-graded semantic equivalence vs ground truth. | Yes (judge) |
| `eval_tool_call_accuracy` | Deterministic agent tool-call correctness. No LLM. | No |
| `eval_audit_pack` | Build a hash-chained, procurement-ready ZIP from a pdfhell run. | No |

## Example session

```
User: I just shipped a RAG endpoint. Can you check it for hallucinations?

Claude: I'll use multivon to evaluate it.
        [calls eval_discover to see what's available]
        [calls eval_faithfulness with your input/context/output]

→ score: 0.667 (passed: False), threshold: 0.9
  reason: 2/3 claims grounded
    ✓ "annual renewal" — supported by context
    ✓ "30-day notice" — supported by context
    ✗ "automatic upgrade" — NOT in context

Claude: Your RAG hallucinated the "automatic upgrade" detail. The context
        doesn't mention upgrades. I'd add a Hallucination evaluator to your CI
        gate, threshold ≥0.85, and re-prompt with explicit "only use facts
        from context" instructions.
```

## Why these 9 tools (not all 44)

`eval_discover` returns the full 44-evaluator catalog, so the agent can always introspect everything. The 9 tools we expose directly are the ones agents actually call mid-edit:

- RAG checks (faithfulness, hallucination, relevance) — most common need
- Agent traces (tool_call_accuracy) — second most common
- Document AI (pdfhell.run, pdfhell.make) — for any RAG-on-PDFs flow
- Audit pack — when procurement is involved
- Discover — meta-capability for planning

Exposing all 44 evaluators as MCP tools would bloat the agent's context window and overwhelm tool-selection. If you need an evaluator that's not directly exposed, the agent can still use `multivon-eval` as a library — `eval_discover` returns the import paths.

## Dependencies

- `mcp[cli] >= 1.0` — official MCP Python SDK + the `mcp dev` inspector
- `multivon-eval >= 0.7.3` — the evaluator surface this wraps
- `pdfhell >= 0.1.0` — the adversarial-PDF benchmark this wraps

All Apache 2.0.

## License

Apache 2.0.

## Citing

```bibtex
@software{multivon_mcp,
  title  = {multivon-mcp: MCP server exposing multivon-eval + pdfhell as agent-callable tools},
  author = {Multivon},
  year   = {2026},
  url    = {https://github.com/multivon-ai/multivon-mcp},
}
```
