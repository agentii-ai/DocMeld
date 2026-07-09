# Implementation Plan: MVP Word Document (DOC/DOCX) Data Pipeline

**Branch**: `006-mvp-doc-pipeline` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/006-mvp-doc-pipeline/spec.md`

## Summary

Extend the existing DocMeld three-stage pipeline (Bronze → Silver → Gold) to process Word documents (.doc and .docx) alongside PDFs. DOCX files are parsed via the IBM docling library, which natively reads OOXML to extract structured elements including text, tables, images, charts, MathType/OMML formulas, headers, footers, footnotes, and endnotes. Legacy .doc files are converted to PDF via LibreOffice and then processed through the existing PyMuPDF backend. The silver and gold stages are extended to render 10 element types (up from 4) with new marker syntax for charts (`[[ChartN]]`), formulas (`[[FormulaN]]`), headers/footers, and markdown footnotes. The existing `ParserBackend` protocol and `BronzeProcessor` are generalized from PDF-only to multi-format, while preserving backward compatibility and the existing PyPI package.

## Technical Context

**Language/Version**: Python 3.9+ (minimum supported per constitution)
**Primary Dependencies**: PyMuPDF (fitz), pymupdf4llm, pandas, openpyxl, pydantic, python-dotenv, langchain-deepseek (existing); docling >= 2.0.0 (existing optional dep); LibreOffice/soffice (external, required only for .doc)
**Storage**: Local filesystem (JSON, JSONL, log files) — no database
**Testing**: pytest with pytest-cov (90%+ coverage target, 100% for core parser); 144 existing tests must remain green
**Target Platform**: macOS, Linux, Windows (cross-platform; .doc support requires LibreOffice installation)
**Project Type**: Single library project with CLI interface (published on PyPI as `docmeld`)
**Performance Goals**: <5 min for 10-50 page .docx through all stages; <8 min for .doc (including LibreOffice conversion); <500MB memory for 100-page documents
**Constraints**: No OCR/VLM for core processing; offline-capable for bronze/silver; API-dependent for gold; existing PDF pipeline must be unaffected
**Scale/Scope**: MVP handles digital-native .docx and legacy .doc; batch processing of 100+ mixed-format files; 95% success rate target for .docx, 85% for .doc
**Current Version**: 0.1.0 on PyPI; this feature targets 0.2.0

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Test-First Development (NON-NEGOTIABLE)
- ✅ **PASS**: Tests written before any new implementation code
- ✅ **PASS**: Existing 144 tests must pass before starting new work
- ✅ **PASS**: Integration tests required for docx→bronze→silver→gold end-to-end
- ✅ **PASS**: Unit tests for each new element type, backend, and renderer extension

### Principle II: Library-First, PyPI-Ready
- ✅ **PASS**: `DocMeldParser` already importable; will accept .doc/.docx paths
- ✅ **PASS**: CLI built on top of library API; --backend flag extended with new choices
- ✅ **PASS**: Type hints and docstrings for all new public API
- ✅ **PASS**: Bump to 0.2.0 (MINOR version) — new element types are additive, no breaking changes to existing contract
- ⚠️ **ACTION REQUIRED**: Element type set expands from 4 to 10 — constitution Principle IV must be amended to reflect new supported types

### Principle III: Lightweight by Default
- ✅ **PASS**: docling is already an optional dependency (`pip install docmeld[docling]`)
- ✅ **PASS**: LibreOffice is external, not a Python dependency — guarded with availability check
- ✅ **PASS**: Core base install remains unchanged (PyMuPDF only)
- ✅ **PASS**: Memory constraint: <500MB for 100-page documents

### Principle IV: Unified Element Format
- ✅ **PASS**: New element types (chart, formula, header, footer, footnote, endnote) extend existing JSON structure
- ✅ **PASS**: All elements include `type` and `page_no` fields
- ✅ **PASS**: Element order preserves document reading order
- ⚠️ **CONSTITUTION UPDATE**: Principle IV lists 4 supported types; must be amended to include all 10 types

### Principle V: Agent-Ready Outputs
- ✅ **PASS**: Extended output formats with chart data, formula LaTeX, header/footer markers
- ✅ **PASS**: Source attribution preserved (page numbers, source filename)
- ✅ **PASS**: Same JSONL contract as PDF pipeline (backward compatible)

### Principle VI: Production-Grade Quality
- ✅ **PASS**: Ruff, black, mypy for all new code
- ✅ **PASS**: Explicit error handling for corrupted .docx, missing LibreOffice, password-protected files
- ✅ **PASS**: Graceful handling with warnings for tracked changes, OLE objects, unsupported formats

### Principle VII: Open-Source Excellence
- ✅ **PASS**: MIT license unchanged
- ✅ **PASS**: CHANGELOG entry for 0.2.0 with all changes
- ✅ **PASS**: README update with .doc/.docx support announcement

**Gate Status**: ✅ **PASSED** (2 action items: update constitution Principle IV element types; ensure backward compatibility of existing JSON contract)

## Project Structure

### Documentation (this feature)

```text
specs/006-mvp-doc-pipeline/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── element-schema.json
└── checklists/
    └── requirements.md
