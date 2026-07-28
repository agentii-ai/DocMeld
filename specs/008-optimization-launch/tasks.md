# Tasks: OSS-Standard Optimization & Launch Readiness

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Branch**: `008-optimization-launch`

Status legend: `[x]` done · `[~]` in progress · `[ ]` pending
Run `pytest tests/` and `mypy docmeld` after every phase; both must stay green.

---

## Phase 0 — Script relocation (prerequisite, done before formal phases)

- [x] T001 `git mv` the 5 tracked package scripts (`summarize.py`, `summarize_bschool.py`,
      `batch_pipeline.py`, `fix_summaries.py`, `run_loop_prompts.py`) from `docmeld/docmeld/` to
      `docmeld/scripts/`, plus root `summarize_rl.py` → `docmeld/scripts/summarize_rl.py`.
- [x] T002 Fix sibling imports in `scripts/batch_pipeline.py` and `scripts/fix_summaries.py`
      (`from docmeld.summarize import …` → `sys.path.insert` + `from summarize import …`).
- [x] T003 De-hardcode `scripts/summarize_rl.py`: drop `sys.path.insert`, convert the hardcoded
      `BASE` path to a required `folder` argparse arg, add `--workers`.
- [x] T004 [P] Update usage docstrings in relocated scripts (`python -m docmeld.X` →
      `python scripts/X.py`).
- [x] T005 [P] Add `docmeld/scripts/README.md` explaining these are personal/example scripts, not part
      of the installed package.

## Phase A — Repo structure & CI  ✅

- [x] T010 [US1] `git mv docmeld/.github .github` — relocate workflows from `docmeld/.github/` to git root.
- [x] T011 [US1] Rewrite `.github/workflows/test.yml`: add `defaults.run.working-directory: docmeld`,
      `fail-fast: false`, Codecov `working-directory: docmeld`.
- [x] T012 [P] [US1] Rewrite `.github/workflows/lint.yml`: add `defaults.run.working-directory: docmeld`.
- [x] T013 [P] [US1] Rewrite `.github/workflows/publish.yml`: OIDC trusted publishing
      (`pypa/gh-action-pypi-publish@release/v1`, `id-token: write`, `environment: pypi`,
      `packages-dir: docmeld/dist/`), build in `docmeld/`.
- [x] T014 `git rm --cached` the three tracked `.DS_Store` files; verify `.DS_Store` already in
      `.gitignore` (prevention mechanism per spec clarification — no pre-commit hook needed).
- [x] T015 [P] Add `/.pre-commit-config.yaml` (pre-commit-hooks, ruff, black, mypy scoped to `docmeld/`).
- [x] T016 [P] Add `/.github/dependabot.yml` (pip `/docmeld`, github-actions `/`, weekly).
- [x] T017 Verify `pytest` → 309 passed / 5 skipped (baseline unchanged). ✅

## Phase C — Fix type bug + enforce mypy  ✅ (done ahead of B)

- [x] T030 [P] [US3] `docmeld/docmeld/parser.py`: `TYPE_CHECKING` import of `PrdResult`/`WorkflowResult`/
      `SkillsResult` from their subpackage models. (CF-3)
- [x] T031 [US3] `docmeld/pyproject.toml` `[tool.mypy]`: `files = ["docmeld"]` + overrides
      (`ignore_missing_imports`, `follow_imports="skip"`) for fitz/pymupdf4llm/docling/torch/pptx/
      langchain_deepseek. (CF-4)
- [x] T032 [P] [US3] `docmeld/docmeld/bronze/element_types.py`: `BronzeElement` → `Union[...]` +
      `TypeAlias`; py3.9-safe (CF-5); `parse_element` map `type[BaseModel]` + `cast`.
- [x] T033 [P] [US3] `docmeld/docmeld/cli.py`: per-branch result variables + `isinstance(bronze_result,
      BronzeResult)`; import `BronzeResult`.
- [x] T034 [P] [US3] `docmeld/docmeld/categorize/categorizer.py`: `cast(...)` the 3 `json.loads` returns.
- [x] T035 [P] [US3] `docmeld/docmeld/bronze/element_extractor.py`: annotate dispatch var
      `b: ParserBackend` (Protocol now enforced).
