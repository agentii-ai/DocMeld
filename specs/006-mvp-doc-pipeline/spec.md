# Feature Specification: MVP Word Document (DOC/DOCX) Data Pipeline

**Feature Branch**: `006-mvp-doc-pipeline`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "Develop a pipeline to process .doc and .docx files into elements JSON with page numbers, mirroring the existing PDF pipeline (001-mvp-pdf-pipeline) but with richer element types including tables, charts, embedded formulas, and images."

## Clarifications

### Session 2026-07-09

- Q: When processing legacy .doc files, what should happen if LibreOffice is not installed? → A: Log a clear error message that LibreOffice is required for .doc processing, skip the file, and continue processing other files.
- Q: Should chart elements (extracted from embedded charts) be represented as structured data or as images? → A: Both: attempt to extract chart data as structured table data (primary), fall back to image extraction if data extraction fails.
- Q: How should the pipeline handle .docx files that have embedded .doc objects (OLE embeddings)? → A: Log a warning about the embedded OLE object (it cannot be extracted without external tools) and proceed with the rest of the document content.
- Q: Should related Word formats (.docm, .dotx, .dot, .rtf) also be supported, or only .doc and .docx? → A: Support .doc and .docx only. Other Word-family formats (.docm, .dotx, .dot, .rtf) are skipped with a warning message, keeping the MVP focused.
- Q: What should happen to the intermediate PDF generated during .doc → LibreOffice → PDF processing? → A: Delete the intermediate PDF automatically after the bronze JSON is successfully generated, keeping the output folder clean.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process Single DOCX File to Bronze Format (Priority: P1)

As a developer, I want to process a single .docx file into a structured JSON format so that I can extract and analyze document elements programmatically.

**Why this priority**: DOCX is the modern standard format used by Microsoft Word since 2007 and represents the vast majority of Word documents in circulation. This is the foundation of the entire DOC pipeline.

**Independent Test**: Can be fully tested by providing a .docx file path, running the bronze processor, and verifying that a sanitized filename with hash suffix is created along with a JSON file containing all document elements (text, tables, titles, images, charts, formulas) with correct page numbers.

**Acceptance Scenarios**:

1. **Given** a .docx file at path `/documents/report.docx`, **When** I run the bronze processor, **Then** the system creates a sanitized filename `report_a3f5c2.docx` (where `a3f5c2` is the last 6 digits of MD5 hash), creates a folder `report_a3f5c2/`, and generates `report_a3f5c2.json` containing all document elements in reading order.

2. **Given** a .docx file with special characters in filename like `Report (2024) - Final!.docx`, **When** I run the bronze processor, **Then** the system sanitizes the filename to `report_2024_final_b7e9d1.docx` and processes it successfully.

3. **Given** a multi-page .docx with tables, images, charts, embedded MathType formulas, and text, **When** I run the bronze processor, **Then** the JSON output contains elements with types "text", "table", "title", "image", "chart", and "formula" in document order, each with correct `page_no` starting from 1.

4. **Given** a .docx that has already been processed (hash exists), **When** I run the bronze processor again, **Then** the system skips re-processing and uses the existing JSON file.

---

### User Story 2 - Process Single Legacy DOC File to Bronze Format (Priority: P2)

As a developer, I want to process legacy .doc files via LibreOffice conversion so that older Word documents are supported within the same pipeline.

**Why this priority**: Legacy .doc files are still common in many organizations. While DOCX is the primary focus, .doc support ensures completeness. This is P2 because it depends on an external tool (LibreOffice) and serves a smaller but important portion of documents.

**Independent Test**: Can be fully tested by providing a .doc file path, verifying that the file is converted to PDF via LibreOffice, and the resulting PDF is then processed through the existing PyMuPDF backend to produce a bronze JSON file.

**Acceptance Scenarios**:

1. **Given** a legacy .doc file at path `/documents/old_report.doc`, **When** I run the bronze processor, **Then** the system converts the file to PDF using LibreOffice (soffice), processes the PDF through the PyMuPDF backend, and produces a bronze JSON file with correct page structure.

2. **Given** a .doc file on a system where LibreOffice is not installed, **When** I run the bronze processor, **Then** the system logs a clear error message indicating LibreOffice is required, skips the file, and continues processing other files in batch mode.

3. **Given** a .doc file with complex formatting (tables, embedded images, headers/footers), **When** I run the bronze processor, **Then** the converted PDF preserves visual layout with minimal fidelity loss, and the resulting JSON reflects the document structure.