```

### Source Code (changes from existing repository root)

```text
docmeld/                          # Repository root
├── samples/                      # [UPDATED] Test fixtures for DOCX pipeline
│   ├── sample_tables.docx        #   Tables (multi-row + single-row)
│   ├── sample_lists.docx         #   Bullet/numbered/nested lists
│   ├── sample_headers_footers.docx # Headers + footers across 3 pages
│   ├── sample_images.docx        #   Embedded PNG images
│   ├── sample_multipage.docx     #   Title hierarchy across 3 pages
│   └── sample3.docx              #   Real-world Chinese document (existing)
│
├── docmeld/
├── __init__.py                          # [UPDATE] Version bump to 0.2.0
├── parser.py                            # Generalize PDF → document (accept .doc/.docx paths)
├── cli.py                               # Extend --backend choices, accept .doc/.docx paths
│
├── bronze/
│   ├── __init__.py
│   ├── processor.py                     # Generalize from PDF-only to multi-format
│   ├── filename_sanitizer.py            # Already works for any extension (reuse)
│   ├── element_extractor.py             # Extend dispatch for new backends
│   ├── element_types.py                 # Add ChartElement, FormulaElement, HeaderElement, FooterElement, FootnoteElement, EndnoteElement
│   └── backends/
│       ├── __init__.py                  # ParserBackend protocol (reuse; already generic)
│       ├── pymupdf_backend.py           # [REUSE] Existing — unchanged
│       ├── docling_backend.py           # [REWRITE] Adapt for .docx; add chart/formula/header/footer/footnote extraction
│       └── soffice_backend.py           # [NEW] LibreOffice → PDF → PyMuPDF for .doc files
│
├── silver/
│   ├── __init__.py
│   ├── processor.py                     # Extend source filename to reflect .doc/.docx origin
│   ├── markdown_renderer.py             # Add chart, formula, header, footer, footnote, endnote rendering
│   ├── title_tracker.py                 # [REUSE] Existing — unchanged
│   ├── page_aggregator.py              # [REUSE] Existing — unchanged
│   └── page_models.py                   # [REUSE] Existing models — no changes needed
│
├── gold/
│   ├── __init__.py
│   ├── processor.py                     # [REUSE] Existing — unchanged (works on any JSONL)
│   ├── deepseek_client.py              # [REUSE] Existing — unchanged
│   └── metadata_extractor.py           # [REUSE] Existing — unchanged
│
└── utils/
    ├── __init__.py
    ├── logging.py                       # [REUSE] Existing — unchanged
    ├── env_loader.py                    # [REUSE] Existing — unchanged
    └── progress.py                      # [REUSE] Existing — unchanged

docmeld/tests/
├── unit/
│   ├── test_docling_backend.py          # [UPDATE] Add .docx-specific element type tests
│   ├── test_soffice_backend.py          # [NEW] .doc conversion + PyMuPDF processing
│   ├── test_element_types.py           # [UPDATE] Add chart/formula/etc model validation
│   ├── test_markdown_renderer.py        # [UPDATE] Add new element marker tests
│   ├── test_filename_sanitizer.py       # [UPDATE] Verify doc/docx extension handling
│   └── ... (existing tests unchanged)
├── integration/
│   ├── test_bronze_pipeline.py          # [UPDATE] Add .docx/.doc path testing
│   ├── test_silver_pipeline.py          # [UPDATE] Add new element type rendering tests
│   ├── test_gold_pipeline.py            # [REUSE] Existing — works on any JSONL
│   ├── test_end_to_end.py              # [UPDATE] Add .docx e2e traversal
│   └── test_cli.py                      # [UPDATE] Add --backend auto/docling/soffice tests
└── contract/
    └── test_element_schema.py           # [UPDATE] Validate 10 element types against schema
