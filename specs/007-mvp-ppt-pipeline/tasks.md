# Tasks: MVP PowerPoint (PPT/PPTX) Data Pipeline

**Input**: Design documents from `specs/007-mvp-ppt-pipeline/`
**Prerequisites**: spec.md (user stories), plan.md (architecture, Phases A–E), research.md (decisions), data-model.md (entities), contracts/ (schema), quickstart.md (samples)

**Tests**: Required per constitution (TDD — tests written before implementation, 90%+ coverage target, 100% core parser). All existing tests must remain green.

**Organization**: Tasks grouped by user story, aligned with the 5 incremental phases (A–E) from plan.md. Each story is independently testable with sample files from `samples/`.

**Branch**: Developed on `main` per user directive.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths relative to repository root (`docmeld/` is the package dir)

---

## Phase 1: Setup & Versioning

**Purpose**: Prepare the project for PPT/PPTX pipeline development. Existing PDF and DOC pipelines must remain unaffected.

- [x] T001 Verify existing test suite passes (baseline): `cd docmeld && source venv/bin/activate && pytest tests/ -v`
- [x] T002 [P] Bump version from 0.2.0 to 0.3.0 in `docmeld/pyproject.toml`
- [x] T003 [P] Bump version from 0.2.0 to 0.3.0 in `docmeld/docmeld/__init__.py`
- [x] T004 Add `pptx = ["python-pptx>=0.6.23"]` and `office = ["docling>=2.0.0", "python-pptx>=0.6.23"]` optional-dependency extras in `docmeld/pyproject.toml` (same file as T002 — run after T002, not parallel)
- [x] T005 [P] Add CHANGELOG entry for 0.3.0 in `docmeld/CHANGELOG.md` (PPT/PPTX pipeline, +4 element types: smartart/notes/group/comment, python-pptx backend, slide pagination)
- [x] T006 [P] Verify 8 PPT/PPTX sample fixtures exist in `docmeld/samples/` (7 `.pptx` + `sample_ppt_legacy.ppt`); if missing, re-download from parser corpora
- [x] T007 [P] Install PPTX dev deps into venv: `cd docmeld && source venv/bin/activate && pip install -e ".[pptx,docling,dev]"`

**Checkpoint**: Version 0.3.0, extras declared, samples ready, existing tests green.

---

## Phase 2: Foundational — Element Type Extension & Schema

**Purpose**: Extend the element type system from 10 to 14 types (+smartart, notes, group, comment), add the `hidden` field, widen `element_id` capacity, and update the schema. Blocking prerequisite for all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Phase

- [x] T008 [P] Write unit tests for 4 new element type Pydantic models in `docmeld/tests/unit/test_element_types.py` (SmartArtElement, NotesElement, GroupElement, CommentElement — validation rules, defaults, type discrimination, `hidden` field default false)
- [x] T009 [P] Write contract test for 14-type element schema in `docmeld/tests/contract/test_element_schema.py` (validate PPT sample JSON against `element-schema.json`; test backward compatibility with 4-type and 10-type documents; test `element_id` `^e_\d{4}$` pattern)

### Implementation for Foundational Phase

- [x] T010 [P] Add SmartArtElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, smartart_type, content, image, image_name, page_no, element_id, parent_id, hidden)
- [x] T011 Add NotesElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, page_no, element_id, parent_id, hidden) — same file as T010, apply sequentially
- [x] T012 Add GroupElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, child_count, page_no, element_id, parent_id, hidden) — same file as T010, apply sequentially
- [x] T013 Add CommentElement model to `docmeld/docmeld/bronze/element_types.py` (fields: type, content, author, page_no, element_id, parent_id, hidden) — same file as T010, apply sequentially
- [x] T014 Add optional `hidden: bool = False` field to all existing element models in `docmeld/docmeld/bronze/element_types.py`
- [x] T015 Expand `BronzeElement` union type in `docmeld/docmeld/bronze/element_types.py` to include all 14 element types
- [x] T016 Update `parse_element()` dispatch in `docmeld/docmeld/bronze/element_types.py` to handle smartart, notes, group, comment
- [x] T017 Widen `element_id` assignment from `f"e_{i+1:03d}"` to `f"e_{i+1:04d}"` in `docmeld/docmeld/bronze/element_extractor.py` (supports up to 9,999 elements)
- [x] T018 Update `element_id` regex in `specs/007-mvp-ppt-pipeline/contracts/element-schema.json` and `docmeld/docmeld/bronze/element_types.py` validators to `^e_\d{4}$`
- [x] T019 Run T008 and T009 tests — verify they PASS with the new models

