# Tasks: MVP Word Document (DOC/DOCX) Data Pipeline

**Input**: Design documents from `specs/006-mvp-doc-pipeline/`
**Prerequisites**: spec.md (user stories), plan.md (architecture), research.md (decisions), data-model.md (entities), contracts/ (schema), quickstart.md (samples)

**Tests**: Required per constitution (TDD — tests written before implementation, 90%+ coverage target). Existing 144 tests must remain green.

**Organization**: Tasks grouped by user story, aligned with the 4 incremental phases from plan.md. Each story is independently testable with sample files from `samples/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths relative to `docmeld/`

---

## Phase 1: Setup & Versioning

**Purpose**: Prepare the project for DOC/DOCX pipeline development. Existing PDF pipeline must remain unaffected.

- [x] T001 Verify existing 144 tests pass (baseline): `cd docmeld && source venv/bin/activate && pytest tests/ -v`
- [x] T002 [P] Bump version from 0.1.0 to 0.2.0 in `docmeld/pyproject.toml`
- [x] T003 [P] Bump version from 0.1.0 to 0.2.0 in `docmeld/docmeld/__init__.py`
- [x] T004 [P] Add CHANGELOG entry for 0.2.0 in `docmeld/CHANGELOG.md` (DOC/DOCX pipeline, 10 element types, soffice backend)
- [x] T005 [P] Add `sample_*.docx` test fixtures to `docmeld/samples/` (verify 6 sample files exist)

**Checkpoint**: Version bumped to 0.2.0, samples ready, existing tests green.

---

## Phase 2: Foundational — Element Type Extension & Schema

**Purpose**: Extend the element type system from 4 to 10 types. This is a blocking prerequisite for all user stories — both bronze extraction and silver rendering depend on the new element models.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Phase

- [x] T006 [P] Write unit tests for 6 new element type Pydantic models in `docmeld/tests/unit/test_element_types.py` (ChartElement, FormulaElement, HeaderElement, FooterElement, FootnoteElement, EndnoteElement — test validation rules, default values, type discrimination)
- [x] T007 [P] Write contract test for 10-type element schema in `docmeld/tests/contract/test_element_schema.py` (validate sample JSON against `element-schema.json`, test backward compatibility with 4-type documents)

### Implementation for Foundational Phase

- [x] T008 [P] Add ChartElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, chart_type, content, image, image_name, page_no, element_id, parent_id)
- [x] T009 [P] Add FormulaElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, formula_type, page_no, element_id, parent_id)
- [x] T010 [P] Add HeaderElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, page_scope, page_no, element_id, parent_id)
- [x] T011 [P] Add FooterElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, page_scope, page_no, element_id, parent_id)
- [x] T012 [P] Add FootnoteElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, reference_id, page_no, element_id, parent_id)
- [x] T013 [P] Add EndnoteElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, reference_id, page_no, element_id, parent_id)
- [x] T014 Expand `BronzeElement` union type in `docmeld/docmeld/bronze/element_types.py` to include all 10 element types
- [x] T015 Update `parse_element()` dispatch function in `docmeld/docmeld/bronze/element_types.py` to handle chart, formula, header, footer, footnote, endnote
- [x] T016 Run T006 and T007 tests — verify they PASS with the new models

**Checkpoint**: 10 element types, contract validated, backward compatible with 4-type documents.

---

## Phase 3: User Story 1 — Process Single DOCX File to Bronze (Priority: P1) 🎯 MVP

**Goal**: Accept a .docx file path, extract 4 core element types (text, table, title, image) via docling backend, produce bronze JSON with sanitized filename, hash suffix, and output folder.

**Independent Test**: Run `docmeld bronze samples/sample_multipage.docx --backend docling` → verify `sample_multipage_<hash>/` folder created with `.json` containing elements with types, page_no, element_id, parent_id fields.

### Tests for User Story 1

- [x] T017 [P] [US1] Write unit test for docling backend .docx extraction (SectionHeaderItem→title, TextItem→text, TableItem→table, PictureItem→image) in `docmeld/tests/unit/test_docling_backend.py` using `samples/sample_multipage.docx`
- [x] T018 [P] [US1] Write integration test for .docx bronze processing (single file, verify JSON output, idempotency) in `docmeld/tests/integration/test_bronze_pipeline.py`
- [x] T019 [P] [US1] Write integration test for filename sanitization with .docx extension in `docmeld/tests/integration/test_bronze_pipeline.py` (verify special chars, hash suffix, .docx extension preserved)

### Implementation for User Story 1

- [x] T020 [US1] Rewrite `DoclingBackend.extract_elements()` in `docmeld/docmeld/bronze/backends/docling_backend.py` to accept .docx paths (map docling DoclingDocument items to 4 element types: title, text, table, image)
- [x] T021 [US1] Generalize `BronzeProcessor.process_file()` in `docmeld/docmeld/bronze/processor.py` to accept both .pdf and .docx paths (detect format, route to appropriate backend)
- [x] T022 [US1] Generalize `BronzeProcessor.process_folder()` in `docmeld/docmeld/bronze/processor.py` to glob both `*.pdf` and `*.docx` files
- [x] T023 [US1] Update `element_extractor.extract_elements()` in `docmeld/docmeld/bronze/element_extractor.py` to accept `backend="docling"` with format routing (.docx → DoclingBackend)
- [x] T024 [US1] Verify `DocMeldParser.__init__()` in `docmeld/docmeld/parser.py` already accepts .docx paths (`Path.is_dir()` check is extension-agnostic — add .docx to help text only if needed)
- [x] T025 [US1] Fix `SilverProcessor.process()` in `docmeld/docmeld/silver/processor.py` to set source filename dynamically from bronze JSON's parent document stem + extension instead of hardcoding `.pdf` suffix (line 58: `source = json_path.stem + ".pdf"` → detect actual extension)
- [x] T026 [US1] Run T017-T019 tests — verify all PASS

**Checkpoint**: Single .docx → bronze JSON works with 4 element types. Idempotent. Sanitized filenames.

---

## Phase 4: User Story 3 — Process Folder of DOCX in Batch (Priority: P1)

**Goal**: Process a folder containing .docx files in batch mode with format filtering, skip logic for unsupported formats, and progress indicators.

**Independent Test**: Run `docmeld bronze samples/ --backend auto` → all .docx files processed, .pdf/.docm/.dotx skipped with warnings, summary report shows counts.

### Tests for User Story 3

- [x] T027 [P] [US3] Write integration test for .docx batch processing in `docmeld/tests/integration/test_bronze_batch.py` (folder with mixed .docx, unsupported formats)
- [x] T028 [P] [US3] Write integration test for format filtering (.docm/.dotx/.dot/.rtf skipped with warning) in `docmeld/tests/integration/test_bronze_batch.py`

### Implementation for User Story 3

- [x] T029 [US3] Update `BronzeProcessor.process_folder()` in `docmeld/docmeld/bronze/processor.py` to filter only .doc/.docx files, skip other Word formats (.docm/.dotx/.dot/.rtf) with warning
- [x] T030 [US3] Update `DocMeldParser.process_all()` and `process_bronze()` in `docmeld/docmeld/parser.py` to handle mixed .pdf/.docx folder batches correctly
- [x] T031 [US3] Run T027-T028 tests — verify all PASS

**Checkpoint**: Batch .docx processing works, format filtering, progress indicators.

---

## Phase 5: User Story 4 — Silver JSONL with Extended Renderer (Priority: P2)

**Goal**: Extend the silver stage markdown renderer to handle all 10 element types with proper markers (`[[ChartN]]`, `[[FormulaN]]`, `[Header]`, `[Footer]`, `[^N]` footnotes).

**Independent Test**: Run `docmeld silver <bronze_json>` on a bronze JSON containing chart/formula/header/footer/footnote elements → JSONL output with correct marker syntax.

### Tests for User Story 4

- [x] T032 [P] [US4] Write unit test for extended markdown renderer (chart, formula, header, footer, footnote, endnote markers) in `docmeld/tests/unit/test_markdown_renderer.py`
- [x] T033 [P] [US4] Write integration test for silver processing with extended element types in `docmeld/tests/integration/test_silver_pipeline.py` (verify marker syntax, global counters, title hierarchy)

### Implementation for User Story 4

- [x] T034 [US4] Add chart rendering case to `render_page()` in `docmeld/docmeld/silver/markdown_renderer.py` (handle chart type → `[[ChartN]]` marker + markdown table + `[/ChartN]]`)
- [x] T035 [US4] Add formula rendering case to `render_page()` in `docmeld/docmeld/silver/markdown_renderer.py` (handle formula type → `[[FormulaN]]` marker + LaTeX content + `[/FormulaN]]`)
- [x] T036 [US4] Add header/footer rendering cases to `render_page()` in `docmeld/docmeld/silver/markdown_renderer.py` (handle header/footer → `[Header]`/`[Footer]` markers with page_scope annotation)
- [x] T037 [US4] Add footnote/endnote rendering cases to `render_page()` in `docmeld/docmeld/silver/markdown_renderer.py` (handle footnote/endnote → `[^N]` markdown footnote syntax)
- [x] T038 [US4] Extend `render_page()` signature to accept and return `chart_counter` and `formula_counter` alongside existing `table_counter` in `docmeld/docmeld/silver/markdown_renderer.py`
- [x] T039 [US4] Update `SilverProcessor.process()` in `docmeld/docmeld/silver/processor.py` to initialize and pass chart/formula counters to `render_page()`
- [x] T040 [US4] Run T032-T033 tests — verify all PASS

**Checkpoint**: Silver JSONL renders all 10 element types with correct marker syntax and independent global counters.

---

## Phase 6: User Story 1 (Extended) — Rich Element Types from DOCX (Priority: P1)

**Goal**: Extend the docling backend to extract the full 10 element types from .docx files: charts (with data + image fallback), formulas (MathType/OMML → LaTeX), headers, footers, footnotes, endnotes.

**Independent Test**: Process `samples/sample_headers_footers.docx` → verify header/footer elements in JSON. Process a .docx with embedded charts/formulas → verify chart/formula elements.

### Tests for US1 Extended

- [x] T041 [P] [US1] Write unit test for docling chart extraction (chart detection + data extraction + image fallback) in `docmeld/tests/unit/test_docling_backend.py`
- [x] T042 [P] [US1] Write unit test for docling formula extraction (MathType/OMML → LaTeX mapping) in `docmeld/tests/unit/test_docling_backend.py`
- [x] T043 [P] [US1] Write unit test for docling header/footer/footnote extraction in `docmeld/tests/unit/test_docling_backend.py` using `samples/sample_headers_footers.docx`
- [x] T044 [P] [US1] Write integration test for .docx end-to-end with rich element types (bronze → silver) in `docmeld/tests/integration/test_end_to_end.py`

### Implementation for US1 Extended

- [x] T045 [US1] Add chart detection and extraction to `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (detect PictureClassificationItem, extract chart data → markdown table, capture image as base64 fallback)
- [x] T046 [US1] Add formula detection and extraction to `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (MathType OLE → LaTeX, OMML XML → LaTeX mapping)
- [x] T047 [US1] Add header/footer extraction to `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (parse docling document headers/footers section, detect page_scope)
- [x] T048 [US1] Add footnote/endnote extraction to `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (parse footnotes/endnotes parts from docling document tree)
- [x] T049 [US1] Run T041-T044 tests — verify all PASS

**Checkpoint**: Full 10-element type extraction from .docx files via docling backend.

---

## Phase 7: User Story 2 — Legacy DOC File via LibreOffice Bridge (Priority: P2)

**Goal**: Process legacy .doc files by converting to PDF via LibreOffice, then processing through existing PyMuPDF backend. Clean up intermediate PDF.

**Independent Test**: Place a .doc file, run `docmeld bronze <path.doc> --backend auto` → LibreOffice converts to PDF → PyMuPDF processes → bronze JSON produced → intermediate PDF deleted.

### Tests for User Story 2

- [x] T050 [P] [US2] Write unit test for SofficeBackend (LibreOffice detection, conversion command construction, cleanup) in `docmeld/tests/unit/test_soffice_backend.py`
- [x] T051 [P] [US2] Write integration test for .doc processing (LibreOffice available path) in `docmeld/tests/integration/test_bronze_pipeline.py`
- [x] T052 [P] [US2] Write unit test for LibreOffice not found error handling in `docmeld/tests/unit/test_soffice_backend.py` (mock `shutil.which("soffice")` returning None)

### Implementation for User Story 2

- [x] T053 [US2] Create `SofficeBackend` class in `docmeld/docmeld/bronze/backends/soffice_backend.py` implementing `ParserBackend` protocol
- [x] T054 [US2] Implement LibreOffice availability check in `SofficeBackend` via `shutil.which("soffice")` in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T055 [US2] Implement .doc → PDF conversion via `subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, doc_path])` in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T056 [US2] Implement intermediate PDF processing via existing PyMuPDF backend delegation in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T057 [US2] Implement intermediate PDF deletion after successful bronze JSON generation in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T058 [US2] Implement corrupted PDF retry logic (1 retry, then skip) in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T059 [US2] Update `element_extractor.extract_elements()` in `docmeld/docmeld/bronze/element_extractor.py` to dispatch `.doc` files to `SofficeBackend`
- [x] T060 [US2] Update `BronzeProcessor.process_file()` in `docmeld/docmeld/bronze/processor.py` to detect `.doc` extension and route to soffice backend
- [x] T061 [US2] Run T050-T052 tests — verify all PASS

**Checkpoint**: .doc files processed via LibreOffice bridge, intermediate PDF cleaned up, element output matches PDF pipeline format.

---

## Phase 8: CLI Extension — Backend Flag & Format Detection

**Purpose**: Extend CLI to accept .doc/.docx paths, add `--backend auto` option, and support format-based routing.

### Tests for CLI

- [x] T062 [P] Write CLI test for `--backend auto` format detection in `docmeld/tests/integration/test_cli.py` (.docx → docling, .doc → soffice)
- [x] T063 [P] Write CLI test for .doc/.docx path acceptance in `docmeld/tests/integration/test_cli.py` (bronze/process subcommands)

### Implementation for CLI

- [x] T064 Update `--backend` choices in `docmeld/docmeld/cli.py` from `["pymupdf", "docling"]` to `["pymupdf", "docling", "auto"]` (lines 22, 31, 50, 65, 75, 85)
- [x] T065 Implement `--backend auto` logic: detect `.doc` → soffice, `.docx` → docling, `.pdf` → pymupdf in `docmeld/docmeld/parser.py`
- [x] T066 Remove "PDF only" assumptions from CLI help text and descriptions in `docmeld/docmeld/cli.py`
- [x] T067 Run T062-T063 tests — verify all PASS

**Checkpoint**: CLI accepts .doc/.docx paths, `--backend auto` routes correctly, help text updated.

---

## Phase 9: User Story 5 — Gold Enrichment (Priority: P3)

**Goal**: Enrich silver JSONL with AI-generated descriptions and keywords via DeepSeek-chat. This stage is format-agnostic (works on any JSONL) and requires minimal code changes.

**Independent Test**: Run `docmeld gold <silver_jsonl>` on a .docx-derived JSONL → verify `description` and `keywords` fields in output.

### Tests for User Story 5

- [x] T068 [P] [US5] Write integration test for gold enrichment on .docx-derived JSONL in `docmeld/tests/integration/test_gold_pipeline.py` (verify description/keywords enrichment, idempotency)

### Implementation for User Story 5

- [x] T069 [US5] Verify gold stage works unchanged on .docx-derived JSONL — run existing gold integration tests against sample document output
- [x] T070 [US5] Run T068 test — verify PASS (gold enrichment preserves all element markers from extended silver renderer)

**Checkpoint**: Gold enrichment works on DOCX pipeline output. Existing PDF gold path unaffected.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, warnings, documentation, final validation.

- [x] T071 [P] Add tracked changes warning in `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (log warning if tracked changes detected in .docx)
- [x] T072 [P] Add OLE object warning in `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (log warning per edge case spec)
- [x] T073 [P] Add nested table depth warning in `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (log warning if nesting > 3 levels)
- [x] T074 [P] Add password-protection detection in `DoclingBackend` in `docmeld/docmeld/bronze/backends/docling_backend.py` (log error and skip)
- [x] T075 [P] Add large file warning (>100MB) in `BronzeProcessor` in `docmeld/docmeld/bronze/processor.py`
- [x] T076 [P] Update `README.md` with .doc/.docx support announcement and quickstart example in `README.md`
- [x] T077 [P] Update `docmeld/CONTRIBUTING.md` with doc/docx test instructions in `docmeld/CONTRIBUTING.md`
- [x] T078 [P] Amend constitution Principle IV from 4 to 10 supported element types in `.specify/memory/constitution.md` (per plan.md action item)
- [x] T079 [P] Copy `element-schema.json` contract to project: `cp specs/006-mvp-doc-pipeline/contracts/element-schema.json docmeld/tests/contracts/` (if tests/contracts/ directory pattern used)
- [x] T080 Run full test suite: `cd docmeld && source venv/bin/activate && pytest tests/ -v` — all existing + new tests pass
- [x] T081 Run lint + type check: `ruff check docmeld/ && black --check docmeld/ && mypy docmeld/`
- [x] T082 Run quickstart validation: execute all CLI examples from `specs/006-mvp-doc-pipeline/quickstart.md` against `samples/` directory
- [x] T083 Verify coverage >= 90%: `pytest tests/ -v --cov=docmeld --cov-report=term-missing`

