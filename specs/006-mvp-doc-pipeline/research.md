# Research: DOC/DOCX Pipeline Libraries & Architecture

**Feature**: `006-mvp-doc-pipeline`
**Date**: 2026-07-09

## Research Questions

### RQ0: What real-world .docx documents exist for testing? (WIPO Samples)

**Decision**: Generate synthetic test fixtures covering all element types, supplemented with WIPO DocConverter sample categories as test scenarios.

**Rationale**: The WIPO PCT DocConverter page lists ~30 curated .docx samples across supported and unsupported feature categories. These are the gold standard for testing .docx extraction tools. However, WIPO uses PrimeFaces JSF with session-gated downloads — files cannot be fetched programmatically. Instead, we:
1. Generated 5 .docx samples covering the core WIPO categories using python-docx
2. Retained the existing Chinese document (`sample3.docx`) as a real-world multi-language fixture
3. Mapped all 30 WIPO categories to our spec's handling strategy (see plan.md section "WIPO-Inspired Edge Case Scenarios")

**WIPO categories mapped**:
- Supported: math equations, chemical formulas, tables, bullets/numbering, headers/footers, drawings, multi-language (11 languages)
- Unsupported/partial: track changes (warning), OLE objects (warning), nested tables (warning past L3), charts (data+image fallback), grouped images (individual extraction), text effects (ignored), shapes (ignored), content controls (text only)

**Alternatives considered**: Direct WIPO download (JSF-gated, not automatable); other sample sources (file-examples.com — low quality; GitHub repos — sparse coverage). Generated samples with python-docx provide controlled, reproducible fixtures.

### RQ1: Docling for .docx — Element Type Coverage

**Decision**: IBM docling (`docling >= 2.0.0`)

**Rationale**:
- Already an optional dependency in the existing project (`pip install docmeld[docling]`)
- Reads OOXML natively — no PDF conversion needed
- Provides structured item iteration (`doc.iterate_items()`) with types: SectionHeaderItem, TextItem, ListItem, TableItem, PictureItem, KeyValueItem, CodeItem
- Has chart classification capabilities (`PictureClassificationItem`) and chart data APIs
- Supports MathType/OMML formula extraction via `FormulaItem`
- Provides header/footer awareness via document structure tree
- 62.9k GitHub stars, IBM-backed, LF AI & Data project, 193+ releases, MIT license
- Supports page number tracking via provenance (`item.prov[0].page_no`)
- The `DoclingDocument` model maps cleanly to DocMeld's Bronze JSON element list

**Alternatives considered**:
- `python-docx` (5.7k stars): Excellent .docx API but no page numbers, no chart/formula extraction, .docx only. Would require page layout calculations from OOXML properties (complex, unreliable).
- `mammoth` (v1.12.0): Good markdown conversion but outputs unstructured text — defeats the purpose of element-level extraction. No page numbers.
- `markitdown` (Microsoft, v0.1.6): Beta quality, markdown-only, no structured elements. Too early for production use.
- `unstructured` (v0.24.0): Heavy dependency tree, no page structure, requires Python 3.11+. Good for raw text but not structured pipeline.
- `textract` (v2.0.0): Text-only, wraps system tools. No tables/images/structure.

**Implementation approach**:
- Create `DocxDoclingBackend` (or extend existing `DoclingBackend` to detect file type)
- Map docling items to DocMeld element types:
  - `SectionHeaderItem` → `title`
  - `TextItem` → `text`
  - `ListItem` → `text` (prefixed with `- `)
  - `TableItem` → `table`
  - `PictureItem` → `image`
  - `PictureClassificationItem` (chart) → `chart` (data extraction) or `image` (fallback)
  - `FormulaItem` → `formula`
  - Headers/footers from document structure → `header`/`footer`
  - Footnotes/endnotes from document structure → `footnote`/`endnote`

### RQ2: What approach should be used for legacy .doc (OLE binary) files?

**Decision**: LibreOffice `soffice --headless --convert-to pdf` bridge + existing PyMuPDF backend

**Rationale**:
- No open-source Python library directly parses the OLE binary .doc format with structured element extraction
- LibreOffice is the most reliable cross-platform .doc → PDF converter
- The existing PyMuPDF backend is well-tested and handles the resulting PDF reliably
- This mirrors the architecture of established tools like `unstructured` and `textract`

**LibreOffice detection**:
```python
import shutil
libreoffice_path = shutil.which("soffice")
```