**Checkpoint**: 14 element types, `hidden` field, wider element_id, contract validated, backward compatible.

---

## Phase 3: User Story 1 (Core) — Process Single PPTX to Bronze, 4 Core Types (Priority: P1) 🎯 MVP

**Goal**: Accept a `.pptx` path and extract the 4 core element types (text, table, title, image) via python-pptx, with slide-number pagination. (Plan Phase A.)

**Independent Test**: Run bronze on `sample_pptx_basic.pptx` → verify sanitized hashed filename/folder, JSON with text/title elements per slide, `page_no` = slide number starting at 1.

### Tests for User Story 1 (Core)

- [x] T020 [P] [US1] Write unit test for PptxBackend core extraction in `docmeld/tests/unit/test_pptx_backend.py` (given `sample_pptx_basic.pptx` → expect text + title elements with correct page_no; given `sample_pptx_image.pptx` → expect image elements with base64)
- [x] T021 [P] [US1] Write integration test for pptx→bronze in `docmeld/tests/integration/test_bronze_pipeline.py` (`.pptx` path → hashed folder + JSON; idempotent re-run skips)
- [x] T022 [P] [US1] Write unit test for `.pptx` extension handling in `docmeld/tests/unit/test_filename_sanitizer.py`

### Implementation for User Story 1 (Core)

- [x] T023 [US1] Create `PptxBackend` implementing the `ParserBackend` protocol in `docmeld/docmeld/bronze/backends/pptx_backend.py` (open with python-pptx, iterate slides → shapes)
- [x] T024 [US1] Implement core shape mapping in `docmeld/docmeld/bronze/backends/pptx_backend.py`: title placeholder→title, body/text frames→text, table shapes→table (markdown), pictures→image (base64 + bbox)
- [x] T025 [US1] Implement slide pagination (`page_no` = 1-indexed slide number) and per-slide `element_id` assignment in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T026 [US1] Register `pptx` backend and `.pptx` extension dispatch in `docmeld/docmeld/bronze/element_extractor.py` and `docmeld/docmeld/bronze/processor.py`
- [x] T027 [US1] Extend `--backend` choices with `pptx` and accept `.pptx` paths in `docmeld/docmeld/cli.py` and `docmeld/docmeld/parser.py`
- [x] T028 [US1] Run T020–T022 — verify PASS

**Checkpoint**: `.pptx` → bronze JSON with 4 core element types. Silver/gold work unchanged. MVP demonstrable.

---

## Phase 4: User Story 1 (Rich) — Presentation-Rich Element Types (Priority: P1)

**Goal**: Add chart (docling assist), formula, smartart, notes, group, footer, comment, inline hyperlinks; hybrid geometric+z-order sort (FR-018); hidden-slide flagging. (Plan Phase B.)

**Independent Test**: Run bronze on `sample_pptx_chart_bar.pptx`, `sample_pptx_comments.pptx`, `sample_pptx_shapes.pptx` → verify chart data-table+image, comment with author, group + child elements; ordering + hidden flags correct.

### Tests for User Story 1 (Rich)

