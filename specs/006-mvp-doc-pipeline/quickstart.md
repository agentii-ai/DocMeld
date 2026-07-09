# Quickstart: DOC/DOCX Pipeline

**Feature**: `006-mvp-doc-pipeline`
**Date**: 2026-07-09

## Prerequisites

- Python 3.9+
- `pip install docmeld` (base install, supports .doc via LibreOffice bridge)
- `pip install docmeld[docling]` (recommended — enables native .docx parsing with full element types)
- LibreOffice (optional, required only for legacy .doc files): `brew install libreoffice` (macOS) / `apt install libreoffice` (Linux)

## Quickstart (Library)

```python
from docmeld import DocMeldParser

# Process a .docx file (full 10 element types via docling)
parser = DocMeldParser("/path/to/report.docx", backend="auto")
result = parser.process_all()
print(f"Done: {result.successful}/{result.total_files} files")
print(f"Time: {result.processing_time_seconds}s")

# Process a legacy .doc file (4 element types via LibreOffice → PDF → PyMuPDF)
parser = DocMeldParser("/path/to/legacy_report.doc", backend="auto")
bronze = parser.process_bronze()
print(f"Elements: {bronze.element_count}, Pages: {bronze.page_count}")
print(f"Output: {bronze.output_path}")
```

## Quickstart (CLI)

```bash
# Full pipeline on a single .docx file
docmeld process /path/to/report.docx --backend auto

# Bronze-only extraction
docmeld bronze /path/to/folder/ --backend docling

# Silver: JSON → page-by-page JSONL
docmeld silver /path/to/report_a3f5c2/report_a3f5c2.json

# Gold: enrich with AI metadata
docmeld gold /path/to/report_a3f5c2/report_a3f5c2.jsonl
```

## Element Types Available

| Backend | Format | Element Types |
|---------|--------|--------------|
| `docling` (auto for .docx) | .docx | text, table, title, image, chart, formula, header, footer, footnote, endnote |
| `pymupdf` (auto for .doc) | .doc (via LibreOffice → PDF) | text, table, title, image |

## Output Structure

```
/path/to/
├── report_a3f5c2.docx              # Hashed copy of source
├── report_a3f5c2/
│   ├── report_a3f5c2.json          # Bronze: structured element list
│   ├── report_a3f5c2.jsonl         # Silver: page-by-page JSONL
│   └── report_a3f5c2_gold.jsonl    # Gold: AI-enriched JSONL
```

## Sample .docx Element Output

```json
[
  {"type": "title", "level": 0, "content": "Executive Summary", "page_no": 1, "element_id": "e_001", "parent_id": ""},
  {"type": "text", "content": "The company achieved record revenue in Q3 2024.", "page_no": 1, "element_id": "e_002", "parent_id": "e_001"},
  {"type": "chart", "chart_type": "bar", "content": "| Quarter | Revenue |\n|---------|--------|\n| Q1 | 100 |\n| Q2 | 120 |", "image": "iVBORw0KGgo...", "image_name": "chart_001.png", "page_no": 2, "element_id": "e_010", "parent_id": "e_005"},
  {"type": "formula", "content": "E = mc^2", "formula_type": "MathType", "page_no": 2, "element_id": "e_011", "parent_id": "e_005"},
  {"type": "header", "content": "Confidential — Q3 2024 Report", "page_scope": "all", "page_no": 3, "element_id": "e_012", "parent_id": ""},
  {"type": "footer", "content": "Page 3 of 15", "page_scope": "all", "page_no": 3, "element_id": "e_013", "parent_id": ""},
  {"type": "footnote", "content": "Source: Internal financial data, audited by Deloitte.", "reference_id": "1", "page_no": 3, "element_id": "e_014", "parent_id": ""}
]
```

## Sample Silver JSONL Output

```jsonl
{"metadata": {"uuid": "...", "source": "report_a3f5c2.docx", "page_no": "page2", "session_title": "# Executive Summary\n## Financial Performance"}, "page_content": "## Financial Performance\n\nThe company achieved record revenue...\n\n[[Chart1]]\n| Quarter | Revenue |\n|---------|--------|\n| Q1 | 100 |\n\n[/Chart1]\n\n[[Formula1]]\nE = mc^2\n[/Formula1]"}
```

## Backend Selection Guide

| Flag | Behavior |
|------|----------|
| `--backend auto` (default) | Detect format by file extension: .docx → docling, .doc → soffice |
| `--backend docling` | Force docling backend (fails for .doc files) |
| `--backend pymupdf` | Force PyMuPDF via LibreOffice conversion (.doc or .docx → convert → PDF → PyMuPDF) |

## Limitations

- **.doc files**: Limited to 4 element types (text, table, title, image) due to PDF conversion. Charts, formulas, headers, footers, footnotes are not individually typed in .doc output.
- **Password-protected .docx**: Skipped with error. Not supported.
- **Embedded OLE objects**: Logged as warnings, not individually extracted. The document content around them is still processed.
- **Tracked changes**: Processed in final (accepted) state. A warning is logged recommending changes be accepted before processing.

## Sample Files

The `samples/` directory contains test fixtures for development and validation:

| File | Tests |
|------|-------|
| `sample_tables.docx` | Multi-row + single-row tables |
| `sample_lists.docx` | Bullet, numbered, nested lists |
| `sample_headers_footers.docx` | Headers + page number footers across 3 pages |
| `sample_images.docx` | Embedded PNG image extraction |
| `sample_multipage.docx` | Title hierarchy (H1→H2) across 3 pages |
| `sample3.docx` | Real-world Chinese document |

These samples replicate categories from the WIPO PCT DocConverter sample page (30 curated .docx test documents covering all common Word features). Use them as TDD fixtures: write a failing test with the sample, implement the feature, verify green.