**Checkpoint**: All edge cases handled, docs updated, full suite green, coverage >= 90%.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──→ Phase 2 (Foundational) ──→ Phase 3 (US1 Core) ──→ Phase 4 (US3 Batch)
                         │                           │
                         ├──→ Phase 5 (US4 Silver Renderer)          │
                         │         │                                  │
                         │         └──→ Phase 6 (US1 Extended) ──────┘
                         │                   │
                         └──→ Phase 7 (US2 .doc) ──→ Phase 8 (CLI)
                                                     │
                                                     └──→ Phase 9 (US5 Gold)
                                                               │
                                                               └──→ Phase 10 (Polish)
```

### User Story Dependencies

- **US1 Core (Phase 3)**: Depends on Phase 2 only
- **US3 Batch (Phase 4)**: Depends on US1 Core (needs processor generalization)
- **US4 Silver (Phase 5)**: Depends on Phase 2 only (needs element type models defined but not backend extraction — can render synthetic bronze JSON with all 10 types)
- **US1 Extended (Phase 6)**: Depends on US1 Core + Phase 5 (needs renderer counters to produce valid JSONL)
- **US2 .doc (Phase 7)**: Depends on US1 Core (needs processor generalization)
- **US5 Gold (Phase 9)**: Depends on US4 (needs silver JSONL output)
- **CLI (Phase 8)**: Depends on US1 Core + US2 (needs all backends available)

### Within Each Phase

- Tests MUST be written first and verified FAILING before implementation
- Models before services, services before integration
- Implementation complete before moving to next phase

### Parallel Opportunities

- Phase 1 (T002-T005): All 4 tasks parallelizable
- Phase 2 (T006-T007, T008-T013): All tests parallelizable, all 6 model additions parallelizable
- Phase 3 tests (T017-T019): All 3 parallelizable
- Phase 5 tests (T032-T033): Both parallelizable
- Phase 6 tests (T041-T044): All 4 parallelizable
- Phase 7 tests (T050-T052): All 3 parallelizable
- Phase 10 (T071-T079): All 9 parallelizable (different files)
- Phases 6 (US1 Extended) and 7 (US2 .doc) can run in parallel after Phase 4

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all tests together:
Task: "Write unit tests for 6 new element type Pydantic models in tests/unit/test_element_types.py"
Task: "Write contract test for 10-type element schema in tests/contract/test_element_schema.py"

# After tests fail, launch all 6 models in parallel:
Task: "Add ChartElement model to bronze/element_types.py"
Task: "Add FormulaElement model to bronze/element_types.py"
Task: "Add HeaderElement model to bronze/element_types.py"
Task: "Add FooterElement model to bronze/element_types.py"
Task: "Add FootnoteElement model to bronze/element_types.py"
Task: "Add EndnoteElement model to bronze/element_types.py"
```

