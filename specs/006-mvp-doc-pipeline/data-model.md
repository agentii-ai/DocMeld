# Data Model: MVP DOC/DOCX Data Pipeline

**Feature**: `006-mvp-doc-pipeline`
**Date**: 2026-07-09

## Entity Definitions

### 1. BronzeElement (Base Class — Extended)

**Purpose**: Represents a single structural component extracted from a document page.

**Base Fields** (unchanged from 001):
- `type`: str — Element type discriminator
- `page_no`: int — Physical page number (1-indexed)
- `element_id`: str — Sequential identifier (e.g., "e_001")
- `parent_id`: str — Parent title element_id for hierarchy

**Supported Types** (expanded from 4 to 10):
```text
text, table, title, image          # Existing (PDF + DOCX + DOC)
chart, formula, header, footer,     # New (DOCX only)
footnote, endnote                   # New (DOCX only)
```

**Relationships**: Flat list structure; parent-child via `element_id`/`parent_id`

**Lifecycle**: Created during bronze stage, immutable thereafter

---

### 2. TitleElement (Unchanged)

**Fields**: type, level (0-5), content, page_no, element_id, parent_id

**Example**:
```json
{
  "type": "title",
  "level": 0,
  "content": "Executive Summary",
  "page_no": 1,
  "element_id": "e_001",
  "parent_id": ""
}
```

---

### 3. TextElement (Unchanged)

**Fields**: type, content, page_no, element_id, parent_id

**Example**:
```json
{
  "type": "text",
  "content": "The company reported strong quarterly results...",
  "page_no": 1,
  "element_id": "e_003",
  "parent_id": "e_001"
}
```

---

### 4. TableElement (Unchanged)

**Fields**: type, content (markdown table), summary, page_no, element_id, parent_id, table_data (optional struct)

**Example**:
```json
{
  "type": "table",
  "content": "| Metric | Q1 | Q2 |\n|--------|----|-----|\n| Revenue | 100 | 120 |",
  "summary": "Items: Revenue, Gross Margin, EBITDA",
  "page_no": 2,
  "element_id": "e_012",
  "parent_id": "e_005",
  "table_data": {"headers": ["Metric", "Q1", "Q2"], "rows": [["Revenue", "100", "120"]], "num_rows": 1, "num_cols": 3}
}
```

---

### 5. ImageElement (Unchanged)

**Fields**: type, image_name, content, image (base64), image_id, bbox, page_no, element_id, parent_id

---

### 6. ChartElement (NEW)

**Purpose**: Represents an embedded chart with structured data and image fallback.

**Fields**:
- `type`: Literal["chart"]
- `chart_type`: str — e.g., "bar", "line", "pie", "scatter", "area"
- `content`: str — Markdown-formatted table representing chart data (when extractable)
- `image`: str — Base64-encoded chart image (always present as fallback)
- `image_name`: str — Filename for the chart image
- `page_no`: int
- `element_id`: str
- `parent_id`: str

**Validation Rules**:
- `chart_type` must be one of: bar, line, pie, scatter, area, radar, doughnut, bubble, unknown
- `content` must be non-empty markdown table OR `image` must be valid base64

**Example**:
```json
{
  "type": "chart",
  "chart_type": "bar",
  "content": "| Quarter | Revenue |\n|---------|--------|\n| Q1 | 100 |\n| Q2 | 120 |\n| Q3 | 140 |",
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "image_name": "chart_revenue_bar.png",
  "page_no": 3,
  "element_id": "e_015",
  "parent_id": "e_008"
}
```

---

### 7. FormulaElement (NEW)

**Purpose**: Represents an embedded mathematical formula.

**Fields**:
- `type`: Literal["formula"]
- `content`: str — LaTeX string representation
- `formula_type`: str — "MathType", "OMML", or "LaTeX"
- `page_no`: int
- `element_id`: str
- `parent_id`: str

**Validation Rules**:
- `content` must be non-empty
- `formula_type` must be one of: MathType, OMML, LaTeX

**Example**:
```json
{
  "type": "formula",
  "content": "E = mc^2",
  "formula_type": "MathType",
  "page_no": 4,
  "element_id": "e_020",
  "parent_id": "e_018"
}
```

