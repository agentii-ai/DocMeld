# Feature Specification: OSS-Standard Optimization & Launch Readiness

**Feature Branch**: `008-optimization-launch`
**Created**: 2026-07-28
**Status**: In Progress
**Input**: User request — "docmeld 是一个优秀的开源项目，用最高的开源项目标准评估整个代码库；优化 README.md。" Expanded during planning to **full remediation** (docs + repo structure + code) plus optimizing **both** README files.

## Context

DocMeld is a published OSS project (v0.3.0 on PyPI, git remote `github.com/agentii-ai/DocMeld`).
It has grown from an MVP PDF pipeline (spec 001) through DOCX (006), PPTX (007), and four
higher-order knowledge-generation features (categorize/prd/workflow/skills, specs 002–005). The
code outpaced its documentation and repository scaffolding. A three-agent deep audit (repo
hygiene/CI, architecture, testing/docs) plus direct verification found issues that would prevent
the project from meeting the standard of top-tier Python OSS (e.g. `rich`, `pydantic`, `httpx`).

The intended outcome: a repository where CI actually runs, the published package ships only library
code with correct type information, the type checker is genuinely enforced, the LLM provider is
swappable, duplicated logic is consolidated, and both READMEs accurately represent v0.3.0+
capabilities.

**This is a non-feature, quality-and-hygiene release.** No new end-user capability is added; the
observable pipeline behavior is preserved. Target version after completion: `0.4.0`.

## Verified Findings (audit + independent confirmation)

Each finding below was confirmed by reading the code/config directly, not merely asserted.

### Critical — repository structure

- **CF-1 Dead CI.** `.github/workflows/{test,lint,publish}.yml` existed under `docmeld/.github/`,
  one level below the git root. GitHub Actions only reads `<repo-root>/.github/workflows/`, so all
  three pipelines never ran. The workflows themselves were good (OS × Python matrix, ruff/black/mypy,
  PyPI publish). *Confirmed: no `.github/` at repo root prior to this work.*
- **CF-2 Invisible community-health files.** LICENSE, CONTRIBUTING.md, CHANGELOG.md all lived under
  `docmeld/`, so GitHub's community-health detection reported them as missing.

### Critical — code correctness

- **CF-3 Type-annotation bug in `parser.py`.** `process_prd`/`process_workflow`/`process_skills`
  were annotated to return `PrdResult`/`WorkflowResult`/`SkillsResult` but those names were never
  imported (they live in `{prd,workflow,skills}/models.py`). Masked at runtime only by
  `from __future__ import annotations`; invalid under the declared strict mypy. *Confirmed.*
- **CF-4 mypy not enforced.** `mypy docmeld/` halted with 4 errors on missing third-party stubs
  (`fitz`, `pymupdf4llm`) plus a torch venv file — no `ignore_missing_imports`. Once those were
  cleared, **46 latent type errors** across `cli.py`, `element_types.py`, `categorizer.py`,
  `element_extractor.py`, `docling_backend.py` surfaced that the broken config had hidden.
  *Confirmed by running mypy.*
- **CF-5 Python 3.9 incompatibility.** `element_types.py` defined `BronzeElement` as a runtime
  `X | Y | …` union on the right-hand side of an assignment (not an annotation). The PEP 604 `|`
  syntax raises `TypeError` at import on Python 3.9, yet the package advertises `>=3.9`.
  *Confirmed by inspection.*

### High — packaging & generality

- **HF-1 Published package shipped personal scripts.** `summarize.py`, `summarize_bschool.py`,
  `batch_pipeline.py`, `fix_summaries.py`, `run_loop_prompts.py` lived inside the importable
  package (`docmeld/docmeld/`) and were published to PyPI. They contain hardcoded personal paths
  and Chinese research-paper prompts. A stray `summarize_rl.py` at the repo root used a
  `sys.path.insert` hack and a hardcoded `/Users/frank/Documents/...` path.
