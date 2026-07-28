# Implementation Plan: OSS-Standard Optimization & Launch Readiness

**Spec**: [spec.md](./spec.md) · **Branch**: `008-optimization-launch` · **Target version**: `0.4.0`

## Overview

Seven phases, ordered safest → most invasive. The full test suite (`pytest tests/`) and `mypy docmeld`
must stay green after every phase. Phases A, B, C are prerequisites — CI must run (A), health files and
packaging metadata must be in place (B), and the type checker must be enforced (C) before the substantive
refactors in D–E, so regressions are caught. (Phase C was completed ahead of B for practical reasons;
the ordering constraint is that A, B, and C are all complete before D begins.) Phases D–E are the code
changes. Phases F–G are documentation, done last so the numbers/commands documented match the final state.

**TDD enforcement for remaining phases (D–E):** Per Constitution Principle I (NON-NEGOTIABLE), each
Phase D and Phase E begins with a failing test before implementation. The test files are written first,
verified red, then production code makes them green. Phase B (health files) and F–G (docs) are
declarative and exempt from TDD.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Test-First Development | ✅ PASS | FR-015: test suite stays ≥309/5 throughout. Phase E adds `test_parser.py` + pytest markers. |
| II. Library-First, PyPI-Ready | ✅ PASS | FR-011 fixes logging handler attachment on import. FR-003 ensures scripts not in wheel. FR-007 adds `py.typed`. |
| III. Lightweight by Default | ✅ PASS | No new dependencies added; personal scripts moved out of the installable package. |
| IV. Unified Element Format | ✅ PASS | No element format changes. NFR-001: pipeline output identical. |
| V. Agent-Ready Outputs | ✅ PASS | No output format changes. Existing output contracts preserved. |
| VI. Production-Grade Quality | ✅ PASS | This is the entire goal: CI running, mypy zero errors, ruff/black enforced, dead code removed. |
| VII. Open-Source Excellence | ✅ PASS | Phase B adds all missing health files. Phase F fixes both READMEs. OIDC publishing. |

**Gate**: No violations. All principles preserved or strengthened.

## Technical Context

- **Language**: Python 3.9+ (minimum per pyproject, verified compatible via CI matrix)
- **Core Dependencies**: PyMuPDF (fitz), pymupdf4llm, pydantic, langchain-deepseek, pandas, openpyxl, docling (optional)
- **Build System**: setuptools (pyproject.toml PEP 621), build (python -m build)
- **Testing**: pytest (309 tests), pytest-cov, strict pytest markers (unit/integration/contract)
- **Linting/Formatting**: ruff, black (line-length=100), mypy (strict mode, now passing)
- **CI/CD**: GitHub Actions (test.yml, lint.yml, publish.yml) — relocated to repo root, working-directory: docmeld
- **Package Layout**: Nested — git root → docmeld/ (pyproject.toml) → docmeld/docmeld/ (importable package)
- **Publishing**: PyPI via OIDC trusted publishing (no long-lived tokens)
- **LLM Integration**: Currently DeepSeek-only via langchain-deepseek; Phase D introduces LLMProvider Protocol
- **Platforms**: macOS, Linux, Windows — all tested in CI

## Repository layout (context)

```
/Users/frank/A/DocMeld/            ← git root
├── .github/workflows/             ← MUST live here (was under docmeld/)
├── .pre-commit-config.yaml
├── README.md                      ← root README (optimize)
├── specs/008-optimization-launch/ ← this plan
└── docmeld/                       ← project dir (pyproject.toml here)
    ├── pyproject.toml
    ├── README.md                  ← canonical README shipped to PyPI (optimize)
    ├── CHANGELOG.md  CONTRIBUTING.md  LICENSE
    ├── scripts/                   ← personal batch scripts (NOT packaged)
    ├── tests/                     ← unit / integration / contract
    └── docmeld/                   ← importable package
        ├── __init__.py  parser.py  cli.py
        ├── bronze/ (backends/)  silver/  gold/
        ├── categorize/  prd/  workflow/  skills/  utils/
        └── py.typed               ← to be added
```

