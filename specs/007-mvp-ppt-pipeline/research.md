# Research: PPT/PPTX Pipeline Libraries & Architecture

**Feature**: `007-mvp-ppt-pipeline`
**Date**: 2026-07-09

## Research Questions

### RQ0: What real-world .ppt/.pptx documents exist for testing?

**Decision**: Use public parser test corpora, supplemented by a legacy binary .ppt fixture.

**Rationale**: Reliable, programmatically-downloadable .pptx fixtures with rich structure exist in established open-source parser test suites. Eight fixtures were collected into `samples/`:

| Source | File | Coverage |
|--------|------|----------|
| docling test data | `sample_pptx_basic.pptx` | text, titles |
| docling test data | `sample_pptx_image.pptx` | embedded images |
| docling test data | `sample_pptx_comments.pptx` | reviewer comments + authors |
| docling test data | `sample_pptx_issue.pptx` | complex layout stress test |
| docling test data | `sample_pptx_shapes.pptx` | grouped/unrecognized shapes |
| python-pptx features | `sample_pptx_chart_bar.pptx` | embedded bar chart |
| unstructured example-docs | `sample_pptx_unstructured.pptx` | mixed text content |
| Apache POI test-data | `sample_ppt_legacy.ppt` | legacy binary OLE .ppt |

**Alternatives considered**: FileFormat/File-Examples/Sample-Files download pages (JS-gated or HTML-wrapped; not reliably fetchable via curl — returned HTML, not PK/OLE payloads). GitHub raw corpora proved the most reliable direct-download source.

### RQ1: python-pptx for .pptx — Element Type Coverage

**Decision**: `python-pptx >= 0.6.23` as the primary shape-level extractor.

**Rationale**:
- Native OOXML reading; exposes the full slide shape tree (placeholders, text frames, tables, pictures, group shapes, GraphicFrame, connectors)
- Slide `notes_slide` provides speaker notes; `slide.shapes` iteration gives geometry (`left`/`top`/`width`/`height`) for the hybrid geometric+z-order sort
- Hyperlink access via run-level `hyperlink.address`
- Hidden-slide detection via the slide `show` attribute
- Table cell iteration for markdown table synthesis
- Pure-Python, lightweight, BSD-licensed, stable and widely adopted

**Alternatives considered**:
- `docling` alone: flattens slides; no discrete speaker notes / comments / group structure
- `Aspose.Slides`, `Spire.Presentation`: commercial licensing — violates open-source constitution
- LibreOffice → PDF for .pptx: discards SmartArt/notes/comments richness

### RQ2: docling as chart-data / table assist

**Decision**: Use docling (existing optional dep) opportunistically for cleaner table markdown and embedded chart data.

**Rationale**: python-pptx exposes `chart.plots` categories/series but produces raw data; docling yields cleaner table serialization and chart classification. `PptxBackend` uses python-pptx first, docling for chart/table refinement when available, and base64 image as the final fallback (FR-012).

### RQ3: Legacy .ppt (OLE binary) approach

**Decision**: Reuse the existing `soffice_backend.py` LibreOffice bridge + PyMuPDF backend, extended to accept `.ppt`.

**Rationale**: The soffice bridge already exists from 006 and is well-tested. No open-source Python library reliably parses the binary .ppt format with structured extraction. `.ppt` is the minority P2 format; 4-type output (text/table/title/image) is acceptable. Intermediate PDF deleted after bronze JSON generation (FR-020).

**LibreOffice detection** (reused): `shutil.which("soffice")`.
**Conversion**: `soffice --headless --convert-to pdf --outdir <dir> <input.ppt>`.

**Alternatives considered**: `olefile` (would need a full binary .ppt parser — impractical); commercial libs (license conflict).

### RQ4: SmartArt text extraction

**Decision**: Parse the underlying diagram data (`dgm:`/`a:t` nodes in the diagram data part) referenced by the shape; fall back to base64 image on failure.

**Rationale**: python-pptx has no first-class SmartArt API. SmartArt (DrawingML Diagram) stores its text in a `diagramData` part linked from the graphic frame. Extracting the `<a:t>` text nodes hierarchically yields the `content`; the diagram layout type maps to `smartart_type`. When parsing fails, the rendered fallback image (if present) is captured as the `image` field.

### RQ5: How should the silver renderer handle the expanded element set?

**Decision**: Add case branches to the existing `render_page()` function; no architectural change.

**Rationale**: The renderer is a dispatch over element type. New types (smartart, notes, comment) get dedicated branches. Global counters for chart/formula/smartart mirror the existing table counter. Notes render after slide content; comments render inline with author. Backward compatibility preserved — PDF/DOC JSONL unaffected.

### RQ6: Pagination unit & cross-pipeline contract

**Decision**: `page_no` = physical slide number (1-indexed, continuous incl. hidden). Silver `metadata.page_no` value = `"page1"`.

**Rationale**: Matches PDF/DOC JSONL contract (SC-016) for interchangeable downstream consumption; slide semantics conveyed by source file type (spec clarification). Hidden slides carry `hidden: true` through all stages.

---

## Dependency Impact

| Dependency | Change | Reason |
|-----------|--------|--------|
| `python-pptx>=0.6.23` | NEW optional extra `[pptx]` | Primary .pptx shape extractor |
| `docling>=2.0.0` | Already optional; no change | Chart/table assist |
| External: `soffice` | Reused from 006 | Legacy .ppt only |
| `office` extra | NEW convenience extra | Bundles docling + python-pptx |
| All other deps | No change | Reuse existing stack |

## Risk Assessment

See plan.md "Risk Assessment" section for the consolidated risk table.
