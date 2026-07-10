# Quickstart: MVP PowerPoint Data Pipeline

**Feature**: `007-mvp-ppt-pipeline`
**Date**: 2026-07-09

## Installation

```bash
# Core installation (PyMuPDF only — PDF + .ppt bridge work out of the box)
pip install docmeld

# With PPTX support
pip install docmeld[pptx]

# With all office formats (.docx, .pptx)
pip install docmeld[office]
```

## Quick Example

```python
from docmeld import DocMeldParser

# Parse a single .pptx file through all three stages
parser = DocMeldParser()
result = parser.process("presentations/pitch_deck.pptx")

# Output is in pitch_deck_a3f5c2/
print(result.output_directory)  # pitch_deck_a3f5c2/
print(result.successful)        # 1 (or 0 if failed)
```

## Output Files

For a file `pitch_deck.pptx` with MD5 hash `a3f5c2...`:

```text
pitch_deck_a3f5c2/
├── pitch_deck_a3f5c2.pptx   # sanitized copy
├── pitch_deck_a3f5c2.json   # bronze: full element list (11 element types)
├── pitch_deck_a3f5c2.jsonl  # silver: one line per slide
└── pitch_deck_a3f5c2_gold.jsonl  # gold: AI-enriched metadata per slide
```

## Example Bronze JSON (single element)

```json
{
  "type": "chart",
  "chart_type": "bar",
  "content": "| Quarter | Revenue |\n|---------|--------|\n| Q1 | 100 |\n| Q2 | 120 |",
  "image": "iVBORw0KGgo...",
  "image_name": "chart_revenue_bar.png",
  "page_no": 3,
  "element_id": "e_015",
  "parent_id": "e_008",
  "hidden": false
}
```

## Example Silver JSONL (single slide)

```json
{"metadata": {"uuid": "...", "source": "pitch_deck_a3f5c2.pptx", "page_no": "page3", "session_title": "# Q4 Review"}, "page_content": "## Revenue Analysis\n[[Chart1]]\n| Quarter | Revenue |\n|---------|--------|\n| Q1 | 100 |\n| Q2 | 120 |\n[[/Chart1]]\n[Notes]\nEmphasize the 40% YoY growth here.\n[/Notes]\n[Comment: A. Reviewer]\nUpdate this figure for FY25.\n[/Comment]"}
```

## CLI Usage

```bash
# Process a single .pptx (default: pptx backend)
docmeld bronze "path/to/pitch_deck.pptx"

# Process a folder of presentations (auto-detect format)
docmeld bronze "path/to/folder/" --backend auto

# Full pipeline: bronze → silver → gold
docmeld process "path/to/pitch_deck.pptx" --backend pptx

# Force PyMuPDF backend (for .ppt via LibreOffice)
docmeld bronze "path/to/legacy.ppt" --backend pymupdf
```

## Backend Selection

| Flag | Formats | Element Types | Require LibreOffice? |
|------|---------|---------------|---------------------|
| `--backend pptx` | .pptx | up to 11 PPTX types | No |
| `--backend pymupdf` | .ppt (via soffice) | 4 (text, table, title, image) | Yes (for .ppt only) |
| `--backend auto` | auto-detect by extension | per format | Only for .ppt |

## Tips

- **Speaker notes**: Extracted from each slide's `notes_slide`; appear after slide content with `[Notes]` markers.
- **Comments**: Full author attribution preserved; rendered as `[Comment: author]`.
- **Charts**: Data extracted when available (markdown table); image fallback always included.
- **SmartArt**: Text extracted hierarchically from diagram data; image fallback when text unavailable.
- **Hidden slides**: Extracted fully with `"hidden": true` on all their elements; continuous slide numbering.
- **Hyperlinks**: Preserved inline as markdown `[text](url)` within text element content.
- **Legacy .ppt**: Requires LibreOffice installed; generates intermediate PDF (auto-deleted).
