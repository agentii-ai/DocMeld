<p align="center">
  <img src="docmeld/assets/banner.png" alt="DocMeld Banner" width="100%">
</p>

<h1 align="center">DocMeld</h1>
<p align="center">Lightweight Doc to agent-ready knowledge pipeline</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black"></a>
  <a href="https://docs.astral.sh/ruff/"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://mypy-lang.org/"><img src="https://img.shields.io/badge/type%20checked-mypy-blue.svg" alt="Checked with mypy"></a>
  <img src="https://img.shields.io/badge/tests-315%20passed-brightgreen.svg" alt="Tests: 315 passed">
  <img src="https://img.shields.io/badge/coverage-78%25-green.svg" alt="Coverage: 78%">
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#pipeline-architecture">Architecture</a> •
  <a href="#python-api">Python API</a> •
  <a href="#cli-reference">CLI</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#contributing">Contributing</a>
</p>

---

DocMeld converts PDF, Word, and PowerPoint documents into structured, agent-consumable formats through a three-stage pipeline — without requiring expensive OCR, VLM, or multimodal models. Built for the age of AI agents, it bridges the gap between static documents and the structured knowledge that LLMs need.

**Supported formats**: `.pdf`, `.docx`, `.doc` (via LibreOffice), `.pptx`, `.ppt` (via LibreOffice).

```bash
# PowerPoint support
pip install docmeld[pptx]      # .pptx via python-pptx
pip install docmeld[office]    # .docx + .pptx
```

Most tools stop at format conversion. DocMeld goes further: **Document → Structured Elements → Page Knowledge → AI-Enriched Metadata**, producing outputs ready for RAG pipelines, agent systems, and downstream AI workflows.

## Why DocMeld?

| | DocMeld | MinerU | Docling | Marker | MarkItDown |
|---|---|---|---|---|---|
| No ML models required | ✅ | ❌ | ❌ | ❌ | ✅ |
| Runs fully offline (core) | ✅ | ❌ | ✅ | ✅ | ✅ |
| Agent-ready outputs | ✅ | ❌ | ❌ | ❌ | ❌ |
| AI metadata enrichment | ✅ | ❌ | ❌ | ❌ | ❌ |
| Lightweight install | ✅ | ❌ | ❌ | ❌ | ✅ |
| MIT license | ✅ | ❌ (AGPL) | ✅ | ❌ (GPL) | ✅ |
| Swappable backends | ✅ | ❌ | N/A | ❌ | ❌ |

## Quick Start

### Installation

```bash
pip install docmeld
```

With optional Docling backend:

```bash
pip install docmeld[docling]
```

### Process your first PDF

```python
from docmeld import DocMeldParser

parser = DocMeldParser("research_paper.pdf")
result = parser.process_all()
print(f"Processed {result.successful}/{result.total_files} files in {result.processing_time_seconds}s")
```

Or from the command line:

```bash
docmeld process research_paper.pdf
```

That's it. Your PDF is now structured JSON, page-by-page JSONL, and (optionally) AI-enriched metadata.

## Pipeline Architecture

DocMeld uses a three-stage medallion architecture. Each stage is independently runnable and idempotent — re-running skips already-processed files.

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   BRONZE    │      │   SILVER    │      │    GOLD     │
│             │      │             │      │             │
│  PDF → JSON │─────▶│ JSON → JSONL│─────▶│ JSONL → AI  │
│  elements   │      │  pages      │      │  metadata   │
│             │      │             │      │             │
│  PyMuPDF /  │      │  Title      │      │  DeepSeek   │
│  Docling    │      │  hierarchy  │      │  enrichment │
└─────────────┘      └─────────────┘      └─────────────┘
   offline              offline            requires API key
