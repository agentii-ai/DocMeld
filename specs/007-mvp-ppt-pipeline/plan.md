# Implementation Plan: MVP PowerPoint (PPT/PPTX) Data Pipeline

**Branch**: `007-mvp-ppt-pipeline` (developed on `main` per user directive) | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/007-mvp-ppt-pipeline/spec.md`

> **Note**: This plan is generated pre-optimized — it bakes in the incremental phase structure (Phases A–E), sample-driven TDD strategy, and risk assessment that were retrofitted onto earlier pipeline plans. It mirrors the proven 001 (PDF) and 006 (DOC) plans.

## Summary

Extend the existing DocMeld three-stage pipeline (Bronze → Silver → Gold) to process PowerPoint presentations (.ppt and .pptx) alongside PDFs and Word documents. Modern .pptx files are parsed via **python-pptx** for slide-level shape extraction (text, titles, tables, images, speaker notes, comments, grouped shapes, SmartArt text, footers, hyperlinks) supplemented by **docling** for richer table structure and embedded chart data. Legacy .ppt files are converted to PDF via the existing LibreOffice `soffice` bridge and processed through the existing PyMuPDF backend. The unit of pagination is the **slide** (`page_no` = physical slide number, 1-indexed, continuous including hidden slides). The silver and gold stages are extended to render presentation-specific element types with new marker syntax for SmartArt (`[[SmartArtN]]`), speaker notes (`[Notes]`), comments (`[Comment: author]`), charts, and formulas. The existing `ParserBackend` protocol, `BronzeProcessor`, and `soffice_backend.py` are reused; a new `PptxBackend` is added. Backward compatibility with the PDF and DOC pipelines and the existing PyPI package is preserved.

## Technical Context

**Language/Version**: Python 3.9+ (minimum supported per constitution)
**Primary Dependencies**: PyMuPDF (fitz), pymupdf4llm, pandas, openpyxl, pydantic, python-dotenv, langchain-deepseek (existing); docling >= 2.0.0 (existing optional dep); **python-pptx >= 0.6.23 (NEW optional dep)**; LibreOffice/soffice (external, required only for .ppt)
**Storage**: Local filesystem (JSON, JSONL, log files) — no database
**Testing**: pytest with pytest-cov (90%+ coverage target, 100% for core parser); all existing tests must remain green
**Target Platform**: macOS, Linux, Windows (cross-platform; .ppt support requires LibreOffice installation)
**Project Type**: Single library project with CLI interface (published on PyPI as `docmeld`)
**Performance Goals**: <5 min for 10-50 slide .pptx through all stages; <8 min for .ppt (including LibreOffice conversion); <500MB memory for 100-slide presentations
**Constraints**: No OCR/VLM for core processing; offline-capable for bronze/silver; API-dependent for gold; existing PDF and DOC pipelines must be unaffected; animations/transitions/video/audio excluded
**Scale/Scope**: MVP handles digital-native .pptx and legacy .ppt; batch processing of 100+ mixed-format files; 95% success rate target for .pptx, 85% for .ppt
**Current Version**: 0.2.0 on PyPI; this feature targets 0.3.0

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Test-First Development (NON-NEGOTIABLE)
- ✅ **PASS**: Tests written before any new implementation code
- ✅ **PASS**: Existing test suite must pass before starting new work
- ✅ **PASS**: Integration tests required for pptx→bronze→silver→gold end-to-end
- ✅ **PASS**: Unit tests for each new element type (smartart, notes, group, comment), the PptxBackend, and renderer extensions

### Principle II: Library-First, PyPI-Ready
- ✅ **PASS**: `DocMeldParser` already importable; will accept .ppt/.pptx paths
- ✅ **PASS**: CLI built on top of library API; `--backend` flag extended with `pptx` choice
- ✅ **PASS**: Type hints and docstrings for all new public API
- ✅ **PASS**: Bump to 0.3.0 (MINOR version) — new element types are additive, no breaking changes to existing contract

### Principle III: Lightweight by Default
- ✅ **PASS**: python-pptx is a lightweight pure-Python dependency, added as an optional extra (`pip install docmeld[pptx]`)
- ✅ **PASS**: docling remains an optional dependency (`pip install docmeld[docling]`)
- ✅ **PASS**: LibreOffice is external, not a Python dependency — guarded with existing availability check
- ✅ **PASS**: Core base install remains unchanged (PyMuPDF only); memory constraint <500MB for 100 slides

### Principle IV: Unified Element Format
- ✅ **PASS**: All elements include `type` and `page_no` fields; element order preserves reading order
- ⚠️ **ACTION REQUIRED**: Constitution Principle IV enumerates 10 types (title, text, table, image, chart, formula, header, footer, footnote, endnote). This feature adds **3 presentation-native types** (`smartart`, `notes`, `group`) and one collaboration type (`comment`), and does **not** use header/footnote/endnote. Principle IV must be amended (MINOR, additive) to register `smartart`, `notes`, `group`, `comment`.

### Principle V: Agent-Ready Outputs
- ✅ **PASS**: Extended output with SmartArt text, speaker notes, comments, chart data, inline hyperlinks
- ✅ **PASS**: Source attribution preserved (slide numbers via `page_no`, source filename)
- ✅ **PASS**: Same JSONL contract as PDF/DOC pipelines — `page_no` value uses `"page1"` for interchangeability (spec clarification)

### Principle VI: Production-Grade Quality
- ✅ **PASS**: Ruff, black, mypy for all new code
- ✅ **PASS**: Explicit error handling for corrupted .pptx, missing LibreOffice, password-protected files
- ✅ **PASS**: Graceful handling with warnings for OLE objects, animations, unsupported formats (.pptm/.potx/.odp)

### Principle VII: Open-Source Excellence
- ✅ **PASS**: MIT license unchanged
- ✅ **PASS**: CHANGELOG entry for 0.3.0; README update announcing .ppt/.pptx support

**Gate Status**: ✅ **PASSED** (1 action item: amend constitution Principle IV to register `smartart`, `notes`, `group`, `comment` element types — additive, MINOR)

## Project Structure

### Documentation (this feature)

```text
specs/007-mvp-ppt-pipeline/
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
├── samples/                      # [UPDATED] Test fixtures for PPTX pipeline
│   ├── sample_pptx_basic.pptx        #   Text + titles across slides
│   ├── sample_pptx_image.pptx        #   Embedded images
│   ├── sample_pptx_comments.pptx     #   Reviewer comments with authors
│   ├── sample_pptx_chart_bar.pptx    #   Embedded bar chart (data + image)
│   ├── sample_pptx_shapes.pptx       #   Grouped/unrecognized shapes
│   ├── sample_pptx_issue.pptx        #   Edge-case layout stress test
│   ├── sample_pptx_unstructured.pptx #   Mixed text content
│   └── sample_ppt_legacy.ppt         #   Legacy binary .ppt (soffice path)
│
├── docmeld/
│   ├── __init__.py                       # [UPDATE] Version bump to 0.3.0
│   ├── parser.py                         # [UPDATE] Accept .ppt/.pptx paths
│   ├── cli.py                            # [UPDATE] Extend --backend with `pptx`; accept .ppt/.pptx paths
│   │
│   ├── bronze/
│   │   ├── processor.py                  # [UPDATE] Format dispatch: .pptx→pptx, .ppt→soffice
│   │   ├── filename_sanitizer.py         # [REUSE] Works for any extension
│   │   ├── element_extractor.py          # [UPDATE] Extend dispatch for PptxBackend
│   │   ├── element_types.py              # [UPDATE] Add SmartArtElement, NotesElement, GroupElement, CommentElement
│   │   └── backends/
│   │       ├── __init__.py               # [REUSE] ParserBackend protocol (already generic)
│   │       ├── pymupdf_backend.py        # [REUSE] Unchanged
│   │       ├── docling_backend.py        # [UPDATE] Add .pptx table/chart-data assist path
│   │       ├── soffice_backend.py        # [REUSE] LibreOffice → PDF → PyMuPDF; extend to accept .ppt
│   │       └── pptx_backend.py           # [NEW] python-pptx slide-level shape extraction
│   │
│   ├── silver/
│   │   ├── processor.py                  # [UPDATE] Source filename reflects .ppt/.pptx origin
│   │   ├── markdown_renderer.py          # [UPDATE] Add smartart, notes, comment, chart, formula rendering
│   │   ├── title_tracker.py              # [UPDATE] Support PPTX section→H1 / slide-title→H2 hierarchy
│   │   ├── page_aggregator.py            # [REUSE] Groups by page_no (slide)
│   │   └── page_models.py                # [REUSE] Existing models
│   │
│   ├── gold/                             # [REUSE] Entire stage unchanged (works on any JSONL)
│   │
│   └── utils/                            # [REUSE] logging, env_loader, progress — unchanged
│
└── tests/
    ├── unit/
    │   ├── test_pptx_backend.py          # [NEW] python-pptx shape → element mapping
    │   ├── test_soffice_backend.py       # [UPDATE] Add .ppt conversion tests
    │   ├── test_element_types.py         # [UPDATE] smartart/notes/group/comment model validation
    │   ├── test_markdown_renderer.py     # [UPDATE] New marker tests ([[SmartArtN]], [Notes], [Comment])
    │   └── test_filename_sanitizer.py    # [UPDATE] Verify ppt/pptx extension handling
    ├── integration/
    │   ├── test_bronze_pipeline.py       # [UPDATE] .pptx/.ppt path testing
    │   ├── test_silver_pipeline.py       # [UPDATE] New element rendering + slide grouping
    │   ├── test_gold_pipeline.py         # [REUSE] Works on any JSONL
    │   ├── test_end_to_end.py            # [UPDATE] .pptx e2e traversal
    │   └── test_cli.py                   # [UPDATE] --backend auto/pptx/pymupdf tests
    └── contract/
        └── test_element_schema.py        # [UPDATE] Validate PPT element types against schema