---

### User Story 3 - Process Folder of Word Documents to Bronze Format (Priority: P1)

As a developer, I want to process an entire folder of .doc and .docx files in batch so that I can efficiently convert large mixed-format document collections.

**Why this priority**: Batch processing is essential for real-world use cases where users have dozens or hundreds of Word documents. This is P1 because it's a natural extension of single-file processing and critical for MVP adoption.

**Independent Test**: Can be fully tested by providing a folder path containing both .doc and .docx files, running the bronze processor, and verifying that all files are processed with the appropriate backend and proper output structure.

**Acceptance Scenarios**:

1. **Given** a folder `/documents/` containing 5 .docx and 3 .doc files, **When** I run the bronze processor on the folder, **Then** all 8 files are processed: .docx files via the docling backend and .doc files via the soffice+PyMuPDF backend.

2. **Given** a folder with mixed file types (DOCX, DOC, PDF, DOCM, DOTX, images), **When** I run the bronze processor, **Then** only .doc and .docx files are processed; other Word-family formats (.docm, .dotx, .dot, .rtf) are skipped with a warning, and non-Word files (PDF, images) are also skipped with a warning.

3. **Given** a folder where some documents have already been processed, **When** I run the bronze processor, **Then** only unprocessed documents are converted, and existing processed files are skipped.

---

### User Story 4 - Convert Bronze JSON to Silver JSONL (Priority: P2)

As a developer, I want to convert bronze JSON files into page-by-page JSONL format so that each page becomes a standalone document suitable for agent consumption, with richer element type support than PDF.

**Why this priority**: Silver processing transforms the element-based structure into page-based documents. This mirrors the PDF pipeline's silver stage but must handle additional element types (charts, formulas, headers, footers, footnotes).

**Independent Test**: Can be fully tested by providing a bronze JSON file containing diverse element types, running the silver processor, and verifying that a JSONL file is created where each line represents one page with metadata and markdown-formatted content including all element types.

**Acceptance Scenarios**:

1. **Given** a bronze JSON file `report_a3f5c2.json` with elements across 5 pages including charts and formulas, **When** I run the silver processor, **Then** a JSONL file `report_a3f5c2.jsonl` is created with exactly 5 lines (one per page).

2. **Given** a bronze JSON with chart elements containing structured table data, **When** I run the silver processor, **Then** charts are rendered in the page_content as markdown tables with a `[[Chart1]]` marker.

3. **Given** a bronze JSON with formula elements (LaTeX or MathML), **When** I run the silver processor, **Then** formulas are preserved in the page_content with `[[Formula1]]` markers and their LaTeX representation.

4. **Given** a bronze JSON with header and footer elements, **When** I run the silver processor, **Then** headers and footers are included in the appropriate page's content with `[Header]` and `[Footer]` markers.

---

### User Story 5 - Enrich Silver JSONL with Gold Metadata (Priority: P3)

As a developer, I want to analyze each page's content and extract descriptions and keywords so that agents can quickly understand and search document content, including chart data and formula contexts.

**Why this priority**: Gold processing adds semantic metadata, same as the PDF pipeline. This is P3 because it's an enhancement on top of core pipeline functionality.

**Independent Test**: Can be fully tested by providing a silver JSONL file, running the gold processor with DeepSeek API, and verifying that each page now includes `description` and `keywords` fields in the metadata.

**Acceptance Scenarios**:

1. **Given** a silver JSONL file with 5 pages containing diverse element types, **When** I run the gold processor, **Then** each page's metadata is enriched with a one-line `description` and a list of `keywords` extracted by DeepSeek-chat.

2. **Given** a page containing a chart about revenue trends, **When** I run the gold processor, **Then** the description references the chart content and keywords include relevant terms like "revenue", "trend", "quarterly".

3. **Given** a silver JSONL file that has already been processed to gold, **When** I run the gold processor again, **Then** the system skips re-processing and uses the existing gold JSONL file.

---

### Edge Cases

- **What happens when a .docx file is corrupted or unreadable?** The system logs an error with the filename and continues processing other files in batch mode. The corrupted file is skipped and reported in the summary.

- **What happens when a .docx has no extractable text (all images/scanned content)?** The bronze processor extracts images and page structure. Text elements will be empty or minimal. A warning is logged indicating the document may benefit from OCR.