```

### Bronze: PDF → Structured JSON

Extracts document elements (titles, text, tables, images) into a unified JSON format with element IDs and parent-child hierarchy.

```json
[
  {
    "type": "title",
    "level": 0,
    "content": "Executive Summary",
    "page_no": 1,
    "element_id": "e_001",
    "parent_id": ""
  },
  {
    "type": "text",
    "content": "The company reported strong Q2 results...",
    "page_no": 1,
    "element_id": "e_002",
    "parent_id": "e_001"
  },
  {
    "type": "table",
    "content": "| Metric | Q1 | Q2 |\n|---|---|---|\n| Revenue | 10M | 15M |",
    "summary": "Items: Revenue",
    "page_no": 2,
    "element_id": "e_003",
    "parent_id": "e_001",
    "table_data": {
      "headers": ["Metric", "Q1", "Q2"],
      "rows": [["Revenue", "10M", "15M"]],
      "num_rows": 1,
      "num_cols": 3
    }
  }
]
```

Supported element types:

| Type | Fields | Description |
|---|---|---|
| `title` | `level`, `content` | Headings with hierarchy (0–5) |
| `text` | `content` | Paragraph content |
| `table` | `content`, `summary`, `table_data` | Markdown tables with structured data |
| `image` | `image_name`, `image`, `bbox`, `image_id` | Base64-encoded images with metadata |
| `chart` | `chart_type`, `content`, `image` | Chart data as markdown table + image fallback |
| `formula` | `content`, `formula_type` | LaTeX/OMML formulas |
| `smartart` | `smartart_type`, `content`, `image` | SmartArt diagram text (PPTX) |
| `notes` | `content` | Speaker notes (PPTX) |
| `group` | `content`, `child_count` | Grouped shapes (PPTX) |
| `comment` | `content`, `author` | Reviewer comments (PPTX) |
| `header`/`footer` | `content`, `page_scope` | Page/slide margins |
| `footnote`/`endnote` | `content`, `reference_id` | Document notes |

All elements include `page_no`, `element_id`, and `parent_id` for cross-referencing.

### Silver: JSON → Page-by-Page JSONL

Transforms flat element lists into self-contained page documents with title hierarchy tracking, markdown rendering, and global table numbering.

```json
{
  "metadata": {
    "uuid": "a1b2c3d4-...",
    "source": "research_paper.pdf",
    "page_no": "page1",
    "session_title": "# Executive Summary\n"
  },
  "page_content": "# Executive Summary\n\nThe company reported strong Q2 results...\n\n[[Table1]]\n| Metric | Q1 | Q2 |\n|---|---|---|\n| Revenue | 10M | 15M |\n[/Table1]"
}
```

Each page carries its full title context, so pages are independently meaningful — ideal for chunked retrieval in RAG systems.

### Gold: JSONL → AI-Enriched Metadata

Adds semantic descriptions and keywords to each page using DeepSeek-chat, with exponential backoff retry and per-page error resilience.

```json
{
  "metadata": {
    "uuid": "a1b2c3d4-...",
    "source": "research_paper.pdf",
    "page_no": "page1",
    "session_title": "# Executive Summary\n",
    "description": "Company reports strong Q2 results with 50% revenue growth",
    "keywords": ["revenue", "quarterly results", "growth", "financial performance"]
  },
  "page_content": "..."
}
```

The gold stage is optional — bronze and silver run fully offline with zero API calls.

### Knowledge Generation (v0.3.1+)

Beyond per-page enrichment, DocMeld can generate structured, agent-ready artifacts from document content using an LLM provider:

| Feature | CLI | Python API | Output |
|---------|-----|-----------|--------|
| **Categorize** | `docmeld categorize papers/` | `parser.process_categorize()` | Topic clusters + `categories.json` |
| **PRD Generator** | `docmeld prd paper.pdf` | `parser.process_prd()` | Product Requirements Document (`.md`) |
| **Workflow** | `docmeld workflow paper.pdf` | `parser.process_workflow()` | Step-by-step implementation workflow (`.md`) |
| **Skills** | `docmeld skills book.pdf` | `parser.process_skills()` | Claude Code skill files (`_skills/`) |

All four features support swappable LLM backends via the provider injection seam (see below).

## Output Structure

After processing `research_paper.pdf`:

```
research_paper.pdf                              # Original (untouched)
research_paper_a3f5c2/                          # Output folder (name + MD5 suffix)
├── research_paper_a3f5c2.json                  # Bronze: structured elements
├── research_paper_a3f5c2.jsonl                 # Silver: page-by-page documents
└── research_paper_a3f5c2_gold.jsonl            # Gold: AI-enriched (optional)
```

Output folder names are sanitized and include an MD5 hash suffix for uniqueness, ensuring safe cross-platform filenames even for PDFs with unicode or special characters.

## Python API

### Full Pipeline

```python
from docmeld import DocMeldParser