```

**Structure Decision**: Single library project — follows existing `docmeld/docmeld/` and `docmeld/tests/` layout. No new modules outside existing hierarchy. The `soffice_backend.py` goes alongside existing backends. Element type models extend `bronze/element_types.py`. Silver renderer adds case branches for new types. CLI adds `--backend auto` and accepts non-.pdf paths.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV amendment: 4 → 10 element types | .docx provides richer structure (charts, formulas, headers, etc.) that PDF format flattens; extracting these is the primary value proposition of a native DOCX pipeline | Rejected: limiting docx output to 4 PDF types would discard the key advantage of direct OOXML parsing |

---

## Phase 0: Research & Decisions

### R1: Docling for .docx — Element Type Coverage

**Decision**: Use docling v2.111+ as the primary .docx backend.

**Rationale**: Docling is already an optional dependency for PDF parsing. IBM's `docling` provides:
- Native OOXML reading (no PDF conversion needed for .docx)
- `DocTags` and structured item iteration similar to existing PDF code
- Chart detection and data extraction (via `PictureClassificationItem` and chart data APIs)
- MathType/OMML → LaTeX formula extraction
- Header/footer/footnote/endnote awareness in the document tree
- 62.9k stars, IBM-backed, LF AI & Data project, 193+ releases

**Alternatives considered**:
- `python-docx`: .docx only, no page numbers, no chart/formula extraction — insufficient for pipeline needs
- `mammoth`: Markdown-only output, loses structured element types — defeats purpose of element pipeline
- `markitdown`: Too early/simplistic, no page numbers or structured elements
- `unstructured`: Heavy dependency footprint, no page structure, .doc support needs system tools

### R2: Legacy .doc Support — The LibreOffice Bridge

**Decision**: Use LibreOffice (`soffice --headless --convert-to pdf`) as the .doc bridge, reusing existing PyMuPDF backend.

**Rationale**: No open-source Python library directly parses the OLE binary .doc format with structured element extraction. LibreOffice provides the most reliable cross-platform conversion path. The resulting PDF is processed through the existing, well-tested PyMuPDF backend. Element type richness is limited to what PDF extraction provides (4 types), but .doc is the minority format.

**Alternatives considered**:
- `olefile`: OLE container reader only — would require implementing an entire .doc binary parser from scratch (impractical for MVP)
- `antiword` / `catdoc`: Text-only extraction, no tables/images/structure
- `spire.doc`: Full .doc support but commercial ($999+/year) — violates open-source constitution
- `win32com`: Windows-only — violates cross-platform requirement

### R3: Element Type Extension Strategy

**Decision**: Extend `element_types.py` with 6 new Pydantic models, keeping existing 4 types unchanged.

**Rationale**: The constitution Principle IV requires backward compatibility. Existing PDF pipeline consumers depend on the 4-type contract. New types are additive (MINOR version bump per semver). The `BronzeElement` union type grows from `TitleElement | TextElement | TableElement | ImageElement` to include all 10 types.

**Key design choices**:
- `ChartElement`: Has `content` (markdown table of chart data), `chart_type` (bar/line/pie/etc.), `image` (base64 fallback), standard `page_no`
- `FormulaElement`: Has `content` (LaTeX string), `formula_type` (MathType/OMML/LaTeX), standard `page_no`
- `HeaderElement` / `FooterElement`: Has `content`, `page_scope` (all/even/odd), standard `page_no`
- `FootnoteElement` / `EndnoteElement`: Has `content`, `reference_id`, standard `page_no`

### R4: Silver Renderer Extension

**Decision**: Extend `render_page()` with case branches for each new element type, following existing pattern.

**Rationale**: The existing renderer handles 3 element types (title, text, table) plus images. Each new type gets a dedicated rendering branch with consistent marker syntax:

| Element Type | Marker Syntax | Content |
|-------------|---------------|---------|
| table | `[[TableN]]` ... `[/TableN]` | Markdown table (existing) |
| chart | `[[ChartN]]` ... `[/ChartN]` | Markdown table of chart data |
| formula | `[[FormulaN]]` ... `[/FormulaN]` | LaTeX content |
| header | `[Header]` content `[/Header]` | Header text + scope annotation |
| footer | `[Footer]` content `[/Footer]` | Footer text |
| footnote | `[^N]` | Footnote content (markdown footnote syntax) |
| endnote | `[^N]` | Endnote content (markdown footnote syntax) |

Global counters for charts and formulas mirror the existing table counter pattern. Header/footer do not need global numbering.

### R5: CLI Extension

**Decision**: Extend `--backend` choices to `pymupdf`, `docling`, `auto`. Add file extension detection. Accept `.doc`/`.docx` paths alongside `.pdf`.

**Rationale**: The existing CLI framework maps well. `--backend auto` detects format by extension and routes accordingly. The `path` argument drops its "PDF-only" assumption. All subcommands (`bronze`, `process`, etc.) benefit automatically.

### R6: Package Versioning

**Decision**: Bump from 0.1.0 to 0.2.0 (MINOR version).

**Rationale**: New element types are additive, existing PDF output is unchanged. Per semver, backward-compatible additions increment MINOR. The `docmeld[docling]` extra dependency already exists.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions, field specifications, validation rules, and state transitions. Key additions:

1. **6 new Pydantic models**: ChartElement, FormulaElement, HeaderElement, FooterElement, FootnoteElement, EndnoteElement
2. **Expanded BronzeElement union**: Now covers all 10 element types
3. **New result models**: SofficeConversionResult (intermediate PDF tracking)
4. **Unchanged entities**: SilverPage, GoldPage, ProcessingResult — same contract as PDF pipeline

### Interface Contracts

See [contracts/element-schema.json](./contracts/element-schema.json) for the JSON Schema validation contract covering all 10 element types. The contract guarantees:
- Every element has `type` (string enum of 10 values) and `page_no` (integer >= 1)
- Each type has required type-specific fields
- Backward compatibility: existing 4-type outputs still validate against this schema
- Unknown types are rejected at contract validation

### Quickstart

See [quickstart.md](./quickstart.md) for developer onboarding with .docx and .doc examples.

---

## Sample-Driven Testing Strategy

The `samples/` directory contains test fixtures covering each element type and edge case. Each sample maps to specific functional requirements and is used in TDD workflow.

### Sample Inventory

> **Note on WIPO samples**: The WIPO PCT DocConverter page (https://pct.wipo.int/DocConverter/pages/sampleFiles.xhtml) provides ~30 curated .docx test documents covering math equations, chemical formulas, tables, charts, track changes, OLE objects, nested tables, and multi-language content. These use PrimeFaces JSF session-gated downloads and cannot be fetched programmatically. The generated samples below replicate the key WIPO categories. See the WIPO Edge Case Mapping table below for the full category → spec mapping.

| Sample File | Tests | FR Coverage |
|-------------|-------|-------------|
| `sample_tables.docx` | Multi-row tables (4 data rows) with `[[TableN]]` markers; single-row table with `[[Table]]` unnumbered marker | FR-010, FR-026 |
| `sample_lists.docx` | Bullet lists, numbered lists, nested bullet lists → text elements with list prefixes | FR-009, FR-016 |
| `sample_headers_footers.docx` | 3-page doc with right-aligned header text + centered footer with `PAGE` field code | FR-014, FR-026 |
| `sample_images.docx` | Embedded PNG images with captions → image elements with base64 encoding | FR-011 |
| `sample_multipage.docx` | 3 chapters across 3 pages: H1→H2 title hierarchy tracking + table on page 2 | FR-008, FR-021, FR-025 |
| `sample3.docx` | Real-world Chinese document (existing fixture) — unicode, CJK text, mixed content | FR-002, SC-013 |

### WIPO-Inspired Edge Case Scenarios (from WIPO DocConverter sample page)

The WIPO PCT DocConverter page lists ~30 sample documents categorizing supported and unsupported features. These map to our spec's edge cases:

**Features we handle (per spec)**:
| WIPO Category | Our Handling |
|---------------|-------------|
| Math equations (MathType/OMML) | Extract as `formula` elements with LaTeX content (FR-013) |
| Chemical formulas | Same formula extraction path; may need formula_type="Chemical" |
| Tables with/without captions | Full table extraction with `[[TableN]]` markers (FR-010) |
| Bullets and numbering | Text elements with list prefixes (FR-009) |
| Header, footer, comments | Header/footer as typed elements; comments logged as warning (FR-014) |
| Multi-language (EN, ZH, JA, KO, FR, DE, PT, RU, ES, AR, IT) | Unicode sanitization; CJK/arabic text in content fields (FR-002, SC-013) |
| Drawings/images | Image elements with base64 (FR-011) |

**Features we log as warnings** (unsupported):
| WIPO Category | Our Handling |
|---------------|-------------|
| Track change mode | Warning: "tracked changes detected — accept before processing" (Edge Case) |
| Embedded OLE objects | Warning: "OLE object not extracted" (Edge Case) |
| Nested tables (with/without content) | Warning if nesting > 3 levels (Edge Case) |
| Charts in description/drawings | Extract: chart data → markdown table; fallback: chart → image (FR-012) |
| Shapes created with text editor | Ignored as non-semantic content |
| Grouped/overlapped images | Extracted individually; z-order not preserved |
| Text effects (WordArt, shadows) | Ignored; plain text extracted |
| Content control objects | Text content extracted; control metadata ignored |
| Hyperlinks | Link text extracted; URL available via OOXML if docling supports |
| Non-standard table-in-drawings | Table extracted if OOXML table markup present |
| Incorrect figure numbering | As-is extraction (no renumbering) |

### TDD Sample-Driven Test Flow

```text
For each sample file:
  1. Write failing test: "Given sample_<name>.docx → Expect <N> elements of type <T>"
  2. Run test → RED (no backend support yet)
  3. Implement docling backend mapping for that element type
  4. Run test → GREEN
  5. Refactor: common patterns, DRY, error handling
  6. Write silver test: "Given bronze JSON → Expect JSONL with <marker> markers"
  7. Implement silver renderer extension
  8. Run test → GREEN