```

**Structure Decision**: Single library project — follows existing `docmeld/docmeld/` and `docmeld/tests/` layout. No new modules outside the existing hierarchy. The new `pptx_backend.py` sits alongside existing backends; `soffice_backend.py` is reused (extended to accept `.ppt`). Element type models extend `bronze/element_types.py`. The silver renderer adds case branches for the new types. CLI adds the `pptx` backend choice and accepts non-.pdf/.docx paths.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV amendment: register `smartart`, `notes`, `group`, `comment` | Presentations carry structure absent from PDF/DOC (SmartArt diagrams, speaker notes, grouped shapes, reviewer comments) that is the primary value of a native PPTX pipeline | Rejected: limiting output to existing types would discard the key advantage of direct OOXML shape parsing |
| Two libraries for one format (python-pptx + docling) | python-pptx exposes slide shapes/notes/comments/groups that docling flattens; docling produces better table markdown + chart data than python-pptx | Rejected: python-pptx alone lacks robust table/chart-data extraction; docling alone lacks notes/comments/group granularity |
| `element_id` format `e_{i+1:03d}` caps at 999 elements | Rich 100-slide decks with charts/SmartArt can exceed 999 elements; existing code uses `:03d` padding | Widen to `e_{i+1:04d}` (supports up to 9,999 elements); schema regex widened to `^e_\\d{4}$` — non-breaking (shorter ids still match); apply in Phase B |

---

## Phase 0: Research & Decisions

### R1: python-pptx as the primary .pptx backend

**Decision**: Use `python-pptx >= 0.6.23` as the primary shape-level extractor for .pptx.

**Rationale**: python-pptx reads the OOXML package natively and exposes the full slide shape tree: text frames, title/body placeholders, tables, pictures, group shapes, GraphicFrame (charts/tables), connectors, and the notes slide. It provides shape geometry (`left`/`top`/`width`/`height`) needed for the hybrid geometric+z-order sort (FR-018), hyperlink runs (FR-009a), and access to slide `show` state for hidden-slide detection. Pure-Python, lightweight, MIT-compatible (BSD), and stable.

**Alternatives considered**:
- `docling` alone: flattens slides; does not expose speaker notes, comments, or grouped-shape structure as discrete items
- `Aspose.Slides` / `Spire.Presentation`: commercial licensing — violates open-source constitution
- LibreOffice → PDF for .pptx: discards SmartArt/notes/comments richness (the whole point of the feature)

### R2: docling as the chart-data / table assist

**Decision**: Use docling (existing optional dep) to enrich tables and extract embedded chart data where python-pptx is weaker.

**Rationale**: python-pptx exposes chart objects and their plot categories/series, but docling's table serialization and chart-data classification produce cleaner markdown tables. The `PptxBackend` calls python-pptx first; for chart/table elements it opportunistically uses docling output when available, falling back to python-pptx's own `chart.plots` category/series data, and finally to a base64 image (FR-012).

### R3: Legacy .ppt support — reuse the existing soffice bridge

**Decision**: Reuse the existing `soffice_backend.py` (LibreOffice `--headless --convert-to pdf`) + PyMuPDF backend, extended to accept `.ppt`.

**Rationale**: The soffice bridge already exists from the 006 DOC pipeline and is well-tested. No open-source Python library reliably parses the legacy binary .ppt (OLE) format with structured extraction. Element richness for .ppt is limited to the 4 PDF-derived types (text, table, title, image) — acceptable since .ppt is the minority P2 format. The intermediate PDF is deleted after successful bronze JSON generation (FR-020).

**Concrete change**: `SofficeBackend` today hard-codes a `.doc`-only suffix guard (`soffice_backend.py`: `if doc_path_obj.suffix.lower() != ".doc": raise ...`). Generalize this guard to an accepted-suffix set `{".doc", ".ppt"}` and rename the docstring/param semantics from "doc" to "source document". The conversion command (`soffice --headless --convert-to pdf`) is format-agnostic and needs no change. The existing single retry-on-corrupt-PDF path is reused.

**Alternatives considered**: `olefile` (would require a full binary .ppt parser); commercial libs (license conflict).

### R4: Element type extension strategy

**Decision**: Extend `element_types.py` with 4 new Pydantic models, keeping the existing 10 types unchanged.

**Rationale**: Backward compatibility (Principle IV). New types are additive (MINOR bump). The `BronzeElement` union grows to include `SmartArtElement`, `NotesElement`, `GroupElement`, `CommentElement`. Presentation output does **not** emit header/footnote/endnote (not applicable), but those types remain in the schema for cross-pipeline validity.

**Key design choices**:
- `SmartArtElement`: `content` (hierarchical markdown), `smartart_type` (process/cycle/hierarchy/relationship/pyramid), `image` (base64 fallback), `image_name`
- `NotesElement`: `content` (plain markdown notes text), `page_no` (parent slide)
- `GroupElement`: `content` (description), `child_count`, `element_id` (children reference via `parent_id`)
- `CommentElement`: `content`, `author`, `page_no`
- `hidden`: optional boolean flag added to all element types (defaults false), set true for elements on hidden slides (spec Assumption 6)

### R5: Silver renderer extension

**Decision**: Extend `render_page()` with case branches for each new element type, following the existing pattern.

**Rationale**: Each new type gets a dedicated rendering branch with consistent marker syntax. Chart/formula/SmartArt use independent global counters mirroring the existing table counter.

| Element Type | Marker Syntax | Content |
|-------------|---------------|---------|
| table | `[[TableN]]` … `[/TableN]` | Markdown table (existing) |
| chart | `[[ChartN]]` … `[/ChartN]` | Markdown table of chart data |
| formula | `[[FormulaN]]` … `[/FormulaN]` | LaTeX content |
| smartart | `[[SmartArtN]]` … `[/SmartArtN]` | Hierarchical markdown text |
| notes | `[Notes]` … `[/Notes]` | Speaker notes text (rendered after slide content) |
| comment | `[Comment: author]` … `[/Comment]` | Reviewer comment text |
| footer | `[Footer]` … `[/Footer]` | Footer/placeholder text |
| image | `[[Image: description]]` | Placeholder |
| title | `#`/`##`/`###` | Markdown heading by level |
| hyperlink | inline `[text](url)` | Preserved within parent element content |