- [x] T029 [P] [US1] Write unit tests for rich extraction in `docmeld/tests/unit/test_pptx_backend.py` (chart→chart_type+data/image on `sample_pptx_chart_bar.pptx`; comment→author on `sample_pptx_comments.pptx`; group+children on `sample_pptx_shapes.pptx`; notes via injected notes_slide; hyperlink inline `[text](url)`)
- [x] T030 [P] [US1] Write unit test for hybrid geometric+z-order sort and >20-element debug log in `docmeld/tests/unit/test_pptx_backend.py` (`sample_pptx_issue.pptx`)
- [x] T031 [P] [US1] Write unit tests for new silver markers in `docmeld/tests/unit/test_markdown_renderer.py` (`[[SmartArtN]]`, `[Notes]`, `[Comment: author]`, `[[ChartN]]`, `[[FormulaN]]`, `[Footer]`; global counters)

### Implementation for User Story 1 (Rich)

- [x] T032 [US1] Implement speaker notes extraction (`slide.notes_slide`) → notes element (emitted after slide content) in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T033 [US1] Implement comment extraction with author from OOXML comment parts in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T034 [US1] Implement group-shape flattening (group element + child elements via `parent_id`) in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T035 [US1] Implement inline hyperlink preservation `[text](url)` within text/shape content in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T036 [US1] Implement chart extraction (python-pptx `chart.plots` → markdown table; base64 image fallback) with docling assist path in `docmeld/docmeld/bronze/backends/pptx_backend.py` and `docmeld/docmeld/bronze/backends/docling_backend.py`
- [x] T037 [US1] Implement SmartArt text extraction from diagram data part (`<a:t>` nodes → hierarchical markdown; image fallback) in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T038 [US1] Implement formula extraction (OMML/Equation objects → LaTeX) in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T039 [US1] Implement footer/placeholder extraction → footer element in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T040 [US1] Implement hybrid geometric (top-to-bottom, left-to-right by bbox) + z-order tie-breaker sort with >20-element debug log in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T041 [US1] Implement hidden-slide detection → set `hidden: true` on elements, continuous numbering in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T042 [US1] Extend `render_page()` with smartart/notes/comment/chart/formula/footer branches + global counters in `docmeld/docmeld/silver/markdown_renderer.py`
- [x] T043 [US1] Support PPTX section→H1 / slide-title→H2 hierarchy in `docmeld/docmeld/silver/title_tracker.py`
- [x] T044 [US1] Run T029–T031 — verify PASS

**Checkpoint**: Full presentation element set in bronze; silver renderer handles all markers. User Story 1 complete.

---

## Phase 5: User Story 2 — Process Single Legacy PPT to Bronze (Priority: P2)

**Goal**: Detect `.ppt`, convert via LibreOffice soffice bridge → PDF → PyMuPDF, delete intermediate PDF, guard on missing LibreOffice. (Plan Phase C.)

**Independent Test**: Run bronze on `sample_ppt_legacy.ppt` → verify soffice conversion, 4-type JSON, intermediate PDF removed; without soffice → clear error + skip.

### Tests for User Story 2

- [x] T045 [P] [US2] Write unit test for `.ppt` acceptance + missing-soffice error in `docmeld/tests/unit/test_soffice_backend.py`
- [x] T046 [P] [US2] Write integration test for `.ppt`→bronze end-to-end in `docmeld/tests/integration/test_bronze_pipeline.py` (`sample_ppt_legacy.ppt`; assert intermediate PDF deleted)

### Implementation for User Story 2

- [x] T047 [US2] Widen the `.doc`-only suffix guard to accept `{".doc", ".ppt"}` and generalize docstring/param naming in `docmeld/docmeld/bronze/backends/soffice_backend.py`
- [x] T048 [US2] Route `.ppt` to SofficeBackend in `docmeld/docmeld/bronze/processor.py` and `docmeld/docmeld/bronze/element_extractor.py`
- [x] T049 [US2] Accept `.ppt` paths and `--backend auto` extension detection in `docmeld/docmeld/cli.py` and `docmeld/docmeld/parser.py`
- [x] T050 [US2] Run T045–T046 — verify PASS