- **HF-2 LLM provider hardcoded to DeepSeek.** No provider Protocol; `DeepSeekClient` instantiated
  directly in 5 places; `client: Any` in every generator signature; `env_loader` only understands
  `DEEPSEEK_*`. This is the #1 generality blocker for an OSS pipeline.
- **HF-3 No `py.typed` marker.** Despite strict-mypy-clean typed code, downstream consumers get no
  type information (PEP 561).
- **HF-4 URL chaos.** Four different repo owners across the tree: git remote `agentii-ai/DocMeld`,
  pyproject `docmeld/docmeld`, READMEs `agentii-ai/docmeld` + `[username]`, CHANGELOG/CONTRIBUTING
  `[username]`/`[your-username]`.
- **HF-5 Placeholder author, no email** in `pyproject.toml`.

### Medium — maintainability

- **MF-1 DRY violations.** `_load_silver_content` duplicated verbatim across prd/workflow/skills
  generators + categorize/aggregator; `_aggregate_content` (30k char, 60/40 split) triplicated;
  code-fence stripping appears in 6+ places.
- **MF-2 Dead code.** `DocMeldParser.output_dir` field (stored, never used), `gold_failed` variable
  (set, never read), `_merge_categories` in categorizer (never called).
- **MF-3 `process_all` single-file path reports unconditional success** even when the gold stage
  fails (the tracked `gold_failed` is discarded).
- **MF-4 Backend dispatch not extensible.** Hardcoded `if/elif` chain in `element_extractor.py`
  plus a 6×-repeated `choices=[...]` list in `cli.py`; the declared `ParserBackend` Protocol was
  never used as a type, so conformance was unchecked.
- **MF-5 Library attaches log handlers.** `setup_logging` mutates the shared `"docmeld"` logger;
  fine for the CLI, unfriendly when imported as a library.

### Medium — testing & docs

- **TF-1 Stale README badges/claims (both files).** Badges said 144 tests / 81% (docmeld/README)
  and 309 / 80% (root README); real suite is **314 collected, 309 passed, 5 skipped**. The
  four shipped commands (categorize/prd/workflow/skills) were missing from CLI Reference and Python
  API sections and marked unchecked in the Roadmap. Backends documented as pymupdf/docling only
  (real: pymupdf/docling/pptx/soffice/auto, default `auto`).
- **TF-2 pytest markers declared but never applied.** `pyproject` declares `unit`/`integration`/
  `contract` with `--strict-markers`, but no test uses `@pytest.mark.*`, so `-m` selection returns
  nothing.
- **TF-3 No `test_parser.py`.** The orchestrator's `process_*` methods are only covered indirectly.
- **TF-4 Missing health files.** No SECURITY.md, CODE_OF_CONDUCT.md, CITATION.cff, issue/PR
  templates, pre-commit config, or Dependabot.

### Retained strengths (preserve, do not regress)

Clean medallion architecture with single-responsibility stage processors; minimal side-effect-free
top-level API with PEP 562 lazy imports; real Protocol-based backend abstraction with centralized
post-processing; Pydantic result models throughout; single named logger, no bare excepts, no stray
prints in library code; exemplary CHANGELOG; thorough CONTRIBUTING; consistent version across
pyproject/`__init__`/git tag; correctly-ignored build/venv artifacts.

## User Scenarios & Testing

### User Story 1 — CI runs on push/PR (Priority: P1)

As a maintainer, I want the existing GitHub Actions workflows to actually execute so that tests,
linting, and type-checking gate every change.

**Independent Test**: `.github/workflows/` exists at the repo root; workflows declare
`working-directory: docmeld`; a push to a branch triggers the Tests and Lint workflows.

**Acceptance**:
1. **Given** the workflows at repo root, **When** a PR is opened, **Then** the OS × Python matrix
   runs `pytest` and the Lint job runs ruff/black/mypy, all resolving against `docmeld/pyproject.toml`.
2. **Given** a tagged release `v*`, **When** the tag is pushed, **Then** `publish.yml` builds from
   `docmeld/` and publishes via PyPI OIDC trusted publishing (no long-lived token).