### R6: Slide as the pagination unit

**Decision**: `page_no` = physical slide number, 1-indexed, continuous (hidden slides consume a number). Silver `metadata.page_no` value = `"page1"` for cross-pipeline interchangeability.

**Rationale**: Matches the JSONL contract of PDF/DOC pipelines (SC-016) while conveying slide semantics via source file type (spec clarification). Hidden slides carry `hidden: true` and flow through all stages (spec clarification).

### R7: Package versioning & dependency packaging

**Decision**: Bump 0.2.0 → 0.3.0 (MINOR). Add `pptx = ["python-pptx>=0.6.23"]` optional extra; add a convenience `office = ["docling>=2.0.0", "python-pptx>=0.6.23"]` extra.

**Rationale**: New element types and format support are additive. python-pptx as an extra keeps the base install lightweight (Principle III).

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions. Key additions:

1. **4 new Pydantic models**: SmartArtElement, NotesElement, GroupElement, CommentElement
2. **Expanded BronzeElement union**: now covers 14 element types (10 existing + 4 new); PPT output uses a subset (text, table, title, image, chart, formula, smartart, notes, group, footer, comment)
3. **New optional field**: `hidden: bool` on all element types (default false)
4. **Unchanged entities**: SilverPage, GoldPage, ProcessingResult — same contract as PDF/DOC pipelines

