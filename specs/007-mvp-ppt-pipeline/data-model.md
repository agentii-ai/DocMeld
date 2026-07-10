# Data Model: MVP PPT/PPTX Data Pipeline

**Feature**: `007-mvp-ppt-pipeline`
**Date**: 2026-07-09

## Entity Definitions

### 1. BronzeElement (Base Class — Extended)

**Purpose**: A single structural component extracted from a slide.

**Base Fields** (unchanged from 001/006):
- `type`: str — Element type discriminator
- `page_no`: int — Physical slide number (1-indexed, continuous including hidden slides)
- `element_id`: str — Sequential identifier (e.g., "e_001")
- `parent_id`: str — Parent element_id (title hierarchy, or group for child shapes)

**New optional field** (all element types):
- `hidden`: bool — True when the element belongs to a hidden slide (default false)

**Supported Types** (14 total; PPT emits the subset noted):
```text
text, table, title, image          # Existing (PDF + DOCX + DOC + PPTX)
chart, formula                      # Existing (DOCX + PPTX)
header, footer, footnote, endnote   # Existing (DOCX); PPT emits footer only
smartart, notes, group, comment     # NEW (PPTX)
```

**Relationships**: Flat list; parent-child via `element_id`/`parent_id` (group→child shapes, title→content).

**Lifecycle**: Created during bronze stage, immutable thereafter.

---

### 2–5. TitleElement / TextElement / TableElement / ImageElement (Unchanged)

Same fields as 001/006. Title has `level` (0-based; 0=slide title, 1=subtitle). Text has `content` (hyperlinks preserved inline as `[text](url)`). Table has `content` (markdown) + `summary`. Image has `image_name`, `content`, `image` (base64), `image_id`, `bbox`.

---

### 6–7. ChartElement / FormulaElement (Unchanged from 006)

- **ChartElement**: `chart_type` (bar/line/pie/scatter/area/…), `content` (markdown data table), `image` (base64 fallback), `image_name`
- **FormulaElement**: `content` (LaTeX), `formula_type` (MathType/OMML/LaTeX)

---

### 8. FooterElement (Reused)

**Fields**: type=`footer`, `content`, `page_scope` (all/even/odd; PPT typically "all"), `page_no`, `element_id`, `parent_id`

---

### 9. SmartArtElement (NEW)

**Purpose**: A SmartArt (DrawingML Diagram) shape with extracted hierarchical text.

**Fields**:
- `type`: Literal["smartart"]
- `smartart_type`: str — "process", "cycle", "hierarchy", "relationship", "pyramid", "list", "unknown"
- `content`: str — Hierarchical markdown text extracted from the diagram data
- `image`: str — Base64-encoded SmartArt rendering (fallback; may be empty)
- `image_name`: str
- `page_no`, `element_id`, `parent_id`, `hidden`

**Validation**: `content` non-empty OR `image` valid base64.

**Example**:
```json
{
  "type": "smartart",
  "smartart_type": "process",
  "content": "- Plan\n- Build\n- Ship",
  "image": "",
  "image_name": "smartart_process_1.png",
  "page_no": 3,
  "element_id": "e_015",
  "parent_id": "e_008",
  "hidden": false
}
```

---

### 10. NotesElement (NEW)

**Purpose**: Speaker notes attached to a slide.

**Fields**:
- `type`: Literal["notes"]
- `content`: str — Plain-markdown notes text (bullets/hyperlinks preserved)
- `page_no`: int — Parent slide number
- `element_id`, `parent_id`, `hidden`

**Ordering rule**: Notes elements are emitted **after** all content elements of their slide (FR-018).

**Example**:
```json
{
  "type": "notes",
  "content": "Emphasize the 40% YoY growth here.",
  "page_no": 3,
  "element_id": "e_030",
  "parent_id": "",
  "hidden": false
}
```

---

### 11. GroupElement (NEW)

**Purpose**: A container for grouped shapes; children extracted separately.

**Fields**:
- `type`: Literal["group"]
- `content`: str — Short description of the group
- `child_count`: int — Number of grouped child shapes
- `page_no`, `element_id`, `parent_id`, `hidden`

**Relationship**: Each child shape is a separate element with `parent_id` = this group's `element_id`.

**Example**:
```json
{
  "type": "group",
  "content": "Grouped diagram (3 shapes)",
  "child_count": 3,
  "page_no": 4,
  "element_id": "e_040",
  "parent_id": "",
  "hidden": false
}
```

---

### 12. CommentElement (NEW)

**Purpose**: An author-attributed reviewer comment anchored to a slide.

**Fields**:
- `type`: Literal["comment"]
- `content`: str — Comment text
- `author`: str — Comment author (empty string when not recorded)
- `page_no`: int — Anchored slide number
- `element_id`, `parent_id`, `hidden`

**Example**:
```json
{
  "type": "comment",
  "content": "Update this figure for FY25.",
  "author": "A. Reviewer",
  "page_no": 2,
  "element_id": "e_050",
  "parent_id": "",
  "hidden": false
}
```

---

### 13–15. SilverPage / GoldPage / ProcessingResult (Unchanged)

- **SilverPage**: `metadata` (uuid, source, `page_no` = "page1", session_title), `page_content` (markdown with extended markers)
- **GoldPage**: adds `metadata.description`, `metadata.keywords`, optional `metadata.gold_processing_failed`
- **ProcessingResult**: total_files, successful, failed, failures, processing_time_seconds, output_directory, log_file

---

## BronzeElement Union Type (Python)

```python
from typing import Union

BronzeElement = Union[
    TitleElement, TextElement, TableElement, ImageElement,   # Existing
    ChartElement, FormulaElement,                            # Existing
    HeaderElement, FooterElement,                            # Existing (PPT: footer only)
    FootnoteElement, EndnoteElement,                         # Existing (PPT: none)
    SmartArtElement, NotesElement, GroupElement, CommentElement,  # NEW (PPTX)
]
```

## State Transitions

### Bronze Stage — PPTX Path
```
.pptx File → [PptxBackend: python-pptx + docling assist] → List[BronzeElement (11 PPT types)] → [Post-process: hybrid sort, hidden flag] → {filename_hash6}.json
```

### Bronze Stage — PPT Path
```
.ppt File → [soffice --convert-to pdf] → Intermediate PDF → [PyMuPDFBackend] → List[BronzeElement (4 types)] → [delete intermediate PDF] → {filename_hash6}.json
```

### Silver Stage (Unchanged flow, extended renderer)
```
{filename_hash6}.json → [Load] → List[BronzeElement] → [Group by page_no (slide) + extended render] → List[SilverPage] → {filename_hash6}.jsonl
```

### Gold Stage (Unchanged)
```
{filename_hash6}.jsonl → [DeepSeek enrichment] → {filename_hash6}_gold.jsonl
```

## Data Volume Estimates

**Bronze JSON (.pptx, 30-slide deck)**: 8-25 elements/slide (text-heavy decks fewer, diagram-heavy more) → ~400 elements, ~2-4MB JSON (base64 images/charts dominate size).

**Bronze JSON (.ppt, 30-slide deck)**: 4-type output, ~200 elements, ~1-2MB.

**Silver/Gold JSONL**: One line per slide; same order of magnitude as PDF/DOC pipelines.
