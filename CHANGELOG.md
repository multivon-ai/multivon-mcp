# Changelog

All notable changes to `multivon-mcp` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-06-03

### Fixed
- MCP `serverInfo` now reports the package version (0.3.1) instead of the MCP SDK version.
- Docs aligned with the current pdfhell suite (17 trap families) and corrected the list of vision-capable models.

### Changed
- Bumped the `multivon-eval` dependency floor to 0.9.4; documented recommended floors (`multivon-eval >= 0.9.8`, `pdfhell >= 0.5.4`) for full feature parity.
- README: added ecosystem badges/cross-links, Claude Code skills comparison table, and agent-trace (`expected_tool_calls`) semantics.

## [0.3.0] - 2026-05-17

### Added
- 3 new agent-workflow tools: `eval_compare_runs` (diff two eval reports with McNemar p-value), `eval_generate_cases` (bootstrap eval cases from source text), and `eval_ingest_trace` (normalize LangGraph / OpenAI Agents / manual traces into EvalCase payloads).
- Brings the exposed surface to 22 tools, completing the generate → run → score → compare loop.

## [0.2.1] - 2026-05-17

### Fixed
- `__version__` now matches the version declared in `pyproject.toml` (0.2.1).

## [0.2.0] - 2026-05-17

### Added
- 10 new MCP tools across compliance (`eval_pii_detection`, `eval_schema_compliance`), safety (`eval_toxicity`, `eval_bias`), RAG retrieval (`eval_context_precision`, `eval_context_recall`), multimodal (`eval_vqa_faithfulness`, `eval_document_grounding`), and flexible scoring (`eval_g_eval`, `eval_custom_rubric`).

## [0.1.0] - 2026-05-17

### Added
- Initial release: FastMCP stdio server exposing agent-callable evaluation tools from `multivon-eval` and `pdfhell`.
- Core tools: `eval_discover`, `eval_faithfulness`, `eval_hallucination`, `eval_relevance`, `eval_answer_accuracy`, `eval_tool_call_accuracy`, `pdfhell_run`, `pdfhell_make`, `eval_audit_pack`.

[0.3.1]: https://github.com/multivon-ai/multivon-mcp/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/multivon-ai/multivon-mcp/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/multivon-ai/multivon-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/multivon-ai/multivon-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/multivon-ai/multivon-mcp/releases/tag/v0.1.0