### Interface Contracts

See [contracts/element-schema.json](./contracts/element-schema.json) — JSON Schema extended with `smartart`, `notes`, `group`, `comment` in the `type` enum plus their required fields, and the optional `hidden` boolean. Backward compatible: existing PDF/DOC outputs still validate.

### Quickstart

See [quickstart.md](./quickstart.md) for developer onboarding with .pptx and .ppt examples.

---

## Sample-Driven Testing Strategy

The `samples/` directory contains 8 fixtures (7 .pptx + 1 legacy .ppt) covering each element type and edge case, downloaded from public parser test corpora (docling, python-pptx, unstructured, Apache POI).

### Sample Inventory

| Sample File | Tests | FR Coverage |
|-------------|-------|-------------|
| `sample_pptx_basic.pptx` | Text + title placeholders, slide title hierarchy | FR-008, FR-009, FR-027 |
| `sample_pptx_image.pptx` | Embedded images → image elements with base64 | FR-011 |
| `sample_pptx_comments.pptx` | Reviewer comments with author attribution | FR-017a, comment rendering |
| `sample_pptx_chart_bar.pptx` | Embedded bar chart → data table + image fallback | FR-012 |
| `sample_pptx_shapes.pptx` | Grouped shapes / unrecognized shapes → group + child elements | FR-016 |
| `sample_pptx_issue.pptx` | Complex/overlapping layout → hybrid ordering + >20-element debug log | FR-018 |
| `sample_pptx_unstructured.pptx` | Mixed text content across slides | FR-009, FR-026 |
| `sample_ppt_legacy.ppt` | Legacy binary → soffice → PDF → PyMuPDF (4 types) | FR-020, FR-021, FR-022 |