**Conversion command**:
```bash
soffice --headless --convert-to pdf --outdir <output_dir> <input.doc>
```

**Implementation approach**:
- New `SofficeBackend` class implementing `ParserBackend` protocol
- On `extract_elements()`: convert .doc → PDF via subprocess, then delegate to PyMuPDF backend
- Clean up intermediate PDF after successful bronze JSON generation
- Element types limited to what PDF extraction provides (text, table, title, image)
- Log warning about element type limitation for .doc files

**Alternatives considered**:
- `olefile` (3.3k stars): OLE container reader — would require implementing a complete Word Binary File Format parser from scratch (thousands of pages of spec, impractical)
- `antiword` / `catdoc`: Text-only, no tables/images/structure. Abandoned projects.
- `spire.doc`: Full .doc support but commercial ($999+/year). Violates open-source constitution and MIT license goals.
- `win32com`: Windows-only (requires MS Office installed). Violates cross-platform requirement.

### RQ3: How should chart data extraction work from .docx files?

**Decision**: Primary: extract structured data from chart OOXML parts. Fallback: capture chart as base64 image.

**Rationale**:
- DOCX charts store underlying data in embedded Excel worksheets within the OOXML package
- Docling provides chart detection via `PictureClassificationItem` with classification type
- Chart data can be extracted from the embedded OOXML spreadsheet parts (`xl/charts/chart1.xml`)
- When data extraction succeeds: build markdown table from chart data, classify chart type (bar/line/pie/etc.)
- When data extraction fails: fall back to image capture (same as PictureItem handling)
- This approach satisfies the clarification decision: "Both: data primary, image fallback"

**Chart type detection**:
- Parse the `c:chart` element in the chart XML to determine type: `c:barChart`, `c:lineChart`, `c:pieChart`, etc.
- Map to human-readable `chart_type` strings

### RQ4: How should formulas be extracted and represented?

**Decision**: Extract MathType/OMML → LaTeX conversion via docling's formula handling.

**Rationale**:
- DOCX stores formulas in two formats: MathType (binary OLE) and OMML (Office Math Markup Language, XML)
- Docling can detect formula items and has formula rendering capabilities
- LaTeX is the universal math representation — most downstream tools (RAG, agents) can handle it
- The `formula_type` field allows consumers to know the source format
- When LaTeX conversion fails, fall back to image capture

**Formula types**:
- `"MathType"`: Embedded binary OLE object containing MathType equation
- `"OMML"`: Native Office Math Markup Language (m:oMathPara XML)
- `"LaTeX"`: Pre-existing LaTeX (rare in .docx but possible)

### RQ5: How should the silver renderer handle the expanded element type set?

**Decision**: Add case branches to existing `render_page()` function, following the established pattern. No architectural change.

**Rationale**:
- The existing renderer is a simple dispatch function: iterate elements, switch on type, append text
- Adding new element types is straightforward case-branch addition
- Global counters for charts and formulas mirror the existing `table_counter` pattern
- Header/footer content is page-scoped (no global numbering needed)
- Footnotes use markdown's `[^N]` syntax, compatible with the existing JSONL contract
- Backward compatibility: existing PDF pipeline JSONL is unaffected (new types only appear in DOCX output)

**Counter management**:
```python
# Current signature:
def render_page(elements, title_tracker, table_counter) -> Tuple[str, int]

# Extended signature:
def render_page(elements, title_tracker, table_counter, chart_counter, formula_counter) -> Tuple[str, int, int, int]
```

---

## Dependency Impact

| Dependency | Change | Reason |
|-----------|--------|--------|
| `docling >= 2.0.0` | Already optional; no change | Existing `[docling]` extra |
| `olefile` | NOT added | No direct OLE parsing needed |
| External: `soffice` | New external dependency for .doc | Required only for legacy .doc files |
| All other deps | No change | Reuse existing stack |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docling chart/formula extraction incomplete for some .docx files | Medium | Medium | Fallback to image capture; document known limitations in quickstart |
| LibreOffice not available on user's system | Medium | Low | Clear error message; .docx-only users unaffected; check at pipeline start |
| .doc → PDF conversion fidelity loss (tables, formulas) | High | Low | .doc is P2; documented limitation; log warning |
| Performance regression for existing PDF pipeline | Low | High | PDF path completely unchanged; separate code paths; existing tests gate |
| Element type set grows beyond constitution's 4 | N/A | Low | Constitution amendment planned; MINOR version bump; backward compatible |
