# multivon-mcp

[![PyPI](https://img.shields.io/pypi/v/multivon-mcp.svg)](https://pypi.org/project/multivon-mcp)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://pypi.org/project/multivon-mcp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/multivon-mcp/month)](https://pepy.tech/project/multivon-mcp)

**[Docs](https://docs.multivon.ai/mcp)** · [Website](https://multivon.ai/agents) · [PyPI](https://pypi.org/project/multivon-mcp) · [multivon-eval (engine)](https://github.com/multivon-ai/multivon-eval) · [Changelog](CHANGELOG.md)

These 22 tools cover what an autonomous eval agent needs to do its job: discover its own capabilities (`eval_discover`), normalize traces from supported sources (`eval_ingest_trace`), and run calibrated evaluators against them. We put the framework behind an MCP boundary because eval belongs in the agent's working loop, not behind a separate dashboard.

An MCP server that gives AI coding agents direct access to evaluation tools. Drop into Claude Desktop, Claude Code, Cursor, Cline, or any [Model Context Protocol](https://modelcontextprotocol.io/)–compatible agent.

When the agent is helping you build an LLM product, it can:

- Score a RAG output for hallucination without you writing the scaffolding
- Generate an adversarial PDF on demand to test your document AI
- Run the full pdfhell mini-suite against a model and analyse the results
- Produce a self-verifying audit pack with a SHA-256 file manifest
- Discover the full evaluation capability catalog as JSON

No copy-paste, and no asking the agent to figure out the SDK calls from `python -c "..."` one-liners.

> **Current release: 0.3.2.** The repository's unreleased changes track MCP Python SDK 1.29.x, multivon-eval 0.16.1, and pdfhell 0.6.1. See the [changelog](CHANGELOG.md).

## Install

```bash
pip install "mcp<2" multivon-mcp  # required by released 0.3.2
```

The next release carries this compatibility bound itself. Installation pulls
`multivon-eval`, `pdfhell`, and the MCP SDK. The provider SDKs (`anthropic`,
`openai`, `google-genai`) come along too — bring your own API key in env.

## Configure your agent

### Claude Code

```bash
claude mcp add --transport stdio --scope user multivon -- multivon-mcp
claude mcp get multivon
```

Set provider keys in your shell or secure environment before starting Claude Code. To share the server configuration with a project instead, use `--scope project`; Claude Code writes `.mcp.json` and supports environment-variable expansion there. It does **not** read `claude_desktop_config.json`.

### Claude Desktop

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

`.cursor/mcp.json` or via Settings → MCP:

```json
{ "mcpServers": { "multivon": { "command": "multivon-mcp" } } }
```

### Cline / OpenCode / any MCP-compatible agent

Same shape — point at the `multivon-mcp` console script.

### Local dev / debugging

From a clone of this repo:

```bash
mcp dev multivon_mcp/server.py
```

From a pip install (the file lives in site-packages, so resolve it):

```bash
mcp dev "$(python -c 'import multivon_mcp.server as s; print(s.__file__)')"
```

Opens the MCP Inspector UI in your browser. You can call any tool by name, see the JSON schemas, and watch the requests/responses.

## The 22 tools

### Discovery & document AI

| Tool | What it does | API key |
|---|---|---|
| `eval_discover` | Full machine-readable capability catalog (evaluators, traps, suites, calibration data, versions). Call first. | No |
| `pdfhell_make` | Generate one adversarial PDF + its answer key. | No |
| `pdfhell_run` | Run the pdfhell adversarial-PDF benchmark against a vision model. Returns pass rate, per-trap CIs, suite hash. | Yes (vision) |
| `eval_audit_pack` | Build a procurement-ready ZIP with a SHA-256 file manifest from a pdfhell run. | No |

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
| `eval_pii_detection` | Local-only regex scan for PII (GDPR / CCPA / PIPEDA / HIPAA / DPDP packs). | No |
| `eval_schema_compliance` | Validate an LLM output against a JSON Schema. | No |

### Agent & multimodal

| Tool | What it does | API key |
|---|---|---|
| `eval_tool_call_accuracy` | Deterministic agent tool-call correctness. No LLM. | No |
| `eval_vqa_faithfulness` | Image-grounded visual-QA faithfulness. | Yes (vision) |
| `eval_document_grounding` | Multi-page document-grounded faithfulness for document-AI agents. | Yes (vision) |

> **Agent traces.** `eval_tool_call_accuracy` and the other agent-trace
> evaluators in `multivon-eval` (`ToolArgumentAccuracy`,
> `ToolCallNecessity`, `TrajectoryEfficiency`, `AgentMemoryEval`,
> `PlanQuality`, `TaskCompletion`, `StepFaithfulness`) take an
> `agent_trace=[AgentStep(...)]` plus `expected_tool_calls=[...]` on
> the case. Three-shape semantics matter: `expected_tool_calls=None`
> skips, `[]` asserts "no tools called", and `[...]` checks for the
> named calls. On repository `main` (shipping in the next release), the MCP
> tool supports the same trace mode: normalize
> trace JSON with `eval_ingest_trace`, then pass its `agent_trace` plus
> `expected_tool_calls` to `eval_tool_call_accuracy`. Set
> `require_order=true` when sequence matters or
> `penalize_unexpected=true` for a strict allow-list. See the
> [`multivon-eval` agent integrations](https://github.com/multivon-ai/multivon-eval/tree/main/multivon_eval/integrations)
> for the source-of-truth tracer code.

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
- Document AI (`pdfhell_run`, `pdfhell_make`) — for any RAG-on-PDFs flow
- Audit pack — when procurement is involved
- Discover — meta-capability for planning
- Agent workflows (compare_runs, generate_cases, ingest_trace) — the loop that turns one-shot scoring into iterative improvement

The three new 0.3.0 tools exist because evals pay off as a loop: generate a starting suite from your own docs (`eval_generate_cases`), run your agent over it, score the trace (`eval_ingest_trace` → `eval_*`), make a fix, then verify the fix improved things vs. the baseline (`eval_compare_runs`). Agents need that whole loop callable from within a conversation, or they fall back to ad-hoc judgment.

Exposing all 44 evaluators as MCP tools would bloat the agent's context window and overwhelm tool-selection. If you need an evaluator that's not directly exposed, the agent can still use `multivon-eval` as a library — `eval_discover` returns the import paths.

## Dependencies

Tested runtime bounds (from `pyproject.toml`):

- `mcp[cli] >= 1.29, < 2` — official MCP Python SDK and Inspector. MCP 2.0 has a different server API and is intentionally excluded until this server migrates.
- `multivon-eval >= 0.16.1` — the 44-evaluator engine, current report schema, and reasoning-judge fix.
- `pdfhell >= 0.6.1` — the 17-family mini-v4 registry, corrected trap renderings, and current audit-pack schema.

These bounds are on repository `main` and will ship in the next release. For
released 0.3.2, use `pip install "mcp<2" multivon-mcp` so pip does not resolve
the incompatible MCP 2.0 server API.

All Apache 2.0.

## MCP server vs Claude Code skills vs eval-action — which one do I use?

`multivon-eval` ships three agent-facing surfaces. They overlap on what
they call (the same evaluator catalog) but differ on where the agent
lives.

| Surface | Where the agent runs | Best for |
|---|---|---|
| **multivon-mcp** (this repo) | Any MCP-compatible client — Claude Desktop, Cursor, Cline, OpenCode, Claude Code | Mid-edit scoring inside an IDE or chat app. Agent calls `eval_faithfulness` / `eval_hallucination` / etc. directly as tools. |
| **Claude Code skills** — `eval-bootstrap`, `eval-audit`, `eval-explain` (bundled in `multivon-eval >= 0.9.8`; install with `multivon-eval install-skills`) | Claude Code only | Workflow-shaped tasks: scaffold an eval suite from a project description, pre-PR regression checks against a baseline, explaining why a particular evaluator was picked. The skills know how to call `multivon-eval bootstrap` / use `compare_reports` / etc. so the agent doesn't have to figure it out from docs. |
| **[eval-action](https://github.com/multivon-ai/eval-action)** | GitHub CI | Gate every PR on eval regressions automatically. Posts the Wilson-CI + McNemar verdict as a PR comment. |

If you're building an LLM product and want the agent in your editor to
score a RAG output without copy-pasting Python, use multivon-mcp.
If you live in Claude Code and want the bootstrap → audit → explain
loop wired up as native commands, use the bundled skills. For PR-time
gating, use the GitHub Action. Most projects end up using more than
one.

## The Multivon ecosystem

Four public packages plus one closed early-access product, built around the same evaluation engine:

| Repo | What it is |
|---|---|
| [multivon-eval](https://github.com/multivon-ai/multivon-eval) | Python SDK — 44 evaluators + `bootstrap` CLI + `multivon_eval.auto`. The engine multivon-mcp wraps. |
| [pdfhell](https://github.com/multivon-ai/pdfhell) | Adversarial PDFs that break AI document readers — exposed here as `pdfhell_run` + `pdfhell_make` tools |
| **multivon-mcp** (you are here) | MCP server — 22 tools from multivon-eval + pdfhell |
| [eval-action](https://github.com/multivon-ai/eval-action) | GitHub Action — runs the same evals on every PR |
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