- [x] T036 [P] [US3] `docmeld/docmeld/bronze/backends/docling_backend.py`: wrap `export_fn(...)` returns
      in `str(...)`.
- [x] T037 Verify `mypy docmeld` → `Success: no issues found` (46 source files post-refactor). ✅
- [x] T038 Verify `pytest` still 309/5. ✅

## Phase B — Community health & packaging metadata  ✅

- [x] T020 [P] [US6] Add `SECURITY.md` at repo root (GitHub Private Vulnerability Reporting, 90-day
      coordinated disclosure, supported versions).
- [x] T021 [P] [US6] Add `CODE_OF_CONDUCT.md` at repo root (Contributor Covenant 2.1).
- [x] T022 [P] [US6] Add `.github/ISSUE_TEMPLATE/bug_report.yml` + `feature_request.yml`.
- [x] T023 [P] [US6] Add `.github/PULL_REQUEST_TEMPLATE.md`.
- [x] T024 [P] [US6] Add `CITATION.cff` at repo root.
- [x] T025 [US2] Reconcile all repo URLs → `github.com/agentii-ai/DocMeld` in:
      `docmeld/pyproject.toml` `[project.urls]` (+ Documentation, Changelog),
      `docmeld/CHANGELOG.md` compare links, `docmeld/CONTRIBUTING.md` clone + citation.
- [x] T026 [US2] `docmeld/pyproject.toml`: real author name + email (confirm value with owner).
- [x] T027 [US2] Add `docmeld/docmeld/py.typed` (empty marker file, PEP 561) + ensure it ships via
      `[tool.setuptools.package-data] docmeld = ["py.typed"]` in `docmeld/pyproject.toml`.
- [x] T028 Verify wheel: `cd docmeld && python -m build --wheel`; `unzip -l dist/*.whl` shows
      `docmeld/py.typed`, no `scripts/`; clean `dist/`/`build/`.

## Phase D — Decouple LLM provider  ✅

- [x] T040 [US4] **TEST FIRST** Add `docmeld/tests/unit/test_provider.py`: `DummyProvider` implementing
      the (not-yet-existing) `LLMProvider` Protocol, injected via `DocMeldParser(provider=...)`,
      verify prd/workflow/skills called without live DeepSeek. **MUST fail before T041** — verify red
      (Protocol not yet defined, provider parameter not yet on `DocMeldParser`).
- [x] T041 [US4] New `docmeld/docmeld/gold/provider.py`: `LLMProvider` Protocol
      (`extract_metadata`, `generate`, `categorize`). Per contract: structural subtyping, no
      inheritance required.
- [x] T042 [US4] `docmeld/docmeld/gold/deepseek_client.py`: rename `generate_prd` → `generate` with a
      deprecated `generate_prd` alias; move `deepseek-chat` model name to a constructor default;
      class structurally conforms to `LLMProvider`.
- [x] T043 [P] [US4] Replace `client: Any` with `LLMProvider` in: `docmeld/docmeld/prd/generator.py`,
      `docmeld/docmeld/workflow/generator.py`, `docmeld/docmeld/skills/generator.py`,
      `docmeld/docmeld/categorize/categorizer.py`.
- [x] T044 [US4] Thread optional `provider: LLMProvider | None = None` through `DocMeldParser`
      (`docmeld/docmeld/parser.py` — `__init__` + 5 instantiation sites); default = env-built
      `DeepSeekClient` (byte-for-byte identical to current behavior).
- [x] T045 Verify: `test_provider.py` passes; `from docmeld.gold.provider import LLMProvider`
      imports; dummy provider drives prd/workflow/skills without network; `pytest` green; `mypy` clean.

## Phase E — DRY, dead code, tests  ✅

- [x] T050 [US6] **TEST FIRST** Add `docmeld/tests/unit/test_parser.py`: test single-file
      `process_all` reports real gold failure (`successful=0, failed=1`); test dummy `LLMProvider`
      injection drives prd/workflow/skills without network. **MUST fail before T055** (code still
      reports unconditional success; dead code not yet removed). Verify red, then proceed.
- [x] T051 [P] [US6] New `docmeld/docmeld/utils/silver_io.py::load_silver_content(jsonl_path)` —
      replace 4+ verbatim copies in `prd/generator.py`, `workflow/generator.py`,
      `skills/generator.py`, `categorize/aggregator.py`.