# Single file — all three stages
parser = DocMeldParser("paper.pdf")
result = parser.process_all()

# Batch — process every PDF in a folder
parser = DocMeldParser("/path/to/papers/")
result = parser.process_all()
print(f"{result.successful}/{result.total_files} files, {result.processing_time_seconds}s")
```

### Individual Stages

```python
from docmeld import DocMeldParser

parser = DocMeldParser("paper.pdf")

# Bronze only
bronze = parser.process_bronze()
print(f"{bronze.element_count} elements across {bronze.page_count} pages")
print(f"Output: {bronze.output_path}")

# Silver (requires bronze output)
silver = parser.process_silver(bronze.output_path)
print(f"{silver.page_count} pages → {silver.output_path}")

# Gold (requires silver output + API key)
gold = parser.process_gold(silver.output_path)
print(f"{gold.pages_enriched} enriched, {gold.pages_failed} failed")
```

### Swappable Backends

DocMeld supports multiple parsing backends through a pluggable architecture. With `--backend auto` (the default), the format is detected from the file extension and routed automatically:

```python
# Default: auto-detect by file extension (recommended)
parser = DocMeldParser("deck.pptx", backend="auto")

# PDF: PyMuPDF (lightweight, fast)
parser = DocMeldParser("paper.pdf", backend="pymupdf")

# DOCX: Docling (IBM's ML-powered OOXML parser)
parser = DocMeldParser("report.docx", backend="docling")

# PPTX: python-pptx — native slide/shape extraction
parser = DocMeldParser("deck.pptx", backend="pptx")

# Legacy .doc / .ppt: LibreOffice bridge
parser = DocMeldParser("old.ppt", backend="soffice")
```

| Backend | Formats | Requires |
|----------|---------|----------|
| `pymupdf` | `.pdf` | core install |
| `docling` | `.docx`, `.pdf` | `docmeld[docling]` |
| `pptx` | `.pptx` | `docmeld[pptx]` |
| `soffice` | `.doc`, `.ppt` | LibreOffice on PATH |
| `auto` | all of the above | per-format |

### Working with Elements

```python
import json

# Load bronze output
with open("paper_a3f5c2/paper_a3f5c2.json") as f:
    elements = json.load(f)

# Filter by type
titles = [e for e in elements if e["type"] == "title"]
tables = [e for e in elements if e["type"] == "table"]

# Navigate hierarchy via parent_id
for elem in elements:
    if elem["parent_id"] == "e_001":
        print(f"  Child of first title: {elem['content'][:50]}")

# Access structured table data
for table in tables:
    headers = table["table_data"]["headers"]
    rows = table["table_data"]["rows"]
    print(f"Table: {len(rows)} rows × {len(headers)} cols")
```

### Knowledge Generation

```python
from docmeld import DocMeldParser

# Categorize papers into topic clusters
parser = DocMeldParser("/path/to/papers/")
result = parser.process_categorize(reorganize=False)
print(f"{result.total_categories} categories from {result.total_papers} papers")