**Checkpoint**: `.ppt` processed via LibreOffice → PDF → PyMuPDF with 4 element types; graceful error when soffice absent.

---

## Phase 6: User Story 3 — Process Folder of Presentations in Batch (Priority: P1)

**Goal**: Batch-process a folder of mixed `.ppt`/`.pptx`, routing each to the correct backend; skip unsupported formats with warnings; continue on per-file failure. (Extends Plan Phase A dispatch.)

**Independent Test**: Point bronze at a folder containing `.pptx`, `.ppt`, and a `.pptm`/`.pdf` → verify pptx via pptx backend, ppt via soffice, others skipped with warnings, summary report produced.

### Tests for User Story 3

- [x] T051 [P] [US3] Write integration test for mixed-folder batch in `docmeld/tests/integration/test_bronze_pipeline.py` (folder with .pptx + .ppt + unsupported → correct routing, skips logged, all processed)
- [x] T052 [P] [US3] Write integration test for batch resilience + summary report in `docmeld/tests/integration/test_bronze_pipeline.py` (one corrupt file → others still processed, failure in summary)

### Implementation for User Story 3

- [x] T053 [US3] Implement folder iteration with per-file backend routing (`.pptx`→pptx, `.ppt`→soffice) in `docmeld/docmeld/bronze/processor.py`
- [x] T054 [US3] Implement unsupported-format skip-with-warning (`.pptm`, `.potx`, `.pot`, `.ppsx`, `.odp`) in `docmeld/docmeld/bronze/processor.py`
- [x] T055 [US3] Ensure progress indicators + summary report cover PPT/PPTX batch in `docmeld/docmeld/bronze/processor.py` and `docmeld/docmeld/utils/progress.py`
- [x] T056 [US3] Run T051–T052 — verify PASS

**Checkpoint**: Mixed-format folders process end-to-end with correct routing and resilient batch behavior.

---

## Phase 7: User Story 4 — Convert Bronze JSON to Silver JSONL (Priority: P2)

**Goal**: Produce one JSONL line per slide with `page_no: "page1"` convention, complete title context, and all element markers rendered. (Plan Phase D.)

**Independent Test**: Run silver on a rich bronze JSON (10 slides incl. chart/smartart/notes) → verify exactly 10 lines, correct markers, `metadata.page_no` = "pageN".

### Tests for User Story 4

- [x] T057 [P] [US4] Write integration test for pptx bronze→silver in `docmeld/tests/integration/test_silver_pipeline.py` (one line per slide; `page_no` "pageN"; smartart/notes/comment/chart markers present; hidden slides retained; silver skip-reprocessing when JSONL already exists — FR-030)
- [x] T058 [P] [US4] Write cross-pipeline parity test in `docmeld/tests/integration/test_silver_pipeline.py` (PPT silver JSONL schema matches PDF/DOC JSONL contract — SC-016)

### Implementation for User Story 4

- [x] T059 [US4] Ensure silver source filename reflects `.ppt`/`.pptx` origin and slide grouping in `docmeld/docmeld/silver/processor.py`
- [x] T060 [US4] Verify per-slide aggregation by `page_no` in `docmeld/docmeld/silver/page_aggregator.py` (no code change expected; add guard/test if gaps found)
- [x] T061 [US4] Run T057–T058 — verify PASS

**Checkpoint**: PPT silver JSONL is interchangeable with PDF/DOC JSONL; one line per slide.

---

## Phase 8: User Story 5 — Enrich Silver JSONL with Gold Metadata (Priority: P3)

**Goal**: Reuse the existing gold stage to add `description` + `keywords` per slide via DeepSeek. (Plan Phase D.)

**Independent Test**: Run gold on a pptx silver JSONL → each slide gains `description` + `keywords`; re-run skips; a chart slide yields relevant keywords.

### Tests for User Story 5

- [x] T062 [P] [US5] Write integration test for pptx silver→gold in `docmeld/tests/integration/test_gold_pipeline.py` (description + keywords added per slide; idempotent re-run; failed-slide flag `gold_processing_failed`)