> **Coverage gaps**: No dedicated formula/SmartArt/notes fixtures exist in the public parser corpora. Mitigation by type: **notes** — inject via `slide.notes_slide.notes_text_frame.text` with python-pptx (supported); **formula** — inject an OMML `<m:oMathPara>` blob into a run's XML (low-level, python-pptx `oxml`); **SmartArt** — python-pptx has **no** SmartArt-creation API, so author one small fixture manually in PowerPoint/LibreOffice and commit it, or assert graceful image-fallback on `sample_pptx_shapes.pptx`.

### TDD Sample-Driven Test Flow

```text
For each sample file:
  1. Write failing test: "Given sample_<name>.pptx → Expect <N> elements of type <T>"
  2. Run test → RED (no PptxBackend support yet)
  3. Implement python-pptx mapping for that element type
  4. Run test → GREEN
  5. Refactor: common patterns, DRY, error handling
  6. Write silver test: "Given bronze JSON → Expect JSONL with <marker> markers"
  7. Implement silver renderer extension → GREEN
```

---

## Incremental Implementation Phases (Optimization)

Work is split into five incremental phases, each independently testable with sample files.

### Phase A: Core PPTX Foundation (P1 — User Story 1, 3) ⟹ tasks Phase 3-4

**Scope**: Accept .pptx paths, extract 4 core element types (text, table, title, image) via python-pptx; slide = page_no.

**Files**: `processor.py` (format dispatch), `pptx_backend.py` (NEW — core mapping), `cli.py` (accept .pptx paths, `pptx` backend)

**Sample tests**: `sample_pptx_basic.pptx` (titles/text), `sample_pptx_image.pptx` (images)

**Deliverable**: Working .pptx → bronze JSON with 4 element types. Silver/gold work unchanged.

### Phase B: Presentation-Rich Element Types (P1 — User Story 1) ⟹ tasks Phase 5-6

**Scope**: Add chart (with docling assist), formula, smartart, notes, group, footer, comment, and inline hyperlinks. Hybrid geometric+z-order sort (FR-018). Hidden-slide flagging.

**Files**: `pptx_backend.py` (extend), `docling_backend.py` (chart/table assist), `element_types.py` (4 new models + `hidden`), `markdown_renderer.py` (new markers), `title_tracker.py` (section→H1 / title→H2)

**Sample tests**: `sample_pptx_chart_bar.pptx`, `sample_pptx_comments.pptx`, `sample_pptx_shapes.pptx`, `sample_pptx_issue.pptx`

**Deliverable**: Full presentation element set in bronze; silver renderer extended with all markers.

### Phase C: Legacy PPT Support (P2 — User Story 2) ⟹ tasks Phase 7