- **What happens when a .docx has embedded OLE objects (e.g., embedded Excel charts, .doc sub-documents)?** The system logs a warning about the embedded OLE object and proceeds with the rest of the document content. OLE objects are not extracted individually.

- **What happens with extremely large .docx files (>100MB)?** The system processes the file but logs a warning about potential memory pressure. Processing time scales with file size.

- **What happens with .docx files that contain tracked changes/revisions?** The system processes the final (accepted) document state. A warning is logged if tracked changes are detected, recommending the user accept all changes before processing.

- **What happens when a .docx contains embedded fonts or custom XML?** The system ignores custom XML parts and embedded fonts; only document content (body, headers, footers, footnotes) is extracted.

- **What happens when a .docx file uses password protection?** The system logs an error and skips the file. Password-protected documents cannot be processed.

- **What happens when a .docx has very complex nested tables?** The system extracts nested tables as hierarchical markdown table structures. If nesting exceeds 3 levels, a warning is logged.

- **What happens when a chart's underlying data cannot be extracted?** The chart is extracted as an image element instead, with a note in the content field that data extraction was unavailable.

- **What happens when LibreOffice conversion of a .doc file produces a corrupted PDF?** The system logs the error, attempts conversion once more, and if it fails again, skips the file, deletes the corrupted intermediate PDF, and reports the failure.

- **What happens with .docm, .dotx, .dot, or .rtf files in the input folder?** The system skips these formats with a warning message indicating they are not supported in this version. Only .doc and .docx are processed.

## Requirements *(mandatory)*

### Functional Requirements

**Bronze Level Processing — DOCX (docling backend):**

- **FR-001**: System MUST accept a local file path to a single .doc or .docx file, or a folder containing .doc/.docx files as input. Other Word-family formats (.docm, .dotx, .dot, .rtf) MUST be skipped with a warning message.

- **FR-002**: System MUST sanitize filenames by removing or replacing characters that are dangerous in file paths (e.g., `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`), preserving the original file extension (.doc or .docx).

- **FR-003**: System MUST calculate the MD5 hash of each document file and append the last 6 digits of the hash to the sanitized filename (e.g., `filename_stem_a3f5c2.docx`).

- **FR-004**: System MUST create an output folder with the same name as the hashed filename (e.g., `filename_stem_a3f5c2/`) in the same directory as the source document.

- **FR-005**: System MUST extract document elements from .docx files using the docling library and store them in a JSON file named `filename_stem_hash6.json`.

- **FR-006**: System MUST support the following element types in the JSON output: "text", "table", "title", "image", "chart", "formula", "header", "footer", "footnote", "endnote".

- **FR-007**: Each element in the JSON MUST include a `type` field (string) and a `page_no` field (integer starting from 1).

- **FR-008**: Title elements MUST include a `level` field (integer, 0-based: 0=H1, 1=H2, etc.) and a `content` field (string).

- **FR-009**: Text elements MUST include a `content` field (string) containing the extracted text.

- **FR-010**: Table elements MUST include a `content` field (markdown-formatted table string) and a `summary` field (string describing table contents). Tables found in headers/footers are identified separately from main body tables.

- **FR-011**: Image elements MUST include `image_name`, `content` (optional description/caption), `image` (base64-encoded), `image_id`, and `bbox` (bounding box coordinates) fields.