### User Story 2 — Published package is clean and typed (Priority: P1)

As a downstream developer, I want `pip install docmeld` to give me only library code with type
information and no personal scripts.

**Acceptance**:
1. The built wheel contains `docmeld/py.typed` and none of the personal batch scripts.
2. `mypy` against a consumer project resolves DocMeld's types.
3. Personal scripts run from `docmeld/scripts/<name>.py` (documented), not `python -m docmeld.<name>`.

### User Story 3 — Type checker is green and enforced (Priority: P1)

As a maintainer, I want `mypy docmeld` to pass with zero errors and stay that way via CI/pre-commit.

**Acceptance**:
1. `mypy docmeld` → `Success: no issues found`.
2. The `parser.py` return annotations resolve (TYPE_CHECKING import block).
3. Third-party stub-less deps are handled via scoped overrides, not a blanket ignore.

### User Story 4 — LLM provider is swappable (Priority: P2)

As a developer, I want to supply an alternative LLM provider so that DocMeld isn't locked to DeepSeek.

**Acceptance**:
1. An `LLMProvider` Protocol exists in `docmeld/gold/`; `DeepSeekClient` implements it.
2. Generators type their client parameter as `LLMProvider`, not `Any`.
3. `DocMeldParser` accepts an optional provider injection; default remains DeepSeek and existing
   behavior is unchanged.

### User Story 5 — Accurate, top-tier READMEs (Priority: P1)

As a prospective user, I want both READMEs to correctly describe every command, the Python API, and
the real capabilities.

**Acceptance**:
1. Badges reflect measured test count and coverage via static shields.io badges updated to match current `pytest --cov` output (no live coverage service integration).
2. CLI Reference and Python API document all 8 commands and 4 new `process_*` methods + result models.
3. Roadmap checks off shipped features; backends section documents auto/pptx/soffice.
4. No placeholder URLs remain; both files point to `agentii-ai/DocMeld`.

### User Story 6 — Community health & maintainability (Priority: P2)

As a contributor, I want standard health files and a codebase free of duplicated logic and dead code.

**Acceptance**:
1. SECURITY.md (with GitHub Private Vulnerability Reporting instructions, 90-day coordinated disclosure), CODE_OF_CONDUCT.md, CITATION.cff, issue/PR templates present at repo root.
2. Duplicated helpers consolidated in `utils/`; dead code removed; `process_all` reports real
   single-file gold failures.
3. pytest markers apply so `-m unit/integration/contract` works; `test_parser.py` added.

## Requirements

- **FR-001**: `.github/` (workflows + dependabot) MUST live at the git repository root and run from
  the `docmeld/` package subdirectory.
- **FR-002**: `publish.yml` MUST use PyPI OIDC trusted publishing.
- **FR-003**: Personal batch scripts MUST NOT ship in the wheel; they live under `docmeld/scripts/`
  and are runnable via `python scripts/<name>.py`. No backward-compatibility shims are required;
  the break is documented in CHANGELOG as these scripts were never public API.
- **FR-004**: `summarize_rl.py` MUST take its target folder as a CLI argument (no hardcoded path,
  no `sys.path` hack).
- **FR-005**: `mypy docmeld` MUST report zero errors; the config MUST scope to the package and
  handle stub-less third-party imports via targeted overrides.
- **FR-006**: `BronzeElement` MUST be defined in a Python 3.9-compatible way.
- **FR-007**: The package MUST ship a `py.typed` marker (PEP 561).
- **FR-008**: An `LLMProvider` Protocol MUST exist; `DeepSeekClient` MUST implement it; generators
  MUST type the client as `LLMProvider`; default behavior MUST be unchanged.
- **FR-009**: Duplicated silver-loading, content-aggregation, and code-fence-stripping logic MUST be
  consolidated into `utils/`.
- **FR-010**: Dead code (`output_dir`, `gold_failed`, `_merge_categories`) MUST be removed;
  single-file `process_all` MUST report actual gold-stage failure.