**Scope**: .ppt detection, reuse soffice bridge (extend to accept .ppt), intermediate PDF cleanup, LibreOffice availability check.

**Files**: `soffice_backend.py` (accept .ppt), `processor.py` (dispatch), `cli.py` (`--backend auto`)

**Sample tests**: `sample_ppt_legacy.ppt` end-to-end.

**Deliverable**: .ppt processed via LibreOffice → PDF → PyMuPDF, 4 element types.

### Phase D: Silver/Gold Contract Parity (P2-P3 — User Stories 4, 5) ⟹ tasks Phase 8

**Scope**: Verify silver JSONL emits exactly one line per slide with `page_no: "page1"` convention and complete title context; gold enrichment reused unchanged; cross-pipeline JSONL parity check (SC-016).

**Files**: `silver/processor.py`, `silver/page_aggregator.py` (verify slide grouping); gold stage unchanged.

**Deliverable**: PPT JSONL interchangeable with PDF/DOC JSONL; gold descriptions/keywords per slide.

### Phase E: Polish & Edge Cases (P3) ⟹ tasks Phase 9-10

**Scope**: OLE-object warnings, animation/video exclusion, password-protection detection, unsupported-format skips (.pptm/.potx/.odp), nested SmartArt/group depth warnings, broken-hyperlink fallback, summary report.

**Files**: `pptx_backend.py` (edge handling), `processor.py` (format filtering)

**Deliverable**: All spec edge cases covered with warnings logged; all functional requirements verified.

### Phase Dependency Graph

```text
Phase A (Core .pptx) ──→ Phase B (Rich types) ──→ Phase D (Silver/Gold parity) ──→ Phase E (Polish)
        │                                              ▲
        └──→ Phase C (Legacy .ppt) ────────────────────┘
```

Phases A and C are parallelizable after A's dispatch scaffolding. Phase B depends on A. Phase D depends on B and C. Phase E depends on D.

### Effort & Task Estimates (input for `/speckit.tasks`)

| Phase | New/Changed files | Est. tasks | Est. LOC (impl+test) | Parallelizable |
|-------|-------------------|-----------|----------------------|----------------|
| A — Core PPTX | `pptx_backend.py` (new), `processor.py`, `cli.py` | 6–8 | ~350 | after scaffolding |
| B — Rich types | `pptx_backend.py`, `docling_backend.py`, `element_types.py`, `markdown_renderer.py`, `title_tracker.py` | 12–16 | ~700 | with C |
| C — Legacy PPT | `soffice_backend.py`, `processor.py` | 3–4 | ~120 | with B |
| D — Silver/Gold parity | `silver/processor.py`, `page_aggregator.py` (verify) | 3–5 | ~150 | no |
| E — Polish | `pptx_backend.py`, `processor.py` | 5–7 | ~200 | no |

Total estimate: **29–40 tasks, ~1,520 LOC**. Phase B is the critical path (largest, gates D). Recommend front-loading B's SmartArt spike (highest-risk item per Risk Assessment) before committing to the full element set.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SmartArt text extraction incomplete (python-pptx has no first-class SmartArt API) | High | Medium | Parse the underlying `dgm:` diagram data XML from the shape part; fall back to base64 image with a warning |
| Chart data extraction fails for uncommon chart types | Medium | Medium | docling assist first, python-pptx `chart.plots` second, base64 image fallback (FR-012) |
| Geometric reading order unreliable for free-form/overlapping slides | Medium | Low | Hybrid sort: geometric primary, z-order (shape-tree order) tie-breaker (FR-018); debug log when >20 elements |
| LibreOffice not available for .ppt | Medium | Low | Clear error message; .pptx-only users unaffected; reuse existing 006 availability check |
| .ppt → PDF conversion fidelity loss | High | Low | .ppt is P2; documented limitation; 4-type output; log warning (FR-022) |
| Performance/regression for existing PDF & DOC pipelines | Low | High | PDF/DOC paths unchanged; separate `pptx_backend.py`; existing tests gate |
| python-pptx cannot open a malformed/newer .pptx | Low | Medium | Explicit exception handling → skip file, log, continue batch (FR-042); pin `python-pptx>=0.6.23` |
| Comments/notes parts absent or malformed | Medium | Low | Guard optional OOXML parts; emit no element when absent; no crash |
| Constitution Principle IV lag (new types not registered) | Medium | Low | Amendment queued as action item before merge; schema updated in Phase 1 |