# Generate a PRD from a research paper
parser = DocMeldParser("paper.pdf")
prd = parser.process_prd()
print(f"PRD: {prd.output_path} ({prd.sections} sections)")

# Extract a workflow from a paper
wf = parser.process_workflow()
print(f"Workflow: {wf.output_path} ({wf.sections} sections)")

# Extract Claude Code skills from a book
skills = parser.process_skills()
print(f"{skills.skill_count} skills → {skills.output_dir}")
```

### Swappable LLM Provider

Inject any LLM backend that implements the `LLMProvider` Protocol:

```python
from docmeld import DocMeldParser
from docmeld.gold.provider import LLMProvider

class MyProvider:
    def extract_metadata(self, content: str) -> dict: ...
    def generate(self, prompt: str) -> str: ...
    def categorize(self, prompt: str) -> str: ...

parser = DocMeldParser("paper.pdf", provider=MyProvider())
# All gold-stage and knowledge-generation features now use MyProvider
prd = parser.process_prd()  # uses your provider, not DeepSeek
```

When no provider is given, a `DeepSeekClient` is constructed from `DEEPSEEK_API_KEY` — byte-for-byte identical to the previous behavior.

### Result Models

All pipeline stages return typed Pydantic models:

```python
BronzeResult(output_path, output_dir, element_count, page_count, skipped)
SilverResult(output_path, page_count, skipped)
GoldResult(output_path, pages_enriched, pages_failed, skipped)
ProcessingResult(total_files, successful, failed, failures, processing_time_seconds, ...)
CategorizeResult(index_path, total_papers, total_categories, papers_failed, reorganized)
PrdResult(output_path, sections, source_pdf, skipped)
WorkflowResult(output_path, sections, source_pdf, skipped)
SkillsResult(output_dir, skill_count, source_pdf, skipped)
```

## CLI Reference

```bash
# Full pipeline (bronze → silver → gold)
docmeld process paper.pdf
docmeld process /path/to/papers/

# Individual stages
docmeld bronze paper.pdf                    # PDF → JSON
docmeld silver paper_a3f5c2/paper_a3f5c2.json    # JSON → JSONL
docmeld gold paper_a3f5c2/paper_a3f5c2.jsonl     # JSONL → enriched JSONL

# Choose parsing backend (pymupdf|docling|pptx|soffice|auto, default: auto)
docmeld bronze paper.pdf --backend docling
docmeld process deck.pptx --backend auto

# Knowledge Generation (requires DEEPSEEK_API_KEY)
docmeld categorize /path/to/papers/               # Topic clustering + categories.json
docmeld categorize /path/to/papers/ --reorganize  # Move files into category folders
docmeld prd paper.pdf                             # Generate Product Requirements Document
docmeld workflow paper.pdf                        # Extract step-by-step workflow
docmeld skills book.pdf                           # Extract Claude Code skills
```

## Configuration

### Gold Stage (AI Enrichment)

Create a `.env.local` file in your working directory:

```bash
DEEPSEEK_API_KEY=your_key_here