The package is nested one level below the git root. Rather than flatten it (disruptive, breaks the
published import path), CI runs with `working-directory: docmeld`.

---

## Phase A — Repo structure & CI  ✅ COMPLETE

**Goal**: make the good-but-dead workflows run; clean the tree.

1. `git mv docmeld/.github .github` — relocate workflows to the git root.
2. Rewrite each workflow with `defaults.run.working-directory: docmeld` so `pip install -e ".[dev]"`,
   `pytest`, ruff/black/mypy resolve against `docmeld/pyproject.toml`. `test.yml` also passes
   `working-directory: docmeld` to the Codecov action, adds `fail-fast: false` to the matrix, and
   covers the NFR-004 matrix: Ubuntu, macOS, Windows × Python 3.9–3.13 (15 jobs).
3. `publish.yml` → PyPI **OIDC trusted publishing** (`pypa/gh-action-pypi-publish@release/v1`,
   `permissions: id-token: write`, `environment: pypi`, `packages-dir: docmeld/dist/`). Dropped the
   `PYPI_API_TOKEN`/twine pattern.
4. Ensure `.DS_Store` is in `.gitignore`; `git rm --cached` any tracked `.DS_Store` files. (Clarified:
   `.gitignore` rule is the prevention mechanism — no pre-commit hook needed.)
5. Add `/.pre-commit-config.yaml` (pre-commit-hooks + ruff + black + mypy, scoped to `docmeld/`)
   and `/.github/dependabot.yml` (pip in `/docmeld`, github-actions in `/`, weekly).

**Verification**: workflows present at root; `pytest` still 309 passed / 5 skipped.

---

## Phase B — Community health & packaging metadata  ⬜ PENDING

**Goal**: satisfy GitHub community-health detection and PEP 561.

6. Add at repo root: `SECURITY.md` (GitHub Private Vulnerability Reporting instructions, 90-day
   coordinated disclosure, supported versions), `CODE_OF_CONDUCT.md`
   (Contributor Covenant 2.1), `.github/ISSUE_TEMPLATE/{bug_report.yml,feature_request.yml}`,
   `.github/PULL_REQUEST_TEMPLATE.md`, `CITATION.cff` (research-tool audience expects it).
7. Reconcile all URLs → `github.com/agentii-ai/DocMeld`: `docmeld/pyproject.toml` `[project.urls]`
   (+ add `Documentation`, `Changelog`), both READMEs, `CHANGELOG.md` compare links,
   `CONTRIBUTING.md` clone + citation.
8. `pyproject.toml`: real author name + email (confirm value with owner during impl);
   add Documentation/Changelog URLs.
9. Add `docmeld/docmeld/py.typed` (empty marker) and ensure it ships — with
   `[tool.setuptools.package-data] docmeld = ["py.typed"]` (or `include-package-data`).

**Verification**: `python -m build --wheel` then `unzip -l dist/*.whl` shows `docmeld/py.typed`,
no `scripts/`.

---

## Phase C — Fix the type bug + enforce mypy  ✅ COMPLETE

**Goal**: `mypy docmeld` → zero errors; keep it that way.

10. **`parser.py`**: add a `TYPE_CHECKING` block importing `PrdResult` (`docmeld.prd.models`),
    `WorkflowResult` (`docmeld.workflow.models`), `SkillsResult` (`docmeld.skills.models`). Runtime
    lazy imports of the generators are unchanged. (Fixes CF-3.)