- [x] T052 [P] [US6] New `docmeld/docmeld/utils/content.py::aggregate_content(pages, max_chars,
      head_ratio)` — name constants `MAX_CONTENT_CHARS`/`HEAD_RATIO`; replace the triplicated
      `_aggregate_content` in prd/workflow/skills generators.
- [x] T053 [P] [US6] New `docmeld/docmeld/utils/text.py::strip_code_fences(text)` — replace 6+ copies
      in `deepseek_client.py`, `prd/generator.py`, `workflow/generator.py`, `skills/generator.py`,
      `categorize/categorizer.py`.
- [x] T054 [US6] Remove dead code in `docmeld/docmeld/`: `parser.py` (`output_dir` field, `gold_failed`
      variable), `categorize/categorizer.py` (`_merge_categories`).
- [x] T055 [US6] Fix single-file `process_all` in `docmeld/docmeld/parser.py` to report real gold-stage
      failure in `ProcessingResult` (MF-3). **This makes T050's test pass.**
- [x] T056 [P] [US6] `docmeld/tests/conftest.py`: add `pytest_collection_modifyitems` hook tagging
      tests by directory (`unit/`→`unit`, `integration/`→`integration`, `contract/`→`contract`)
      so `pytest -m unit/integration/contract` selects correctly. (TF-2)
- [x] T057 [P] [US6] Export `generate_prd`/`generate_workflow`/`generate_skills`/`categorize_papers` +
      `LLMProvider` from subpackage `__init__.py` files: `docmeld/docmeld/prd/__init__.py`,
      `docmeld/docmeld/workflow/__init__.py`, `docmeld/docmeld/skills/__init__.py`,
      `docmeld/docmeld/categorize/__init__.py`, `docmeld/docmeld/gold/__init__.py`.
- [x] T058 [US6] Include `docmeld/scripts/` in ruff/black lint scope: format `docmeld/scripts/*.py`
      with `ruff --fix` + `black`; no exclusion config needed. (NFR-002: entire `docmeld/` dir must
      pass `ruff check` + `black --check`.)
- [x] T059 [US6] Fix `setup_logging` in `docmeld/docmeld/cli.py` to be library-safe (FR-011): remove
      handler attachment on import; CLI entry point configures logging explicitly on demand. Verify
      `python -c "import docmeld"` does not mutate the `"docmeld"` logger's handlers.
- [x] T060 Verify: `pytest tests/ -q` green incl. `test_parser.py` + `test_provider.py`;
      `pytest -m unit` selects; `mypy docmeld` clean; `ruff check docmeld/ && black --check docmeld/`
      clean (library + scripts).

## Phase F — Optimize both READMEs  ✅

- [x] T061 [US5] Update badges in `docmeld/README.md` and root `README.md`: measure live test count +
      coverage via `pytest --cov`; use static shields.io badges (no Codecov/Coveralls integration).
- [x] T062 [P] [US5] Update CLI Reference in `docmeld/README.md`: add `categorize [--reorganize]`,
      `prd`, `workflow`, `skills`; fix `--backend` choices to `pymupdf|docling|pptx|soffice|auto`
      (default `auto`).
- [x] T063 [P] [US5] Add "Knowledge Generation" section to `docmeld/README.md` (after Gold):
      categorize / PRD / workflow / skills, each 2–3 lines with CLI + Python API examples.
- [x] T064 [P] [US5] Update Python API section in `docmeld/README.md`: document
      `process_categorize`/`process_prd`/`process_workflow`/`process_skills` + result models
      (`CategorizeResult`, `PrdResult`, `WorkflowResult`, `SkillsResult`) + provider injection seam.
- [x] T065 [P] [US5] Update Roadmap in `docmeld/README.md`: check off categorize/prd/workflow/skills;
      keep OCR, agent-prompt-gen, LangChain unchecked.
- [x] T066 [P] [US5] Update Backends section in `docmeld/README.md`: document auto-detection +
      pptx/soffice; correct default to `auto`.
- [x] T067 [P] [US5] Update project structure tree in `docmeld/README.md`: add
      categorize/prd/skills/workflow subpackages + `scripts/` note (not shipped) + `py.typed`.
