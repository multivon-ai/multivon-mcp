# multivon-mcp

[![PyPI](https://img.shields.io/pypi/v/multivon-mcp.svg)](https://pypi.org/project/multivon-mcp)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://pypi.org/project/multivon-mcp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/multivon-mcp/month)](https://pepy.tech/project/multivon-mcp)

**[Docs](https://docs.multivon.ai/mcp)** · [Website](https://multivon.ai/agents) · [PyPI](https://pypi.org/project/multivon-mcp) · [multivon-eval (engine)](https://github.com/multivon-ai/multivon-eval)

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

Restart Claude. The 22 tools become available; ask Claude `"use multivon to evaluate this RAG output"` and it figures out which tool to call.

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

## The 22 tools

### Discovery & document AI

| Tool | What it does | API key |
|---|---|---|
| `eval_discover` | Full machine-readable capability catalog (evaluators, traps, suites, calibration data, versions). Call first. | No |
| `pdfhell_make` | Generate one adversarial PDF + its answer key. | No |
| `pdfhell_run` | Run the pdfhell adversarial-PDF benchmark against a vision model. Returns pass rate, per-trap CIs, suite hash. | Yes (vision) |
| `eval_audit_pack` | Build a hash-chained, procurement-ready ZIP from a pdfhell run. | No |

### RAG generation & retrieval

| Tool | What it does | API key |
|---|---|---|
| `eval_faithfulness` | QAG-graded faithfulness — is a RAG output grounded in the retrieved context? | Yes |
| `eval_hallucination` | QAG-graded hallucination — does the output contain content NOT in context? | Yes |
| `eval_relevance` | QAG-graded answer-vs-question relevance. | Yes |
| `eval_answer_accuracy` | QAG-graded semantic equivalence vs ground truth. | Yes |
| `eval_context_precision` | RAG retrieval quality — are the retrieved chunks on-topic? | Yes |
| `eval_context_recall` | RAG retrieval completeness — does context contain enough info to answer? | Yes |

### Safety, compliance, fairness

| Tool | What it does | API key |
|---|---|---|
| `eval_toxicity` | QAG-graded toxicity / harmful-content detection. | Yes |
| `eval_bias` | QAG-graded bias across gender, race, politics, age, socioeconomic axes. | Yes |
| `eval_pii_detection` | Local-only regex scan for PII (GDPR / CCPA / PIPEDA / HIPAA packs). | No |
| `eval_schema_compliance` | Validate an LLM output against a JSON Schema. | No |

### Agent & multimodal

| Tool | What it does | API key |
|---|---|---|
| `eval_tool_call_accuracy` | Deterministic agent tool-call correctness. No LLM. | No |
| `eval_vqa_faithfulness` | Image-grounded visual-QA faithfulness. | Yes (vision) |
| `eval_document_grounding` | Multi-page document-grounded faithfulness for document-AI agents. | Yes (vision) |

### Flexible scoring

| Tool | What it does | API key |
|---|---|---|
| `eval_g_eval` | G-Eval holistic 0.0-1.0 scoring against a plain-English criterion. | Yes |
| `eval_custom_rubric` | Score against your own list of yes/no quality checks. | Yes |

### Agent workflows (new in 0.3.0)

| Tool | What it does | API key |
|---|---|---|
| `eval_compare_runs` | Diff two eval report JSONs — pass-rate delta, per-case regressions/improvements, McNemar p-value. Use after every fix to confirm it actually helped. | No |
| `eval_generate_cases` | Generate N eval cases (input / expected_output / context) from a chunk of source text. Eliminates the cold-start when building a new suite. | Yes (judge) |
| `eval_ingest_trace` | Convert a JSON agent trace (LangGraph / OpenAI Agents / manual) into an EvalCase payload. Use to score trajectories your agent just executed. | No |

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

## Why these 22 tools (not all 44)

`eval_discover` returns the full 44-evaluator catalog, so the agent can always introspect everything. The 22 tools we expose directly are the ones agents actually call mid-edit:

- RAG generation checks (faithfulness, hallucination, relevance, answer_accuracy)
- RAG retrieval checks (context_precision, context_recall)
- Safety / fairness guardrails (toxicity, bias)
- Compliance (pii_detection, schema_compliance) — local-only, no API egress
- Flexible scoring (g_eval, custom_rubric) for user-defined rubrics
- Multimodal (vqa_faithfulness, document_grounding) for vision agents
- Agent traces (tool_call_accuracy)
- Document AI (pdfhell.run, pdfhell.make) — for any RAG-on-PDFs flow
- Audit pack — when procurement is involved
- Discover — meta-capability for planning
- Agent workflows (compare_runs, generate_cases, ingest_trace) — the loop that turns one-shot scoring into iterative improvement

The three new 0.3.0 tools matter because evals are most useful as a *loop*, not a single call: generate a starting suite from your own docs (`eval_generate_cases`), run your agent over it, score the trace (`eval_ingest_trace` → `eval_*`), make a fix, then verify the fix improved things vs. the baseline (`eval_compare_runs`). Agents need that whole loop callable from within a conversation — otherwise they fall back to ad-hoc judgment.

Exposing all 44 evaluators as MCP tools would bloat the agent's context window and overwhelm tool-selection. If you need an evaluator that's not directly exposed, the agent can still use `multivon-eval` as a library — `eval_discover` returns the import paths.

## Dependencies

- `mcp[cli] >= 1.0` — official MCP Python SDK + the `mcp dev` inspector
- `multivon-eval >= 0.7.3` — the evaluator surface this wraps
- `pdfhell >= 0.1.0` — the adversarial-PDF benchmark this wraps

All Apache 2.0.

## The Multivon ecosystem

Five public + one early-access package, all built on a shared evaluation engine:

| Repo | What it is |
|---|---|
| [multivon-eval](https://github.com/multivon-ai/multivon-eval) | Python SDK — 44 evaluators + `bootstrap` CLI + `multivon_eval.auto`. The engine multivon-mcp wraps. |
| [pdfhell](https://github.com/multivon-ai/pdfhell) | Adversarial PDFs that break AI document readers — exposed here as `pdfhell_run` + `pdfhell_make` tools |
| **multivon-mcp** (you are here) | MCP server — 22 tools from multivon-eval + pdfhell |
| [eval-action](https://github.com/multivon-ai/eval-action) | GitHub Action — runs the same evals on every PR |
| [eval-framework-benchmark](https://github.com/multivon-ai/eval-framework-benchmark) | Reproducible head-to-head benchmark vs DeepEval + RAGAS |
| multivon-guard *(early access)* | Local proxy that catches LLM coding agents leaking secrets / PII |

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