```

---

## Incremental Implementation Phases (Optimization)

The original plan treats all element types as a single implementation block. This optimization splits work into four incremental phases, each independently testable with sample files.

### Phase A: Core DOCX Foundation (P1 — User Story 1, 3) ⟹ tasks Phase 3-4

**Scope**: Accept .docx paths, extract 4 core element types (text, table, title, image) — same as PDF pipeline.

**Files**: `processor.py` (generalize), `docling_backend.py` (initial .docx mapping), `cli.py` (accept .docx paths)

**Sample tests**: `sample_multipage.docx` (title hierarchy), `sample_tables.docx` (table extraction)

**Deliverable**: Working .docx → bronze JSON pipeline with 4 element types. Silver/gold stages work unchanged.

### Phase B: Rich Element Types (P1 — User Story 1) ⟹ tasks Phase 5-6

**Scope**: Add chart, formula, header, footer, footnote, endnote extraction from .docx.

**Files**: `docling_backend.py` (extend), `element_types.py` (new models), `markdown_renderer.py` (extend)

**Sample tests**: `sample_headers_footers.docx` (header/footer), `sample_lists.docx` (list rendering)

**Deliverable**: Full 10-element type bronze output. Silver renderer extended with all markers.

### Phase C: Legacy DOC Support (P2 — User Story 2) ⟹ tasks Phase 7

**Scope**: .doc detection, LibreOffice bridge, intermediate PDF cleanup.

**Files**: `soffice_backend.py` (NEW), `processor.py` (format dispatch), `cli.py` (--backend auto)

**Sample tests**: Pipeline output from existing `.doc` file in samples/

**Deliverable**: .doc files processed via LibreOffice → PDF → PyMuPDF, with 4 element types.

### Phase D: Polish & Edge Cases (P2-P3 — User Stories 4, 5) ⟹ tasks Phase 8-10

**Scope**: Chart data extraction fallback, OLE warnings, tracked changes warnings, nested table handling, password-protection detection.

**Files**: `docling_backend.py` (edge case handling), gold stage (unchanged — reuses existing)

**Deliverable**: All edge cases covered, warnings logged, all 11 edge cases from spec verified.

### Phase Dependency Graph

```text
Phase A (Core .docx) ──┬──→ Phase B (Rich types) ──→ Phase D (Polish)
                        │
                        └──→ Phase C (Legacy .doc) ──→ Phase D (Polish)
```

Phases A and C are parallelizable. Phase B depends on A. Phase D depends on B and C.

---

## Risk Assessment (Updated with WIPO Findings)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docling chart/formula extraction incomplete for some .docx files | Medium | Medium | Fallback to image capture; verified against WIPO math/chemical formula samples |
| LibreOffice not available on user's system | Medium | Low | Clear error message; .docx-only users unaffected; check at pipeline start |
| .doc → PDF conversion fidelity loss | High | Low | .doc is P2; documented limitation; log warning per FR-020 |
| Performance regression for existing PDF pipeline | Low | High | PDF path completely unchanged; separate code paths; existing tests gate |
| WIPO-level complexity (nested tables in drawings, grouped images) | Medium | Low | Graceful degradation: extract what we can, log warnings for unparseable constructs |
| CJK/multi-language text extraction fidelity | Medium | Medium | Existing Unicode sanitization handles CJK; `sample3.docx` validates Chinese text paths |
| Docling version drift (API changes across v2.x) | Low | Medium | Pin `docling>=2.0.0,<3.0`; integration tests catch breakage on dep upgrades |
