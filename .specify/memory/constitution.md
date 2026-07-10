<!--
  Sync Impact Report
  ==================
  Version change: 0.0.0 → 1.0.0 (MAJOR - initial ratification)
  Modified principles: N/A (initial creation)
  Added sections:
    - Principle I: Test-First Development (NON-NEGOTIABLE)
    - Principle II: Library-First, PyPI-Ready
    - Principle III: Lightweight by Default
    - Principle IV: Unified Element Format
    - Principle V: Agent-Ready Outputs
    - Principle VI: Production-Grade Quality
    - Principle VII: Open-Source Excellence
    - Section: Technical Constraints
    - Section: Development Workflow
    - Section: Governance
  Removed sections: N/A (initial creation)
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ compatible (Constitution Check section exists)
    - .specify/templates/spec-template.md ✅ compatible (priority-based stories align)
    - .specify/templates/tasks-template.md ✅ compatible (TDD task ordering supported)
  Follow-up TODOs: None
-->

# DocMeld Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

Every feature, bugfix, and refactor MUST follow strict Test-Driven Development:

- Tests MUST be written before implementation code
- Tests MUST fail (red) before any production code is written
- Implementation MUST be the minimum code to make tests pass (green)
- Refactoring MUST only occur after tests pass, and tests MUST remain green
- No pull request will be merged without corresponding test coverage
- Integration tests MUST cover every public API surface (parser inputs, output formats, CLI commands)
- Unit tests MUST cover every extractor and exporter independently
- Target: 90%+ code coverage; core parser logic MUST have 100% coverage

Rationale: DocMeld processes real documents where silent data loss or corruption is unacceptable. TDD ensures correctness from day one and builds the trust required for a widely-adopted open-source tool.

### II. Library-First, PyPI-Ready

DocMeld is a Python library first, CLI tool second:

- The core MUST be importable as `from docmeld import DocMeldParser` with zero side effects on import
- All functionality MUST be accessible programmatically before being exposed via CLI
- The package MUST be installable via `pip install docmeld` with minimal, well-pinned dependencies
- Public API MUST use type hints throughout and follow PEP 8
- Semantic versioning (MAJOR.MINOR.PATCH) MUST be used for all releases
- Breaking API changes MUST increment the MAJOR version
- Every public class and function MUST have a docstring

Rationale: Developers adopt libraries they can embed in their own pipelines. A clean, importable API with predictable versioning is the foundation for ecosystem growth and community trust.

### III. Lightweight by Default

The MVP and core package MUST NOT require expensive or hard-to-install models:

- Core parsing MUST use only PyMuPDF (fitz) — no OCR, VLM, or multimodal model dependencies
- The base install (`pip install docmeld`) MUST complete in under 30 seconds on a standard machine
- Total core dependency count MUST remain under 10 packages
- Optional heavy backends (OCR, VLM) MAY be supported via extras (`pip install docmeld[ocr]`) in future versions, but MUST NOT be required
- The library MUST run entirely offline with zero API calls for core functionality
- Memory usage MUST stay under 500MB for documents up to 100 pages

Rationale: The #1 complaint about existing tools (MinerU, Marker, Docling) is heavyweight model dependencies. DocMeld wins adoption by being the tool that just works — `pip install` and go.

### IV. Unified Element Format

All parsed documents MUST produce a single, consistent JSON element structure:

- Every element MUST contain `type` (string) and `page_no` (integer)
- Supported element types: `title`, `text`, `table`, `image`, `chart`, `formula`, `header`, `footer`, `footnote`, `endnote`, `smartart`, `notes`, `group`, `comment`
- `title` elements MUST include `level` (integer, 0-based) and `content` (string)
- `text` elements MUST include `content` (string)
- `table` elements MUST include `content` (markdown string) and `summary` (string)
- `image` elements MUST include `image_name`, `content`, `image` (base64), `image_id`, and `bbox`
- `chart` elements MUST include `chart_type`, `content` (markdown table), `image` (base64 fallback), and `image_name`
- `formula` elements MUST include `content` (LaTeX string) and `formula_type`
- `header` and `footer` elements MUST include `content` and `page_scope` (all/even/odd)
- `footnote` and `endnote` elements MUST include `content` and `reference_id`
- `smartart` elements MUST include `smartart_type` and `content` (with `image` fallback)
- `notes` elements MUST include `content` (speaker notes attached to a slide)
- `group` elements MUST include `child_count`; grouped children reference the group via `parent_id`
- `comment` elements MUST include `content` and `author`
- Element order in the list MUST reflect document reading order
- The format MUST be documented with a JSON Schema and validated on output
- New element types MAY be added in MINOR versions but existing types MUST NOT change shape in MINOR/PATCH versions