---

## Implementation Strategy

### MVP First (US1 Core Only — Phase 1-3)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T016) — CRITICAL
3. Complete Phase 3: US1 Core .docx bronze (T017-T026)
4. **STOP and VALIDATE**: Process `samples/sample_multipage.docx` through bronze → verify 4 element types in JSON
5. Deploy as 0.2.0-alpha if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 Core → .docx bronze works (4 types) → **MVP!**
3. US3 Batch → folder processing works
4. US4 Silver → extended renderer with all 10 markers
5. US1 Extended → full 10-type .docx extraction
6. US2 .doc → legacy .doc support
7. CLI Extension → `--backend auto` routing
8. US5 Gold → AI enrichment
9. Polish → edge cases + docs + final validation

### Parallel Team Strategy

With multiple developers (after Phase 2 complete):
- **Dev A**: Phase 3 → Phase 6 (US1 Core + Extended)
- **Dev B**: Phase 7 (US2 .doc — parallel with Dev A once processor generalized)
- **Dev C**: Phase 5 (US4 Silver — parallel once Phase 6 element types available)

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [US*] label maps task to specific user story for traceability
- Each user story is independently completable and testable with samples from `samples/`
- TDD enforced: tests written first, verified RED, then implementation to GREEN
- Existing 144 tests serve as regression gate — must remain green at every checkpoint
- Constitution Principle IV must be amended from 4 to 10 element types (tracked in plan.md)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