# Optional: custom API endpoint
# DEEPSEEK_API_ENDPOINT=https://api.deepseek.com
```

The gold stage is entirely optional. Bronze and silver stages run offline with no API keys, no network calls, and no model downloads.

### Logging

DocMeld writes timestamped log files (`docmeld_YYYYMMDD_HHMMSS.log`) to the working directory. Console output shows INFO-level messages; log files capture full DEBUG output.

## Unified Element Schema

DocMeld enforces a strict element schema via Pydantic models. This contract guarantees downstream consumers always get a predictable structure.

```python
from docmeld.bronze.element_types import (
    TitleElement,    # type, level, content, page_no, element_id, parent_id
    TextElement,     # type, content, page_no, element_id, parent_id
    TableElement,    # type, content, summary, page_no, element_id, parent_id, table_data
    ImageElement,    # type, image_name, content, image, image_id, bbox, page_no, element_id, parent_id
)
```

Element types are validated at creation time. New types may be added in minor versions, but existing types will never change shape in minor/patch releases.

## Roadmap

- [x] Bronze → Silver → Gold pipeline
- [x] CLI interface with subcommands
- [x] Swappable backends (PyMuPDF + Docling)
- [x] Element hierarchy (`element_id` / `parent_id`)
- [x] Structured table data extraction
- [x] Idempotent processing
- [x] Batch folder processing
- [x] Research paper batch categorization + topic clustering
- [x] Paper-to-PRD generation
- [x] Paper-to-workflow extraction
- [x] Book-to-Claude-Skills generation
- [x] DOCX support
- [x] PPTX / PPT support
- [x] Swappable LLM provider (bring your own backend)
- [ ] OCR for scanned PDFs (`pip install docmeld[ocr]`)
- [ ] Agent prompt generation
- [ ] LangChain / LlamaIndex integration

## Development

### Setup

```bash
git clone https://github.com/agentii-ai/DocMeld.git
cd docmeld
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Quality Gates

```bash
pytest tests/ -v --cov=docmeld       # 315 tests, 78% coverage
ruff check docmeld/                   # Linting
black --check docmeld/                # Formatting
mypy docmeld/                         # Strict type checking
```

### Project Structure

```
docmeld/
├── docmeld/
│   ├── __init__.py              # Public API (DocMeldParser, __version__)
│   ├── parser.py                # Pipeline orchestrator
│   ├── cli.py                   # CLI entry point (argparse)
│   ├── py.typed                 # PEP 561 marker
│   ├── bronze/
│   │   ├── backends/
│   │   │   ├── pymupdf_backend.py   # PyMuPDF + pymupdf4llm
│   │   │   ├── docling_backend.py   # Docling (optional, DOCX/PDF)
│   │   │   ├── pptx_backend.py      # python-pptx (PPTX)
│   │   │   └── soffice_backend.py   # LibreOffice bridge (.doc/.ppt)
│   │   ├── element_extractor.py     # Extraction + post-processing
│   │   ├── element_types.py         # Pydantic element models (14 types)
│   │   ├── filename_sanitizer.py    # Safe filenames + MD5 hashing
│   │   └── processor.py            # Bronze orchestrator
│   ├── silver/
│   │   ├── page_aggregator.py       # Group elements by page
│   │   ├── page_models.py          # Result models (Pydantic)
│   │   ├── markdown_renderer.py     # Elements → markdown
│   │   ├── title_tracker.py         # Title hierarchy state
│   │   └── processor.py            # Silver orchestrator
│   ├── gold/
│   │   ├── deepseek_client.py       # DeepSeek API client + retry
│   │   ├── provider.py              # LLMProvider Protocol (swappable)
│   │   ├── metadata_extractor.py    # Content → description + keywords
│   │   └── processor.py            # Gold orchestrator
│   ├── categorize/                  # Topic clustering (categorize)
│   ├── prd/                         # PRD generation (prd)
│   ├── workflow/                    # Workflow extraction (workflow)
│   ├── skills/                      # Skills extraction (skills)
│   └── utils/                       # Shared helpers
├── scripts/                     # Example scripts (not shipped in package)
├── tests/                       # Unit, integration, contract tests
├── pyproject.toml
├── CONTRIBUTING.md
├── CHANGELOG.md
└── LICENSE                      # MIT
```

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. The short version:

1. Fork and clone
2. Write tests first (TDD is non-negotiable)
3. Run all quality gates before pushing
4. Open a PR with a clear description

## License

MIT License — see [LICENSE](LICENSE) for details.

## Citation

```bibtex
@software{docmeld2026,
  title     = {DocMeld: Lightweight PDF to Agent-Ready Knowledge Pipeline},
  year      = {2026},
  license   = {MIT},
  url       = {https://github.com/agentii-ai/DocMeld}
}
```