- [x] T068 [P] [US5] Fix all placeholder URLs → `agentii-ai/DocMeld` in `docmeld/README.md` and root
      `README.md` (clone command, citation block, PyPI/homepage links).
- [x] T069 [US5] Sync root `README.md` with `docmeld/README.md` — root may be a trimmed mirror
      pointing at the canonical one to prevent drift; ensure both are consistent.
- [x] T070 Verify: grep both READMEs for `144`/`81%`/`[username]`/`[your-username]`/`docmeld/docmeld`
      → zero matches; all 8 CLI commands + 4 `process_*` methods present.

## Phase G — CHANGELOG  ✅

- [x] T071 Reorder `[Unreleased]` to top of `docmeld/CHANGELOG.md` (currently mis-ordered between
      0.2.0 and 0.1.0); fix compare-link URLs to `agentii-ai/DocMeld`.
- [x] T072 [P] Add `[Unreleased]` entry to `docmeld/CHANGELOG.md` summarizing all of 008: scripts
      relocated out of package, `LLMProvider` abstraction, parser type-bug + py3.9 union fix, mypy
      gating, CI moved to root, OIDC publishing, `py.typed`, health files, DRY refactor, README
      overhaul.
- [x] T073 Confirm version stays `0.3.0` in `docmeld/pyproject.toml` + `docmeld/docmeld/__init__.py`
      (no bump, no publish).

## Final verification  ✅

- [x] T080 Full sweep: `pytest tests/ -q` (≥309/5), `mypy docmeld` (0), `ruff check docmeld/ && black --check docmeld/` clean, `docmeld
      --help` (8 commands), wheel check (`py.typed` yes / `scripts/` no), coverage measured, both
      READMEs grep-clean, `git status` free of `.DS_Store`, `.github/` at root.

---

## Story → Phase Mapping

| User Story | Priority | Phase(s) | Task IDs |
|------------|----------|----------|----------|
| US1 — CI runs on push/PR | P1 | Phase A | T010–T017 |
| US2 — Published package clean & typed | P1 | Phase B + A | T025–T028 (+ T013) |
| US3 — Type checker green & enforced | P1 | Phase C | T030–T038 |
| US4 — LLM provider swappable | P2 | Phase D | T040–T045 |
| US5 — Accurate, top-tier READMEs | P1 | Phase F | T061–T070 |
| US6 — Community health & maintainability | P2 | Phase B + E | T020–T024, T050–T060 |

## Dependency Graph

```
Phase 0 (scripts) ✅ ──┐
Phase A (CI) ✅ ───────┤
                       ├──▶ Phase D (LLM provider) ──▶ Phase E (DRY/tests)
Phase B (health) ──────┤                                    │
Phase C (mypy) ✅ ─────┘                                    ▼
                                                 Phase F (READMEs) ──▶ Phase G (CHANGELOG) ──▶ Final (T080)
```

**Key**: Phase D requires A+C (CI and mypy must gate code changes). Phase E requires D (uses `LLMProvider`).
Phases B, F, G are independent of D/E and may run in parallel.

## Parallel Opportunities

| Phase | Parallelizable tasks | Notes |
|-------|---------------------|-------|
| Phase B | T020–T024 (all 5 health files) | Independent files, no shared state |
| Phase D | T043 (4 files all typed `client: Any` → `LLMProvider`) | Same change pattern across 4 modules |
| Phase E | T051, T052, T053 (3 new utils) + T056, T057 | Utils are independent; conftest + exports can run alongside |
| Phase F | T062–T068 (7 README content updates) | All against same files but different sections — batch strategically |
| Phase G | T072 (CHANGELOG entry) | Independent of T071 ordering fix |

## Progress summary (as of 2026-07-28)

**Complete**: ALL PHASES. 62/62 tasks done.
- Phase 0 (script relocation), Phase A (CI to root + hygiene), Phase B (health + packaging),
  Phase C (type bug fixed, mypy green — 46 latent errors cleared), Phase D (LLM provider TDD),
  Phase E (DRY refactor, dead code, pytest markers, logging fix), Phase F (both READMEs),
  Phase G (CHANGELOG), Final verification.
**Invariant held throughout**: `pytest` = 315 passed / 5 skipped; no observable pipeline behavior change.