### Implementation for User Story 5

- [x] T063 [US5] Verify gold stage consumes pptx silver JSONL unchanged in `docmeld/docmeld/gold/processor.py` (no code change expected; confirm via test)
- [x] T064 [US5] Run T062 — verify PASS; add end-to-end pptx traversal to `docmeld/tests/integration/test_end_to_end.py`

**Checkpoint**: Full bronze→silver→gold pipeline works for `.pptx`.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, warnings, quality gates, docs. (Plan Phase E.)

- [x] T065 [P] Implement OLE-object and animation/video/audio exclusion warnings in `docmeld/docmeld/bronze/backends/pptx_backend.py`
- [x] T066 Implement password-protected `.pptx` detection → error + skip in `docmeld/docmeld/bronze/backends/pptx_backend.py` — same file as T065, apply sequentially
- [x] T067 Implement nested SmartArt/group depth-limit warning (>5 levels) and broken-hyperlink plain-text fallback in `docmeld/docmeld/bronze/backends/pptx_backend.py` — same file as T065, apply sequentially
- [x] T068 [P] Add `--backend auto/pptx/pymupdf` CLI tests in `docmeld/tests/integration/test_cli.py`
- [x] T069 [P] Update `docmeld/README.md` with `.ppt`/`.pptx` support announcement and `pip install docmeld[pptx]`
- [x] T070 Amend constitution Principle IV to register `smartart`, `notes`, `group`, `comment` element types in `.specify/memory/constitution.md` (MINOR, additive; bump constitution version)
- [x] T071 Run full quality gate: `cd docmeld && source venv/bin/activate && pytest tests/ -v --cov=docmeld --cov-report=term-missing && ruff check docmeld/ && black --check docmeld/ && mypy docmeld/`
- [x] T072 Run `specs/007-mvp-ppt-pipeline/quickstart.md` validation against `samples/` presentations end-to-end

**Checkpoint**: All edge cases covered, quality gates green, docs and constitution updated.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 Core (Phase 3)**: Depends on Foundational — MVP
- **US1 Rich (Phase 4)**: Depends on Phase 3
- **US2 Legacy PPT (Phase 5)**: Depends on Foundational; parallelizable with Phase 4
- **US3 Batch (Phase 6)**: Depends on Phase 3 (core dispatch) and Phase 5 (soffice routing)
- **US4 Silver (Phase 7)**: Depends on Phase 4 (rich element types to render)
- **US5 Gold (Phase 8)**: Depends on Phase 7
- **Polish (Phase 9)**: Depends on all desired stories complete

### Story Dependency Graph

```text
Setup → Foundational ─┬─→ US1 Core (P3) ─→ US1 Rich (P4) ─→ US4 Silver (P7) ─→ US5 Gold (P8) ─→ Polish (P9)
                      │                          │                                 ▲
                      └─→ US2 Legacy PPT (P5) ────┴─→ US3 Batch (P6) ───────────────┘
```

### Parallel Opportunities

- All Setup tasks marked [P] (T002, T003, T005–T007) run in parallel
- Foundational: tests T008/T009 run in parallel (different files); the 4 model additions T010–T013 share `element_types.py` and are applied sequentially
- After Phase 3: US1 Rich (Phase 4) and US2 Legacy PPT (Phase 5) can proceed in parallel (different files: pptx_backend vs soffice_backend)
- All test-writing tasks within a story marked [P] run in parallel before implementation

---

## Parallel Example: Foundational Phase

```bash
# Write foundational tests together (different files → parallel):
Task: "Unit tests for 4 new element models in docmeld/tests/unit/test_element_types.py"
Task: "Contract test for 14-type schema in docmeld/tests/contract/test_element_schema.py"

# Then add the 4 models to element_types.py sequentially (same file — no [P]):
#   T010 SmartArtElement → T011 NotesElement → T012 GroupElement → T013 CommentElement
```