- **FR-011**: `setup_logging` MUST NOT attach handlers on import (library-safe); CLI entry point
  MUST configure logging explicitly on demand. Importing `docmeld` as a library MUST NOT mutate the
  shared `"docmeld"` logger's handlers.
- **FR-012**: pytest markers MUST be applied so `-m` selection works; a `test_parser.py` MUST exist.
- **FR-013**: All repo URLs MUST resolve to `github.com/agentii-ai/DocMeld`; `pyproject` MUST carry
  a real author name + email and Documentation/Changelog URLs.
- **FR-014**: Both `README.md` files MUST accurately document all 8 CLI commands, the full Python
  API (including the 4 new `process_*` methods and their result models), correct backends, an
  updated Roadmap, and correct badges.
- **FR-015**: The full test suite MUST remain green (≥309 passed, 5 skipped) after every phase.
- **FR-016**: Version MUST NOT be bumped and the package MUST NOT be published as part of this work;
  CHANGELOG `[Unreleased]` captures the changes for a future `0.4.0`.

### Non-Functional

- **NFR-001**: No regression in observable pipeline behavior (bronze/silver/gold outputs identical).
- **NFR-002**: `ruff check docmeld/` and `black --check docmeld/` MUST pass across the entire
  `docmeld/` directory (library source + scripts). Scripts are included in lint scope;
  no separate config or exclusion needed.
- **NFR-003**: `git mv` MUST be used for relocations to preserve file history.
- **NFR-004**: CI test matrix MUST cover Ubuntu, macOS, Windows × Python 3.9, 3.10, 3.11, 3.12, 3.13 (15 jobs).

## Out of Scope

- Adding new pipeline capabilities or element types.
- OCR for scanned PDFs, agent-prompt generation, LangChain/LlamaIndex integration (remain roadmap).
- Migrating to a Sphinx/mkdocs documentation site (noted as a future gap; not required here).
- Publishing to PyPI or cutting the `0.4.0` release (owner action).
- Flattening the repo (moving the package up to the git root) — considered but deferred; the
  `working-directory` approach in CI resolves the immediate CI breakage without a disruptive move.

## Clarifications

### Session 2026-07-28

- Q: Should relocated `docmeld/scripts/` be included in ruff/black lint scope? → A: Yes, include scripts in lint formatting (Option B).
- Q: What OS × Python version combinations should CI test matrix cover? → A: Ubuntu, macOS, Windows × Python 3.9, 3.10, 3.11, 3.12, 3.13 (15 jobs).
- Q: Should library logging handler attachment be fixed now or deferred? → A: Fix now — library imports must not attach handlers; CLI auto-configures on demand.
- Q: Backward compatibility for relocated scripts — add deprecation shims? → A: No backward-compat shim; document new invocation (python scripts/<name>.py) in CHANGELOG (Option B).
- Q: Security vulnerability reporting channel and disclosure policy? → A: GitHub Private Vulnerability Reporting; 90-day coordinated disclosure (Option B).
- Q: Live coverage service (Codecov/Coveralls) or static badges? → A: Static badges updated manually to match current pytest --cov output at release time (Option B).
- Q: How to prevent `.DS_Store` from being re-committed? → A: Add `.DS_Store` to `.gitignore`; remove any currently tracked files via `git rm --cached` (Option A).

## Success Criteria

- CI workflows present at repo root and structurally correct (matrix, working-directory, OIDC).
- `mypy docmeld` → zero errors; `pytest` → ≥309 passed / 5 skipped; ruff+black clean across the entire `docmeld/` directory (library source + scripts).
- Built wheel: contains `py.typed`, excludes `scripts/`.
- `LLMProvider` importable; a dummy provider injectable into `DocMeldParser` without hitting DeepSeek.
- Both READMEs: no `144`/`81%`/`[username]`/`docmeld/docmeld`; all 8 commands + 4 `process_*`
  methods documented.
- No tracked `.DS_Store`; health files present; CHANGELOG `[Unreleased]` updated; version still 0.3.0.
