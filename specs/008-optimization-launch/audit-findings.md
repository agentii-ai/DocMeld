# Audit Findings Reference — DocMeld OSS Standard Evaluation

Source: three parallel deep-review agents (repo hygiene/CI, code architecture, testing/docs) plus
direct verification (running `mypy`, `pytest`, reading code/config). Benchmark: top-tier Python OSS
(`rich`, `pydantic`, `httpx`). Date: 2026-07-28. Full remediation tracked in [tasks.md](./tasks.md).

Severity: **Critical** (breaks a core promise: CI, correctness, install) · **High** (blocks OSS
quality/generality) · **Medium** (maintainability/polish).

---

## Critical

| ID | Finding | Evidence | Fix / Phase |
|----|---------|----------|-------------|
| CF-1 | CI never runs — workflows under `docmeld/.github/`, not repo root | No `.github/` at git root; GH Actions only reads `<root>/.github/workflows/` | Phase A ✅ |
| CF-2 | LICENSE/CONTRIBUTING/CHANGELOG invisible to GitHub (under `docmeld/`) | GH community-health scans root/`.github/` | Phase A/B |
| CF-3 | `parser.py` returns `PrdResult`/`WorkflowResult`/`SkillsResult` never imported | grep: only used as annotations; defs in `{prd,workflow,skills}/models.py` | Phase C ✅ |
| CF-4 | mypy not enforced — halted on missing stubs; hid 46 latent errors | `mypy docmeld/` → 4 stub errors, then 46 real errors once cleared | Phase C ✅ |
| CF-5 | `BronzeElement` runtime `X\|Y` union breaks import on Python 3.9 (pkg claims ≥3.9) | RHS-of-assignment PEP 604 union in `element_types.py:155` | Phase C ✅ |

## High

| ID | Finding | Evidence | Fix / Phase |
|----|---------|----------|-------------|
| HF-1 | Personal scripts shipped in the wheel | `summarize*.py`, `batch_pipeline.py`, `fix_summaries.py`, `run_loop_prompts.py` inside `docmeld/docmeld/`; root `summarize_rl.py` had `sys.path` hack + hardcoded path | Phase 0 ✅ |
| HF-2 | LLM provider hardcoded to DeepSeek | `DeepSeekClient` new'd in 5 sites; `client: Any` in every generator; DeepSeek-only `env_loader` | Phase D |
| HF-3 | No `py.typed` — consumers get no types despite strict-mypy code | absent from `docmeld/docmeld/` | Phase B |
| HF-4 | URL chaos: 4 repo owners | remote `agentii-ai/DocMeld`; pyproject `docmeld/docmeld`; READMEs `agentii-ai/docmeld`+`[username]`; CHANGELOG/CONTRIBUTING `[username]` | Phase B/F/G |
| HF-5 | Placeholder author, no email | `authors=[{name="DocMeld Contributors"}]`, no `Author-email` | Phase B |

## Medium

| ID | Finding | Evidence | Fix / Phase |
|----|---------|----------|-------------|
| MF-1 | DRY: `_load_silver_content` (×4), `_aggregate_content` 30k/60-40 (×3), code-fence strip (×6+) | prd/workflow/skills generators, aggregator, deepseek_client, categorizer | Phase E |
| MF-2 | Dead code: `output_dir` field, `gold_failed` var, `_merge_categories` | parser.py, categorizer.py | Phase E |
| MF-3 | Single-file `process_all` reports success even on gold failure | parser.py hardcodes `successful=1, failed=0` | Phase E |
| MF-4 | Backend dispatch not extensible; Protocol unused as a type | `if/elif` in element_extractor; `choices=[…]` ×6 in cli; `b` untyped | partial (Phase C typed `b`); registry deferred |
| MF-5 | Library attaches log handlers via `setup_logging` on shared logger | utils/logging.py; `ProcessingResult.log_file` always `""` | noted; optional |
| TF-1 | Stale README badges/claims (both files) | 144/81% vs real 314 collected/309 passed; missing 4 commands; wrong backends; unchecked roadmap | Phase F |
| TF-2 | pytest markers declared but never applied → `-m` broken | no `@pytest.mark.*`; `--strict-markers` set | Phase E |
| TF-3 | No `test_parser.py`; `process_*` covered only indirectly | tests/ listing | Phase E |
| TF-4 | Missing SECURITY.md, CODE_OF_CONDUCT.md, CITATION.cff, issue/PR templates, pre-commit, dependabot | repo scan | Phase A/B |

## Retained strengths (do not regress)

- Clean medallion architecture; single-responsibility bronze/silver/gold stage processors.
- Minimal, side-effect-free top-level API (`__init__.py` exports only `DocMeldParser`/`__version__`
  via PEP 562 lazy `__getattr__`).
- Real `ParserBackend` Protocol with centralized post-processing (element_id/parent_id/table
  summaries) — no per-backend duplication of that logic.
- Pydantic result models throughout; single named logger; no bare `except:`; no `print()` in library.
- Exemplary CHANGELOG (Keep-a-Changelog + SemVer); thorough CONTRIBUTING (TDD, conventional commits).
- Version consistent across `pyproject`/`__init__`/git tag `v0.3.0`; build/venv artifacts correctly
  gitignored.
- Test suite is substantive: 314 collected across unit/integration/contract, AI calls properly
  mocked (no live API in CI), meaningful assertions.

## Confirmed baseline metrics

- Tests: **314 collected, 309 passed, 5 skipped** (README claimed 144).
- Element types: **14** (`title, text, table, image, chart, formula, header, footer, footnote,
  endnote, smartart, notes, group, comment`).
- Package modules: ~23, ~4,260 LOC. Version `0.3.0`.
- mypy after Phase C: **`Success: no issues found in 42 source files`** (was 4 blocking + 46 latent).