Rationale: A stable, predictable intermediate format is what makes DocMeld composable. Downstream consumers (RAG pipelines, agent builders, prompt generators) depend on this contract. Breaking it breaks the ecosystem.

### V. Agent-Ready Outputs

DocMeld's differentiator is the path from document to agent-consumable artifact:

- The unified JSON element format MUST be designed for direct consumption by LLM-based agents
- Output formats MUST include JSON (structured elements), Markdown (human-readable), and Excel (tabular data)
- Table outputs MUST include summaries and metadata sufficient for an agent to decide relevance without reading full content
- Future versions MUST support transformation to prompts, workflows, and Claude skill definitions
- All outputs MUST preserve source attribution (page numbers, document filename) for citation and traceability

Rationale: Every competitor stops at format conversion. DocMeld's roadmap to agent-ready artifacts is the strategic moat. Every design decision MUST keep this path open.

### VI. Production-Grade Quality

Code quality standards MUST match production-level open-source projects:

- All code MUST pass ruff linting and black formatting with zero exceptions
- All code MUST pass mypy type checking in strict mode
- Error handling MUST be explicit — no bare `except:` clauses; exceptions MUST be logged with context
- The parser MUST gracefully handle malformed PDFs without crashing — return partial results with warnings
- CI MUST run tests, linting, type checking, and coverage on every push and PR
- Dependencies MUST be pinned to compatible ranges and audited for known vulnerabilities
- Performance benchmarks MUST be tracked for core parsing operations

Rationale: To become the most popular doc-to-agent tool, DocMeld MUST earn developer trust through reliability. Production-grade quality is not optional — it is the price of admission.

### VII. Open-Source Excellence

DocMeld MUST be a model open-source project:

- MIT license — no exceptions, no dual-licensing
- README MUST include: badges (CI, coverage, PyPI version), quickstart (under 5 lines of code), feature overview, and roadmap
- CONTRIBUTING.md MUST exist with clear guidelines for issues, PRs, and code style
- All issues and PRs MUST receive a response within 72 hours
- CHANGELOG.md MUST be maintained with every release following Keep a Changelog format
- Releases MUST be automated via CI/CD (GitHub Actions → PyPI)

Rationale: Star count and adoption correlate directly with project approachability. A well-maintained, welcoming project attracts contributors who accelerate the roadmap.

## Technical Constraints

- **Language**: Python 3.9+ (minimum supported version)
- **Core Dependencies**: PyMuPDF (fitz), pandas, openpyxl, pydantic
- **Testing**: pytest with pytest-cov; minimum 90% coverage gate in CI
- **Formatting**: black (line length 100), ruff for linting
- **Type Checking**: mypy in strict mode
- **Package Management**: pyproject.toml (PEP 621); poetry or hatch for builds
- **CI/CD**: GitHub Actions for test, lint, type-check, publish
- **Platforms**: macOS, Linux, Windows — all MUST be tested in CI
- **CLI**: Click or argparse (stdlib preferred for zero extra deps)

## Development Workflow

1. **Branch**: Create feature branch from `main` with descriptive name
2. **Test First**: Write failing tests that define the expected behavior
3. **Implement**: Write minimum code to pass tests
4. **Refactor**: Clean up while keeping tests green
5. **Lint & Type Check**: Run `ruff check`, `black --check`, `mypy` — all MUST pass
6. **PR**: Open pull request with description linking to issue/spec
7. **Review**: At least one approval required; CI MUST be green
8. **Merge**: Squash-merge to `main`; delete feature branch
9. **Release**: Tag with semantic version; CI publishes to PyPI

All PRs MUST include:
- Tests covering the change
- Updated docstrings if public API changed
- CHANGELOG entry for user-facing changes

## Governance

This constitution is the supreme authority for DocMeld development practices. All code, PRs, reviews, and architectural decisions MUST comply with these principles.

**Amendment Process**:
- Any contributor MAY propose an amendment via a GitHub issue tagged `constitution`
- Amendments MUST include: the change, rationale, and migration plan for existing code
- Amendments MUST be approved by at least one maintainer
- Version MUST be incremented per semantic versioning (MAJOR for principle removal/redefinition, MINOR for additions, PATCH for clarifications)

**Compliance**:
- Every PR review MUST verify compliance with applicable principles
- The plan-template Constitution Check gate MUST reference these principles
- Complexity beyond what is specified here MUST be justified in writing

**Version**: 1.1.0 | **Ratified**: 2026-03-12 | **Last Amended**: 2026-07-10