---

### 8. HeaderElement (NEW)

**Purpose**: Represents a page header.

**Fields**:
- `type`: Literal["header"]
- `content`: str — Header text content
- `page_scope`: str — "all", "even", or "odd" (which pages this header applies to)
- `page_no`: int
- `element_id`: str
- `parent_id`: str

**Validation Rules**:
- `content` must be non-empty
- `page_scope` must be one of: all, even, odd

**Example**:
```json
{
  "type": "header",
  "content": "Chapter 3: Financial Analysis",
  "page_scope": "all",
  "page_no": 15,
  "element_id": "e_025",
  "parent_id": ""
}
```

---

### 9. FooterElement (NEW)

**Purpose**: Represents a page footer.

**Fields**:
- `type`: Literal["footer"]
- `content`: str — Footer text content
- `page_scope`: str — "all", "even", or "odd"
- `page_no`: int
- `element_id`: str
- `parent_id`: str

**Example**:
```json
{
  "type": "footer",
  "content": "Page 15",
  "page_scope": "all",
  "page_no": 15,
  "element_id": "e_026",
  "parent_id": ""
}
```

---

### 10. FootnoteElement (NEW)

**Purpose**: Represents a footnote (bottom of page note).

**Fields**:
- `type`: Literal["footnote"]
- `content`: str — Footnote text
- `reference_id`: str — The footnote reference marker (e.g., "1", "*")
- `page_no`: int — The page where the footnote reference appears
- `element_id`: str
- `parent_id`: str

**Example**:
```json
{
  "type": "footnote",
  "content": "Source: Annual Report 2024, Section 3.2",
  "reference_id": "1",
  "page_no": 7,
  "element_id": "e_035",
  "parent_id": ""
}
```

---

### 11. EndnoteElement (NEW)

**Purpose**: Represents an endnote (document-end note).

**Fields**: Same structure as FootnoteElement
- `type`: Literal["endnote"]

---

### 12. SilverPage (Unchanged)

**Fields**: metadata (uuid, source, page_no, session_title), page_content

**Note**: `page_content` now includes extended marker syntax for charts, formulas, headers, footers, footnotes.

---

### 13. GoldPage (Unchanged)

**Additional Fields**: metadata.description, metadata.keywords, metadata.gold_processing_failed (optional)

---

### 14. ProcessingResult (Unchanged)

**Fields**: total_files, successful, failed, failures, processing_time_seconds, output_directory, log_file

---

## BronzeElement Union Type (Python)

```python
from typing import Union

BronzeElement = Union[
    TitleElement, TextElement, TableElement, ImageElement,     # Existing
    ChartElement, FormulaElement,                              # New
    HeaderElement, FooterElement,                              # New
    FootnoteElement, EndnoteElement                            # New
]
```

## State Transitions

### Bronze Stage — DOCX Path
```
.docx File → [DoclingBackend] → List[BronzeElement (10 types)] → [Post-process] → {filename_hash6}.json
```

### Bronze Stage — DOC Path
```
.doc File → [soffice --convert-to pdf] → Intermediate PDF → [PyMuPDFBackend] → List[BronzeElement (4 types)] → [Post-process] → {filename_hash6}.json
```

### Silver Stage (Unchanged flow, extended renderer)
```
{filename_hash6}.json → [Load] → List[BronzeElement] → [Group by page_no + extended render] → List[SilverPage] → {filename_hash6}.jsonl
```

### Gold Stage (Unchanged)
```
{filename_hash6}.jsonl → [DeepSeek enrichment] → {filename_hash6}_gold.jsonl
```

## Data Volume Estimates

**Bronze JSON (.docx, 50-page document)**:
- Elements per page: 10-30 (richer than PDF due to headers/footers/footnotes)
- 50-page document: ~700 elements, ~3MB JSON
- Larger than PDF due to header/footer elements on every page

**Bronze JSON (.doc, 50-page document)**:
- Same as PDF: ~500 elements, ~2MB JSON

**Silver/Gold JSONL**:
- Same order of magnitude as PDF pipeline (additional element markers add minor overhead)
