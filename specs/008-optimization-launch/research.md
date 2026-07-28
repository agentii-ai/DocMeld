# Research: OSS-Standard Optimization & Launch Readiness

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-07-28

## 1. LLMProvider Protocol Surface

**Decision**: Three-method Protocol: `extract_metadata(...)`, `generate(prompt) -> str`, `categorize(...)`.

**Rationale**: Audit of `DeepSeekClient` reveals `generate_prd` is misleadingly named — it generates free-form text and is called by workflow/skills, not just PRD. `categorize_papers` and `generate_prd` both delegate to `_call_categorize_api`. The consolidated surface removes the implicit assumption that "text generation" is a PRD-specific operation.

**Alternatives considered**:
- Single `invoke(prompt) -> str` method — too coarse; loses type safety and semantic distinction between structured (categorization/metadata) vs. free-form generation.
- Keep all existing method names — preserves back-compat but perpetuates misleading naming for new providers.
- Full abstraction including async — unnecessary now; can be added later as `AsyncLLMProvider` Protocol.

**Back-compat**: `generate_prd` retained as a thin deprecated alias that delegates to `generate`.

## 2. pytest Marker Strategy

**Decision**: `pytest_collection_modifyitems` hook in `tests/conftest.py` that auto-tags by directory.

**Rationale**: 314 existing tests have no markers. Per-test `@pytest.mark.unit` edits would touch every file and create merge conflicts. The conftest hook tags tests by directory (`tests/unit/` → `unit`, `tests/integration/` → `integration`, `tests/contract/` → `contract`) with zero per-test edits.

**Alternatives considered**:
- Per-test decorators — more explicit but requires 314 file edits.
- `pytest.ini` testpaths-based selection — doesn't support `-m` flag.
- Auto-use marker fixture — more complex, less standard.

## 3. Scripts Lint Scope

**Decision**: Include `docmeld/scripts/` in ruff/black lint scope (entire `docmeld/` directory).

**Rationale**: Clarified during spec review. Top-tier OSS projects format all tracked code uniformly. The scripts, while personal utilities, are part of the repository and should meet the same quality bar. The lint commands become `ruff check docmeld/ && black --check docmeld/`.

**Alternatives considered**:
- Exclude scripts (separate config) — simpler but creates a two-tier quality structure.
- Relaxed rules for scripts — adds config complexity for marginal benefit.

## 4. CI Matrix Configuration

**Decision**: Ubuntu, macOS, Windows × Python 3.9, 3.10, 3.11, 3.12, 3.13 (15 jobs).

**Rationale**: Matches top-tier Python OSS norms (pydantic, httpx). Windows is essential for a doc-processing library (many enterprise users on Windows). Python 3.9 is the declared minimum; 3.13 is the latest stable. `fail-fast: false` ensures all jobs report regardless of partial failures.

**Alternatives considered**:
- Linux-only matrix — faster but misses cross-platform edge cases.
- Skip Windows — common shortcut but DocMeld's PyMuPDF/docling deps have known platform-specific behavior.
- Python 3.9 + 3.13 only — too sparse for a library with runtime type concerns.

## 5. Logging Library-Safety

**Decision**: Remove handler attachment from `setup_logging`; CLI entry point attaches handlers explicitly.

**Rationale**: Top-tier OSS libraries (pydantic, httpx, rich) never mutate the logging configuration on import. The current `setup_logging` adds a `StreamHandler` to the shared `"docmeld"` logger at module level, which is a side effect unacceptable for library consumers. The fix: make the logging setup a no-op at import time; the CLI entry point calls a dedicated `configure_cli_logging()` when invoked.

**Alternatives considered**:
- Defer to future release — contradicts the goal of this being a quality/hygiene release.
- Guard with `if __name__ == "__main__"` — doesn't help for `python -m docmeld` or programmatic use.
- Use `logging.NullHandler` by default — clean but requires consumer to understand they need to add handlers; acceptable but less user-friendly for CLI.
