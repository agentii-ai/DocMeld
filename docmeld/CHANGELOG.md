# Changelog

All notable changes to DocMeld will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Repository hygiene**: CI workflows relocated to repo root (`.github/workflows/`); OIDC trusted publishing for PyPI.
- **Packaging**: Personal batch scripts moved from the importable package to `docmeld/scripts/` (not shipped in wheel).
- **LLM provider abstraction**: New `LLMProvider` Protocol in `docmeld/gold/provider.py`; `DeepSeekClient` implements it; generators typed as `LLMProvider` instead of `Any`; `DocMeldParser` accepts optional `provider` injection.
- **Type safety**: 46 latent mypy errors fixed; `parser.py` return annotations resolved via `TYPE_CHECKING` imports; `BronzeElement` union made Python 3.9-compatible; strict mypy enforced in CI/pre-commit.
- **DRY consolidation**: Duplicated `_load_silver_content`, `_aggregate_content`, and code-fence-stripping logic consolidated into `utils/{silver_io,content,text}.py`.
- **Dead code removed**: `DocMeldParser.output_dir`, `gold_failed` variable, `_merge_categories` in categorizer.
- **`process_all` fixed**: Single-file path now correctly reports gold-stage failure (`successful=0, failed=1`) instead of hardcoded success.
- **Pytest markers**: `pytest_collection_modifyitems` hook in `conftest.py` auto-tags tests by directory; `pytest -m unit/integration/contract` now selects correctly.
- **Library-safe logging**: `import docmeld` no longer mutates logger handlers; CLI entry point configures logging explicitly.

### Added
- `py.typed` marker (PEP 561) — downstream consumers get type information.
- `SECURITY.md` with GitHub Private Vulnerability Reporting + 90-day coordinated disclosure.
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `CITATION.cff`, issue/PR templates, Dependabot, pre-commit config.
- Shared utilities: `utils/silver_io.py`, `utils/content.py`, `utils/text.py` with `MAX_CONTENT_CHARS`/`HEAD_RATIO` constants.
- `test_provider.py` (3 tests) — LLMProvider injection seam.
- `test_parser.py` (3 tests) — `process_all` failure semantics + provider injection.
- Subpackage `__init__.py` exports for `generate_prd`, `generate_workflow`, `generate_skills`, `categorize_papers`, `LLMProvider`.
- Both READMEs updated with accurate badges (315 tests / 78% coverage), full CLI reference, Knowledge Generation section, Python API with provider seam, and backends table (auto/pptx/soffice).

### Fixed
- All repo URLs unified to `github.com/agentii-ai/DocMeld`.
- CHANGELOG compare-link URLs fixed (were `[username]` placeholders).

## [0.3.0] - 2026-07-10

### Added
- PPT/PPTX pipeline: Process PowerPoint presentations alongside PDFs and Word docs (bronze → silver → gold).
- 4 new element types: smartart, notes, group, comment (14 total).
- `PptxBackend`: native python-pptx slide-level shape extraction.
- Slide-based pagination; `hidden` flag on elements from hidden slides.
- Inline hyperlink preservation as markdown `[text](url)`.
- Hybrid geometric + z-order element ordering within slides.
- `SofficeBackend` extended to accept legacy `.ppt` files.
- `--backend pptx` CLI choice; `auto` routes `.pptx`→pptx, `.ppt`→soffice.
- `[[SmartArtN]]`/`[Notes]`/`[Comment: author]` marker syntax in silver JSONL output.
- `pptx` and `office` optional-dependency extras.
- `element_id` widened to 4 digits (`e_0001`) to support large presentations.

## [0.2.0] - 2026-07-09

### Added
- DOC/DOCX pipeline: Process Word documents alongside PDFs (bronze → silver → gold).
- 6 new element types: chart, formula, header, footer, footnote, endnote (10 total).
- SofficeBackend: LibreOffice bridge for legacy .doc file processing.
- `--backend auto` CLI flag: automatic format detection.
- Chart data extraction with image fallback; MathType/OMML → LaTeX formula extraction.
- Header/footer, footnote/endnote detection in .docx documents.
- Format filtering: .docm/.dotx/.dot/.rtf skipped with warning.
- `[Header]`/`[Footer]`/`[^N]` marker syntax in silver JSONL output.

### Changed
- Element type system expanded from 4 to 10 types (backward compatible).
- BronzeProcessor and DocMeldParser generalized from PDF-only to multi-format.
- SilverProcessor source filename now dynamically detects .pdf/.doc/.docx extension.

## [0.1.0] - 2026-03-12

### Added
- Bronze: PDF to structured JSON element extraction (PyMuPDF). Text, table, title, image types.
- Silver: JSON to page-by-page JSONL with title hierarchy and markdown rendering.
- Gold: AI-powered metadata extraction using DeepSeek-chat with retry logic.
- CLI: `docmeld process`, `bronze`, `silver`, `gold` subcommands.
- Python API: `DocMeldParser` with `process_all()`, `process_bronze()`, `process_silver()`, `process_gold()`.
- Filename sanitization with MD5 hash suffix; idempotent processing; batch folder support.
- Timestamped logging, `.env.local` support, cross-platform (macOS/Linux/Windows).
- 109 tests, 82% code coverage.

[Unreleased]: https://github.com/agentii-ai/DocMeld/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/agentii-ai/DocMeld/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/agentii-ai/DocMeld/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/agentii-ai/DocMeld/releases/tag/v0.1.0