11. **`pyproject.toml` `[tool.mypy]`**: add `files = ["docmeld"]` (scope out venv/tests) and a
    `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` + `follow_imports = "skip"` for
    `fitz`, `pymupdf4llm`, `docling.*`, `torch.*`, `pptx.*`, `langchain_deepseek.*`. `follow_imports
    = skip` prevents mypy from descending into docling→torch (whose sources aren't py3.9-clean).
    (Fixes CF-4.)
12. Clear the **46 latent errors** the fixed config exposed:
    - **`element_types.py`**: `BronzeElement` → `Union[...]` with a `TypeAlias` (TYPE_CHECKING import
      from `typing_extensions`); this also fixes CF-5 (py3.9 runtime union). `parse_element` map typed
      `dict[str, type[BaseModel]]`; return `cast("BronzeElement", model_cls(**data))`.
    - **`cli.py`**: the single reused `result` variable across command branches caused ~40 errors
      (each branch returns a different result type, but mypy widened to the first). Fix: give each
      branch its own variable (`proc_result`, `bronze_result`, `silver_result`, …) and replace the
      `hasattr(...)` probe with `isinstance(bronze_result, BronzeResult)` (import `BronzeResult`).
    - **`categorizer.py`**: `cast(...)` the three `json.loads`-derived returns (`no-any-return`).
    - **`element_extractor.py`**: annotate the dispatch variable `b: ParserBackend` (TYPE_CHECKING
      import) — fixes the assignment errors and makes the Protocol actually enforced (addresses MF-4).
    - **`docling_backend.py`**: wrap `export_fn(...)` returns in `str(...)` (`no-any-return` from a
      `getattr` result).

**Status**: done — `mypy docmeld` → `Success: no issues found in 42 source files`; `pytest` green.

**Verification**: `mypy docmeld` clean; `pytest tests/ -q` still 309/5.

---

## Phase D — Decouple the LLM provider  ⬜ PENDING

**Goal**: remove the DeepSeek lock-in (HF-2) behind a Protocol without changing default behavior.

**TDD**: Write `tests/unit/test_provider.py` FIRST (test dummy provider injection, verify it fails).
Then implement T040–T043; the test turns green.

13. **TEST FIRST** — `tests/unit/test_provider.py`: create a `DummyProvider` implementing the
    (not-yet-existing) Protocol, attempt to inject it via `DocMeldParser(provider=...)`, verify
    `process_prd/workflow/skills` are called without live DeepSeek. This test MUST fail before T041
    (Protocol not yet defined, provider parameter not yet on DocMeldParser). Then T041–T044 implement
    the Protocol, update DeepSeekClient, thread injection; the test turns green.
14. New `docmeld/gold/provider.py` defining an `LLMProvider` `Protocol` with the methods the code
    already relies on. Audit note: `DeepSeekClient.generate_prd` is misleadingly named — it is really
    "generate free-form text" and is also called by workflow/skills; `categorize_papers` and
    `generate_prd` both delegate to `_call_categorize_api`. Consolidate the surface to:
    `extract_metadata(...)`, `generate(prompt) -> str` (free-form), `categorize(...)`. Keep
    `generate_prd` as a thin deprecated alias for back-compat.
15. `DeepSeekClient` implements `LLMProvider` (structural — no inheritance needed). Move the
    `deepseek-chat` model name to a constructor default instead of two buried magic strings.
16. Replace `client: Any` in `prd/`, `workflow/`, `skills/generator.py` and `categorize/categorizer.py`
    with `LLMProvider`.
17. Thread an optional `provider: LLMProvider | None = None` (or `llm=`) through `DocMeldParser`
    (`__init__` and the five instantiation sites), defaulting to constructing a `DeepSeekClient` from
    env. This is the injection seam; default path is byte-for-byte the current behavior.

**Verification**: `test_provider.py` passes; `python -c "from docmeld.gold.provider import LLMProvider"`;
a dummy object with the three methods injects into `DocMeldParser` and drives prd/workflow/skills
without network; `pytest` green (existing gold/categorize tests already mock the client).

---

## Phase E — DRY, dead code, tests  ⬜ PENDING

**Goal**: consolidate duplication (MF-1), remove dead code (MF-2/MF-3), fix test hygiene (TF-2/TF-3).

**TDD**: Write `tests/unit/test_parser.py` FIRST (cover gold-failure semantics for single-file
`process_all`; provider injection from Phase D). These tests MUST fail before T053–T054. Then fix
the code; tests turn green.

18. **TEST FIRST** — `tests/unit/test_parser.py`: test that single-file `process_all` returns
    `successful=0, failed=1` when the gold stage fails (currently always reports `successful=1`).
    Test that a dummy `LLMProvider` (from Phase D) injected via `DocMeldParser` drives
    prd/workflow/skills without network. These MUST fail before Step 20.
19. New shared helpers in `utils/`, replacing all duplicated copies:
    - `utils/silver_io.py::load_silver_content(jsonl_path)` — replaces the verbatim
      `_load_silver_content` in prd/workflow/skills generators + near-identical aggregator logic.
    - `utils/content.py::aggregate_content(pages, max_chars=..., head_ratio=...)` — the 30k / 60-40
      split, with the constants named once (`MAX_CONTENT_CHARS`, `HEAD_RATIO`).
    - `utils/text.py::strip_code_fences(text)` — replaces the 6+ copies (deepseek_client, prd,
      workflow, skills, categorizer).
20. Remove dead code: `DocMeldParser.output_dir` field, `gold_failed` variable, `_merge_categories`
    in categorizer. Fix single-file `process_all` (MF-3) to report the actual gold failure in the
    returned `ProcessingResult` instead of hardcoded `successful=1, failed=0`. This is the fix that
    makes Step 18's test pass.
21. Apply pytest markers (TF-2) via a `pytest_collection_modifyitems` hook (or autouse) in
    `tests/conftest.py` that tags by directory (`unit/`→`unit`, etc.) — no per-test edits — so
    `pytest -m unit/integration/contract` selects correctly.
22. Publish the reusable API: export `generate_prd`/`generate_workflow`/`generate_skills`/
    `categorize_papers` (and `LLMProvider`) from their subpackage `__init__.py` files.
23. Include `docmeld/scripts/` in ruff/black lint scope (decided: format everything under `docmeld/`).
    Run ruff + black on the scripts directory; no separate config or exclusion needed.
24. Fix `setup_logging` to be library-safe (FR-011): remove handler attachment on import; CLI entry
    point configures logging explicitly on demand.

**Verification**: `pytest tests/ -q` green incl. new `test_parser.py`; `pytest -m unit` selects;
`mypy docmeld` still clean; `ruff check docmeld/ && black --check docmeld/` clean (full dir, scripts included).

---

## Phase F — Optimize BOTH READMEs  ⬜ PENDING

Apply to `docmeld/README.md` (canonical, PyPI) and root `README.md`; keep them consistent (the root
file may be a trimmed mirror pointing at the canonical one to prevent drift).

25. **Badges**: correct test count + coverage (measure live). Use static shields.io badges updated
    manually to match current `pytest --cov` output and PyPI version at release time. No live
    coverage service integration (Codecov/Coveralls deferred).
26. **CLI Reference**: add `categorize [--reorganize]`, `prd`, `workflow`, `skills`; correct
    `--backend` choices to `pymupdf|docling|pptx|soffice|auto` (default `auto`).
27. **New "Knowledge Generation" section** (after Gold): categorize / PRD / workflow / skills, each
    2–3 lines with CLI + Python API.
28. **Python API**: document `process_categorize/prd/workflow/skills` + result models
    (`CategorizeResult`, `PrdResult`, `WorkflowResult`, `SkillsResult`) and the new provider seam.
29. **Roadmap**: check off categorize/prd/workflow/skills; keep OCR, agent-prompt-gen, LangChain
    unchecked.
30. **Backends**: document auto-detection + pptx/soffice.
31. **Project structure tree**: add categorize/prd/skills/workflow subpackages + `scripts/` (not
    shipped) note + `py.typed`.
32. **Fix placeholder URLs** → `agentii-ai/DocMeld` (clone command, citation block).

**Verification**: grep both files for `144`/`81%`/`[username]`/`docmeld/docmeld` → none; all 8
commands + 4 `process_*` methods present.

---

## Phase G — CHANGELOG  ⬜ PENDING

33. Move `[Unreleased]` to the top of `docmeld/CHANGELOG.md` (currently mis-ordered between 0.2.0 and
    0.1.0). Add an `[Unreleased]` entry summarizing this work: scripts relocated out of the package,
    `LLMProvider` abstraction, parser type-bug + py3.9 union fix, mypy gating, CI moved to root, OIDC
    publishing, `py.typed`, health files, DRY refactor, README overhaul. Fix compare-link URLs.
34. **Do not bump the version or publish** — the `[Unreleased]` block is the staging area for a future
    `0.4.0` release cut by the owner.

---

## Critical files

- **CI/structure**: `.github/workflows/{test,lint,publish}.yml` (moved+rewritten),
  `.github/dependabot.yml`, `.pre-commit-config.yaml`
- **Health**: `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `.github/ISSUE_TEMPLATE/*`,
  `.github/PULL_REQUEST_TEMPLATE.md`
- **Packaging**: `docmeld/pyproject.toml`, `docmeld/docmeld/py.typed` (new)
- **Code (done in C)**: `docmeld/docmeld/parser.py`, `cli.py`, `bronze/element_types.py`,
  `bronze/element_extractor.py`, `bronze/backends/docling_backend.py`, `categorize/categorizer.py`
- **Code (D/E)**: `docmeld/docmeld/gold/{provider.py (new),deepseek_client.py}`,
  `{prd,workflow,skills}/generator.py`, `utils/{silver_io,content,text}.py` (new), subpackage
  `__init__.py` files
- **Tests**: `docmeld/tests/conftest.py`, `docmeld/tests/unit/test_parser.py` (new)
- **Docs**: `docmeld/README.md`, root `README.md`, `docmeld/CHANGELOG.md`, `docmeld/CONTRIBUTING.md`
- **Scripts (done)**: relocated to `docmeld/scripts/` with sibling imports + de-hardcoded `summarize_rl.py`

## Global verification (from `/Users/frank/A/DocMeld/docmeld`, `source venv/bin/activate`)

1. `pytest tests/ -q` → ≥309 passed, 5 skipped, after every phase.
2. `pytest -m unit -q` / `-m integration` select tests (Phase E marker fix).
3. `mypy docmeld` → 0 errors.
4. `ruff check docmeld/ && black --check docmeld/` → clean (full dir, library + scripts).
5. `python -c "import docmeld; from docmeld import DocMeldParser"`; `docmeld --help` lists 8 commands.
6. `python -c "from docmeld.gold.provider import LLMProvider"`; dummy-provider injection works.
7. `python -m build --wheel`; `unzip -l dist/*.whl` shows `docmeld/py.typed`, no `scripts/`; clean up
   `dist/`/`build/`.
8. `pytest --cov=docmeld --cov-report=term | tail -1` → record TOTAL % for static shields.io README badge.
9. Both READMEs grep-clean of stale strings; all commands/methods present.
10. `git status` free of stray `.DS_Store`; `.github/` at repo root.

## Risks & mitigations

- **Provider refactor breaks mocked tests** — existing gold/categorize tests patch the client; keep
  the `generate_prd` alias and the same method behavior so mocks still match. Run tests per module.
- **`follow_imports=skip` hides real type issues in first-party code** — scope is limited to named
  third-party modules only; first-party code is still fully checked.
- **Formatting the relocated scripts churns diffs** — scripts are now included in lint scope per
  NFR-002; perform formatting as a single atomic commit to keep the diff isolated.
- **Version drift** — `__version__` is hardcoded in two places; out of scope to single-source now,
  but noted for the 0.4.0 cut.