---

## Implementation Strategy

### MVP First (User Story 1 Core)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 Core (.pptx → bronze, 4 types)
4. **STOP and VALIDATE**: `.pptx` → bronze JSON works; existing tests green
5. Demo the MVP

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 Core → 4-type .pptx bronze (MVP!)
3. US1 Rich → full element set (charts, smartart, notes, comments, groups, hyperlinks)
4. US2 Legacy PPT → .ppt via soffice (parallel with US1 Rich)
5. US3 Batch → mixed-folder processing
6. US4 Silver → per-slide JSONL
7. US5 Gold → AI enrichment
8. Polish → edge cases + quality gates

### Risk-First Note

Per plan Risk Assessment, spike **T037 (SmartArt text extraction)** early in Phase 4 — python-pptx has no first-class SmartArt API; validate the diagram-data XML approach before committing to the full rich element set.

---

## Requirements Coverage Traceability

Maps every spec requirement group to the task(s) that satisfy it. Use before merge to confirm nothing is orphaned.

| Requirement (spec) | Tasks |
|--------------------|-------|
| FR-001 input path/folder; unsupported-format skip | T026, T053, T054 |
| FR-002/003/004 sanitize, MD5 hash, output folder | T022 (reuse existing sanitizer, verify `.ppt`/`.pptx`) |
| FR-005 extract .pptx elements → JSON | T023, T024, T026 |
| FR-006 14 element types supported | T010–T016 |
| FR-007 type + page_no per element | T025 |
| FR-008 title level/content | T024 |
| FR-009 text content; FR-009a inline hyperlinks | T024, T035 |
| FR-010 table markdown + summary | T024, T036 (docling assist) |
| FR-011 image base64 + bbox | T024 |
| FR-012 chart data-table + image fallback | T036 |
| FR-013 formula LaTeX | T038 |
| FR-014 SmartArt hierarchical text | T037 |
| FR-015 notes content per slide | T032 |
| FR-016 group + child parent_id | T034 |
| FR-017 footer; FR-017a comment + author | T039, T033 |
| FR-018 hybrid geometric+z-order; notes last | T040 |
| FR-019 bronze skip-reprocessing | T021 |
| FR-020/021/022 legacy .ppt soffice bridge | T047, T048, T049 |
| FR-023–028 silver JSONL, per-slide, markers, page_no | T042, T059, T057 |
| FR-027 section→H1 / title→H2 hierarchy | T043 |
| FR-029 independent global counters | T042 |
| FR-030 silver skip-reprocessing | T057 |
| FR-031–037 gold enrichment (reused) | T063, T062 |
| FR-038–042 progress, logging, summary, idempotency, fail-open batch | T055, T052 |
| FR-043 `--backend pptx/pymupdf/auto` | T027, T049, T068 |
| Edge: hidden slides | T041, T057 |
| Edge: OLE/animation/video/audio exclusion | T065 |
| Edge: password-protected | T066 |
| Edge: nested SmartArt/group depth; broken hyperlink | T067 |
| Edge: corrupted file resilience | T052 |
| SC-016 cross-pipeline JSONL parity | T058 |
| Constitution Principle IV amendment | T070 |

**Orphan check**: All 45 FRs, 16 edge cases, and SC-016 map to at least one task. No orphaned requirements.

---

## Notes

- [P] tasks = independent work with no ordering dependency. For **production-code** tasks this also means different files (same-file impl tasks are marked sequential, e.g. T011–T013, T066–T067). For **test-writing** tasks, [P] on the same test module is allowed because they add independent test functions that merge cleanly.
- [Story] label maps task to user story for traceability
- Tests are written FIRST and MUST fail before implementation (constitution TDD)
- Existing PDF/DOC pipelines must stay green throughout (T001 baseline, T071 gate)
- Commit after each task or logical group
- `page_no` uses `"page1"` literal in silver for cross-pipeline parity (slide semantics via source type)
- Hidden slides carry `hidden: true` through all stages