- **FR-012**: Chart elements MUST include a `content` field (markdown-formatted table representing the chart's underlying data, when extractable), a `chart_type` field (string: e.g., "bar", "line", "pie"), and an `image` field (base64-encoded chart image as fallback). If data extraction fails, the chart is captured as an image element with type "image" and a note.

- **FR-013**: Formula elements MUST include a `content` field (LaTeX string representation) and a `formula_type` field (string: e.g., "MathType", "OMML", "LaTeX").

- **FR-014**: Header and footer elements MUST include a `content` field (string) and indicate whether they apply to all pages, even pages only, or odd pages only.

- **FR-015**: Footnote and endnote elements MUST include a `content` field (string), a `reference_id` field (string, the footnote/endnote reference marker), and the `page_no` where the reference appears.

- **FR-016**: Elements in the JSON MUST be ordered according to the document's reading order (body text first, headers/footers per page, footnotes inline where referenced).

- **FR-017**: System MUST skip re-processing if a bronze JSON file already exists for a given document hash.

**Bronze Level Processing — DOC (soffice backend):**

- **FR-018**: System MUST detect .doc files and route them to the soffice backend, which converts the document to an intermediate PDF via LibreOffice, processes it through the existing PyMuPDF backend, and then deletes the intermediate PDF after successful bronze JSON generation.

- **FR-019**: System MUST verify that LibreOffice (soffice) is available on the system PATH. If not found, the system MUST log a clear error message and skip .doc files without crashing the pipeline.

- **FR-020**: The soffice backend MUST produce output in the same format as bronze DOCX processing (JSON with all available element types). A `WARNING` level log message MUST indicate that element type richness is limited to the 4 types extractable from the converted PDF (text, table, title, image). The output JSON MUST include a `"soffice_conversion": true` marker in a document-level metadata field.

**Silver Level Processing:**

- **FR-021**: System MUST accept a bronze JSON file path as input and produce a JSONL file with the same base name (e.g., `filename_stem_hash6.jsonl`).

- **FR-022**: Each line in the JSONL file MUST represent one page of the document.

- **FR-023**: Each JSONL line MUST be a valid JSON object with `metadata` and `page_content` fields.

- **FR-024**: The `metadata` field MUST include: `uuid` (unique identifier), `source` (filename), `page_no` (e.g., "page1"), and `session_title` (markdown title hierarchy).

- **FR-025**: System MUST track title hierarchy across elements and include all parent titles at the beginning of each page's content.

- **FR-026**: The `page_content` field MUST render all elements from that page in markdown format, handling the following element type renderings:
  - Tables: `[[TableN]]` / `[/TableN]` markers with global numbering (only tables with >1 data row receive numbered markers)
  - Charts: `[[ChartN]]` / `[/ChartN]` markers with global numbering, rendered as markdown tables
  - Formulas: `[[FormulaN]]` / `[/FormulaN]` markers with LaTeX content
  - Headers: `[Header scope=all|even|odd]` content `[/Header]` markers
  - Footers: `[Footer scope=all|even|odd]` content `[/Footer]` markers
  - Footnotes: `[^N]` markdown footnote syntax
  - Images: `[[Image: description]]` placeholder
  - Titles: markdown headings (`#`, `##`, `###`) based on level

- **FR-027**: Numbering for tables, charts, and formulas MUST each be independent global sequences across the entire document (Table1, Table2, ...; Chart1, Chart2, ...; Formula1, Formula2, ...).

- **FR-028**: System MUST skip re-processing if a silver JSONL file already exists for a given bronze JSON.

**Gold Level Processing:**

- **FR-029**: System MUST accept a silver JSONL file path as input and produce an enriched JSONL file with a `_gold` suffix (e.g., `filename_hash6_gold.jsonl`) in the same output folder, preserving the original silver JSONL file.

- **FR-030**: System MUST use DeepSeek-chat API to analyze each page's `page_content` and extract semantic metadata. API credentials MUST be provided via the `DEEPSEEK_API_KEY` environment variable (required). An optional `DEEPSEEK_API_ENDPOINT` environment variable MAY be used to specify custom API endpoints. The system MUST support loading these variables from a `.env.local` file at the repository root.

- **FR-031**: For each page, the system MUST add a `description` field (string, one-line summary) to the metadata.

- **FR-032**: For each page, the system MUST add a `keywords` field (list of strings) to the metadata.

- **FR-033**: System MUST handle API rate limiting by implementing exponential backoff with up to 3 retry attempts.

- **FR-034**: System MUST continue processing remaining pages if one page fails gold enrichment, marking failed pages with `"gold_processing_failed": true`.

- **FR-035**: System MUST skip re-processing if a gold JSONL file already exists (determined by presence of `description` and `keywords` fields in metadata).

**General Requirements:**

- **FR-036**: System MUST provide progress indicators when processing multiple files (e.g., "Processing 3/10 files...").

- **FR-037**: System MUST log all errors with sufficient context (filename, page number, error message) to a timestamped log file named `docmeld_YYYYMMDD_HHMMSS.log` in the current working directory. A new log file is created per pipeline invocation.

- **FR-038**: System MUST generate a summary report after processing showing: total files processed, successful conversions, failed conversions, and processing time.

- **FR-039**: System MUST be idempotent — running the same processing step multiple times produces the same result without duplicating work.

- **FR-040**: When processing multiple files in batch mode, the system MUST continue processing all remaining files even if one file fails, logging each error and including all failures in the final summary report (fail-fast disabled).

- **FR-041**: System MUST support a `--backend` CLI flag that allows users to select the processing backend: `docling` (default for .docx), `pymupdf` (for .doc via soffice conversion), or `auto` (detect based on file extension).

### Key Entities

- **Word Document**: The source file to be processed (.doc or .docx). Attributes: original filename, sanitized filename, MD5 hash, file size, page count, format (doc/docx).

- **Document Element**: A structural component extracted from the document. Attributes: type (text/table/title/image/chart/formula/header/footer/footnote/endnote), page_no, content, additional type-specific fields.

- **Chart Element**: A structured representation of an embedded chart. Attributes: chart_type (bar/line/pie/etc.), content (markdown table of data), image (base64 fallback).

- **Formula Element**: An embedded mathematical formula. Attributes: content (LaTeX string), formula_type (MathType/OMML/LaTeX).

- **Header/Footer Element**: A page margin element. Attributes: content, page_scope (all/even/odd).

- **Footnote/Endnote Element**: A document note. Attributes: content, reference_id, page_no.

- **Bronze JSON**: The intermediate structured representation of a document. Contains an ordered list of document elements.

- **Silver Page**: A single page represented as a standalone JSON object. Attributes: metadata (uuid, source, page_no, session_title), page_content (markdown-formatted).

- **Gold Page**: An enriched silver page with semantic metadata. Additional attributes: description (string), keywords (list of strings).

- **Processing Pipeline**: The three-stage transformation process. Stages: Bronze (DOCX/DOC → JSON), Silver (JSON → JSONL by page), Gold (JSONL → enriched JSONL with AI metadata).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single .docx file (10-50 pages) can be processed through all three pipeline stages (bronze → silver → gold) in under 5 minutes on standard hardware.

- **SC-002**: A single .doc file (10-50 pages) can be processed through all three pipeline stages in under 8 minutes (accounting for LibreOffice conversion overhead).

- **SC-003**: The system successfully processes 95% of digital-native .docx files without errors or data loss.

- **SC-004**: The system successfully processes 85% of legacy .doc files without errors (lower threshold due to format complexity and conversion fidelity).

- **SC-005**: Bronze JSON output preserves 100% of extractable text content from the source document in correct reading order.

- **SC-006**: Tables extracted from .docx files are recognized with at least 90% accuracy (correct structure, headers, and cell content).

- **SC-007**: Charts in .docx files are detected and at minimum captured as images; chart data extraction succeeds for at least 70% of common chart types (bar, line, pie).

- **SC-008**: Embedded formulas (MathType, OMML) in .docx files are extracted with correct LaTeX representation for at least 90% of formulas.

- **SC-009**: Silver JSONL output contains exactly one line per page, with each page including complete title hierarchy context and correctly rendered markers for all element types.

- **SC-010**: Gold metadata extraction produces relevant descriptions and keywords for 90% of pages as validated by manual review of sample outputs.

- **SC-011**: Batch processing of 100 mixed-format documents (.doc and .docx) completes without manual intervention, with a detailed summary report of successes and failures.

- **SC-012**: Re-running the pipeline on already-processed files completes in under 10 seconds (skipping existing outputs).

- **SC-013**: The system handles filenames with special characters, spaces, and unicode without errors or data corruption.

- **SC-014**: Memory usage stays under 500MB when processing .docx files up to 100 pages.

- **SC-015**: The pipeline produces outputs that are directly consumable by downstream agent systems without additional transformation, with the same JSONL contract as the PDF pipeline.

## Assumptions

1. LibreOffice is required for .doc file processing. The system will check for its availability and skip .doc files with a clear error if not found, rather than failing the entire pipeline.

2. The existing PyMuPDF backend (from 001-mvp-pdf-pipeline) can be reused for processing the PDF generated from .doc conversion via LibreOffice.

3. The silver and gold pipeline stages (JSON → JSONL and JSONL → enriched JSONL) can be mostly reused from the PDF pipeline, with extensions for the new element types (chart, formula, header, footer, footnote, endnote).

4. DeepSeek-chat API usage mirrors the existing PDF gold pipeline.

5. Document page numbers as reported by docling may differ from the document's own page numbering (e.g., roman numerals for front matter). The pipeline uses physical page numbers (1-indexed) as its canonical page numbering.

6. Tracked changes in .docx files should be accepted before processing for best results. The system will log a warning if it detects tracked changes but will not reject the file.

7. Embedded OLE objects in .docx (Excel charts, Visio diagrams, etc.) are logged as warnings and not individually extracted, as no open-source Python library reliably extracts these.
