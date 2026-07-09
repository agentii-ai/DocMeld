# Feature Specification: MVP PowerPoint (PPT/PPTX) Data Pipeline

**Feature Branch**: `007-mvp-ppt-pipeline`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "Develop a pipeline to process .ppt and .pptx files into elements JSON with slide numbers, mirroring the existing PDF pipeline (001-mvp-pdf-pipeline) but with richer element types including tables, charts, embedded formulas, images, SmartArt, speaker notes, slide layouts, and more."

## Clarifications

### Session 2026-07-09

- Q: When processing legacy .ppt files, what should happen if LibreOffice is not installed? → A: Log a clear error message that LibreOffice is required for .ppt processing, skip the file, and continue processing other files.
- Q: What PPTX-specific element types should the pipeline extract beyond those already in the PDF/DOC pipeline? → A: PPTX adds "notes" (speaker notes), "smartart" (SmartArt diagrams), "group" (grouped shapes), and "footer" (slide footer/placeholders). The existing 10 types (text, table, title, image, chart, formula, header, footer, footnote, endnote) carry forward where applicable.
- Q: How should the pipeline handle slides that contain multiple overlapping shapes/layers? → A: Order elements by geometric reading order (top-to-bottom, left-to-right) as primary, using z-order (shape-tree stacking) as the tie-breaker when shapes overlap or share the same position. Log a debug message when complex layering is detected (more than 20 elements on one slide).
- Q: Should speaker notes be attached to their slide's page or output as separated data? → A: Attach speaker notes to their slide's page, rendered in the silver `page_content` with `[Notes]` markers, making them part of the page context for downstream agents.
- Q: Should the silver metadata `page_no` use the presentation-native label "slide1" or the cross-pipeline "page1"? → A: Use "page1" for the metadata value to maintain identical JSONL contract across PDF, DOC, and PPT pipelines. Slide semantics are conveyed by the source file type.
- Q: How should hidden slides be handled across the Bronze → Silver → Gold pipeline? → A: Extract hidden slides fully with continuous physical slide numbering, flag them with `hidden: true` in Bronze, and include them in Silver and Gold output so downstream agents can decide whether to use them.
- Q: Should PowerPoint slide comments/annotations be extracted? → A: Yes — extract comments as a `comment` element type with `author`, `content`, and `page_no` fields from the OOXML comment parts; render in silver with `[Comment: author]` markers.
- Q: Which library is the primary .pptx parsing engine? → A: python-pptx for slide-level shape extraction (text, notes, comments, groups, SmartArt, footers) plus docling for richer tables and embedded chart data; no PDF conversion for .pptx.
- Q: How should hyperlinks (text/shape links) be handled? → A: Preserve inline as markdown links `[text](url)` within their parent text element's `content`; no dedicated element type. The target URL is retained in the markdown link.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process Single PPTX File to Bronze Format (Priority: P1)

As a developer, I want to process a single .pptx file into a structured JSON format so that I can extract and analyze presentation elements programmatically, organized by slide number.

**Why this priority**: PPTX is the modern standard format used by PowerPoint since 2007 and represents the vast majority of presentation files in circulation. This is the foundation of the entire PPT pipeline.

**Independent Test**: Can be fully tested by providing a .pptx file path, running the bronze processor, and verifying that a sanitized filename with hash suffix is created along with a JSON file containing all slide elements (text, tables, titles, images, charts, formulas, SmartArt, speaker notes) with correct slide numbers.

**Acceptance Scenarios**:

1. **Given** a .pptx file at path `/presentations/pitch_deck.pptx`, **When** I run the bronze processor, **Then** the system creates a sanitized filename `pitch_deck_a3f5c2.pptx` (where `a3f5c2` is the last 6 digits of MD5 hash), creates a folder `pitch_deck_a3f5c2/`, and generates `pitch_deck_a3f5c2.json` containing all slide elements in reading order.

2. **Given** a .pptx file with special characters in filename like `Q4 Earnings (Final) - v2!.pptx`, **When** I run the bronze processor, **Then** the system sanitizes the filename to `q4_earnings_final_v2_b7e9d1.pptx` and processes it successfully.

3. **Given** a multi-slide .pptx with tables, images, charts, SmartArt, embedded formulas, text, and speaker notes, **When** I run the bronze processor, **Then** the JSON output contains elements with types "text", "table", "title", "image", "chart", "formula", "smartart", "notes", "group", and "footer" in slide order, each with correct `page_no` starting from 1 (where `page_no` maps to slide number).

4. **Given** a .pptx that has already been processed (hash exists), **When** I run the bronze processor again, **Then** the system skips re-processing and uses the existing JSON file.

---

### User Story 2 - Process Single Legacy PPT File to Bronze Format (Priority: P2)

As a developer, I want to process legacy .ppt files via LibreOffice conversion so that older presentation files are supported within the same pipeline.

**Why this priority**: Legacy .ppt files are still common in many organizations. While PPTX is the primary focus, .ppt support ensures completeness. This is P2 because it depends on an external tool (LibreOffice) and serves a smaller but important portion of presentations.

**Independent Test**: Can be fully tested by providing a .ppt file path, verifying that the file is converted to PDF via LibreOffice, and the resulting PDF is then processed through the existing PyMuPDF backend to produce a bronze JSON file.

**Acceptance Scenarios**:

1. **Given** a legacy .ppt file at path `/presentations/old_pitch.ppt`, **When** I run the bronze processor, **Then** the system converts the file to PDF using LibreOffice (soffice), processes the PDF through the PyMuPDF backend, and produces a bronze JSON file with correct slide/page structure.

2. **Given** a .ppt file on a system where LibreOffice is not installed, **When** I run the bronze processor, **Then** the system logs a clear error message indicating LibreOffice is required, skips the file, and continues processing other files in batch mode.

3. **Given** a .ppt file with complex formatting (tables, embedded images, speaker notes), **When** I run the bronze processor, **Then** the converted PDF preserves visual layout with minimal fidelity loss, and the resulting JSON reflects the slide structure. A warning is logged noting that element type richness is limited to what PDF extraction supports.

---

### User Story 3 - Process Folder of Presentation Files to Bronze Format (Priority: P1)

As a developer, I want to process an entire folder of .ppt and .pptx files in batch so that I can efficiently convert large mixed-format presentation collections.

**Why this priority**: Batch processing is essential for real-world use cases where users have dozens or hundreds of presentations. This is P1 because it's a natural extension of single-file processing and critical for MVP adoption.

**Independent Test**: Can be fully tested by providing a folder path containing both .ppt and .pptx files, running the bronze processor, and verifying that all files are processed with the appropriate backend and proper output structure.

**Acceptance Scenarios**:

1. **Given** a folder `/presentations/` containing 5 .pptx and 3 .ppt files, **When** I run the bronze processor on the folder, **Then** all 8 files are processed: .pptx files via the pptx backend and .ppt files via the soffice+PyMuPDF backend.

2. **Given** a folder with mixed file types (PPTX, PPT, PDF, PPTM, POTX, images), **When** I run the bronze processor, **Then** only .ppt and .pptx files are processed; other presentation-family formats (.pptm, .potx, .ppsx, .odp) are skipped with a warning, and non-presentation files (PDF, images) are also skipped with a warning.

3. **Given** a folder where some presentations have already been processed, **When** I run the bronze processor, **Then** only unprocessed presentations are converted, and existing processed files are skipped.

---

### User Story 4 - Convert Bronze JSON to Silver JSONL (Priority: P2)

As a developer, I want to convert bronze JSON files into slide-by-slide JSONL format so that each slide becomes a standalone document suitable for agent consumption, with richer element type support than PDF.

**Why this priority**: Silver processing transforms the element-based structure into slide-based documents. This mirrors the PDF pipeline's silver stage but must handle additional element types (charts, formulas, SmartArt, speaker notes, grouped shapes).

**Independent Test**: Can be fully tested by providing a bronze JSON file containing diverse element types, running the silver processor, and verifying that a JSONL file is created where each line represents one slide with metadata and markdown-formatted content including all element types.

**Acceptance Scenarios**:

1. **Given** a bronze JSON file `pitch_deck_a3f5c2.json` with elements across 10 slides including charts, SmartArt, and speaker notes, **When** I run the silver processor, **Then** a JSONL file `pitch_deck_a3f5c2.jsonl` is created with exactly 10 lines (one per slide).

2. **Given** a bronze JSON with chart elements containing structured table data, **When** I run the silver processor, **Then** charts are rendered in the slide_content as markdown tables with a `[[Chart1]]` marker.

3. **Given** a bronze JSON with SmartArt elements, **When** I run the silver processor, **Then** SmartArt is rendered with `[[SmartArt1]]` markers and its textual content is extracted as markdown.

4. **Given** a bronze JSON with speaker notes elements, **When** I run the silver processor, **Then** speaker notes are included in the appropriate slide's content with `[Notes]` / `[/Notes]` markers.

5. **Given** a bronze JSON with slide footer elements, **When** I run the silver processor, **Then** footers are included with `[Footer]` / `[/Footer]` markers.

---

### User Story 5 - Enrich Silver JSONL with Gold Metadata (Priority: P3)

As a developer, I want to analyze each slide's content and extract descriptions and keywords so that agents can quickly understand and search presentation content, including chart data, SmartArt, and speaker notes contexts.

**Why this priority**: Gold processing adds semantic metadata, same as the PDF pipeline. This is P3 because it's an enhancement on top of core pipeline functionality.

**Independent Test**: Can be fully tested by providing a silver JSONL file, running the gold processor with DeepSeek API, and verifying that each slide now includes `description` and `keywords` fields in the metadata.

**Acceptance Scenarios**:

1. **Given** a silver JSONL file with 10 slides containing diverse element types, **When** I run the gold processor, **Then** each slide's metadata is enriched with a one-line `description` and a list of `keywords` extracted by DeepSeek-chat.

2. **Given** a slide containing a SmartArt process diagram about Q4 strategy, **When** I run the gold processor, **Then** the description references the SmartArt content and keywords include relevant terms like "strategy", "Q4", "process".

3. **Given** a silver JSONL file that has already been processed to gold, **When** I run the gold processor again, **Then** the system skips re-processing and uses the existing gold JSONL file.

---

### Edge Cases

- **What happens when a .pptx file is corrupted or unreadable?** The system logs an error with the filename and continues processing other files in batch mode. The corrupted file is skipped and reported in the summary.

- **What happens when a .pptx has no extractable text (all images/scanned slides)?** The bronze processor extracts images and slide structure. Text elements will be empty or minimal. A warning is logged indicating the presentation may benefit from OCR.

- **What happens when a .pptx has embedded OLE objects (e.g., embedded Excel charts, Visio diagrams)?** The system logs a warning about the embedded OLE object and proceeds with the rest of the slide content. OLE objects are not extracted individually.

- **What happens with extremely large .pptx files (>200MB)?** The system processes the file but logs a warning about potential memory pressure. Processing time scales with file size.

- **What happens when a slide has complex overlapping shapes (more than 20 elements on one slide)?** The system orders all elements by geometric reading order with z-order tie-breaking and logs a debug message about complex layering. No elements are dropped.

- **What happens with .pptx files that contain animations/video embeds?** The system extracts static visual content only. Animations, transitions, and video/audio embeds are silently ignored; their placeholder text (if any) is extracted if available.

- **What happens when a .pptx file uses password protection?** The system logs an error and skips the file. Password-protected presentations cannot be processed.

- **What happens when a .pptx has very complex nested SmartArt or grouped shapes?** The system extracts SmartArt text content hierarchically. If nesting exceeds 5 levels, a warning is logged. Grouped shapes are flattened: each child shape is extracted individually with a `group` parent reference.

- **What happens when a chart's underlying data cannot be extracted from the OOXML package?** The chart is extracted as an image element instead, with a note in the content field that data extraction was unavailable.

- **What happens when speaker notes contain formatting (bold, bullets, hyperlinks)?** The system extracts speaker notes as plain markdown text, preserving bullet structure and hyperlinks. Rich formatting beyond markdown (colors, fonts) is stripped.

- **What happens with .pptm, .potx, .ppsx, or .odp files in the input folder?** The system skips these formats with a warning message indicating they are not supported in this version. Only .ppt and .pptx are processed.

- **What happens when LibreOffice conversion of a .ppt file produces a corrupted PDF?** The system logs the error, attempts conversion once more, and if it fails again, skips the file, deletes the corrupted intermediate PDF, and reports the failure.

- **What happens with PowerPoint template (.pot) files?** .pot files are not supported. The system skips them with a warning message, same as other unsupported presentation formats.

- **What happens when a presentation contains hidden slides?** Hidden slides are extracted at their physical position with continuous numbering (no gaps in `page_no`), marked with `hidden: true`, and included in silver and gold output.

- **What happens when a slide has reviewer comments/annotations?** Comments are extracted as `comment` elements with author attribution and anchored to their slide's `page_no`. They are rendered in silver content with `[Comment: author]` markers. If no author is recorded, the author field is left empty.

- **What happens when text or a shape contains a hyperlink?** The hyperlink is preserved inline within the element's `content` as a markdown link `[text](url)`. Broken or empty URLs fall back to plain text (the visible link text is retained without a link target).

## Requirements *(mandatory)*

### Functional Requirements

**Bronze Level Processing — PPTX (pptx backend):**

- **FR-001**: System MUST accept a local file path to a single .ppt or .pptx file, or a folder containing .ppt/.pptx files as input. Other presentation-family formats (.pptm, .potx, .pot, .ppsx, .odp) MUST be skipped with a warning message.

- **FR-002**: System MUST sanitize filenames by removing or replacing characters that are dangerous in file paths (e.g., `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`), preserving the original file extension (.ppt or .pptx).

- **FR-003**: System MUST calculate the MD5 hash of each presentation file and append the last 6 digits of the hash to the sanitized filename (e.g., `filename_stem_a3f5c2.pptx`).

- **FR-004**: System MUST create an output folder with the same name as the hashed filename (e.g., `filename_stem_a3f5c2/`) in the same directory as the source presentation.

- **FR-005**: System MUST extract slide elements from .pptx files and store them in a JSON file named `filename_stem_hash6.json`.

- **FR-006**: System MUST support the following element types in the JSON output: "text", "table", "title", "image", "chart", "formula", "smartart", "notes", "group", "footer", "comment". Header, footnote, and endnote types from the DOC pipeline are not applicable to presentations and are excluded.

- **FR-007**: Each element in the JSON MUST include a `type` field (string) and a `page_no` field (integer starting from 1, representing the slide number).

- **FR-008**: Title elements MUST include a `level` field (integer, 0-based: 0=slide title, 1=subtitle/subheading) and a `content` field (string). System MUST detect the primary title placeholder on each slide and classify it as the slide title.

- **FR-009**: Text elements MUST include a `content` field (string) containing the extracted text from text boxes, shapes, and text placeholders.

- **FR-009a**: Hyperlinks on text or shapes MUST be preserved inline within the parent element's `content` as markdown links in the form `[text](url)`, retaining the target URL. Hyperlinks are not extracted as a separate element type.

- **FR-010**: Table elements MUST include a `content` field (markdown-formatted table string) and a `summary` field (string describing table contents).

- **FR-011**: Image elements MUST include `image_name`, `content` (optional description/caption), `image` (base64-encoded), `image_id`, and `bbox` (bounding box coordinates) fields.

- **FR-012**: Chart elements MUST include a `content` field (markdown-formatted table representing the chart's underlying data, when extractable from the embedded Excel data), a `chart_type` field (string: e.g., "bar", "line", "pie", "scatter", "area"), and an `image` field (base64-encoded chart image as fallback). If data extraction fails, the chart is captured as an image element with type "image" and a note.

- **FR-013**: Formula elements MUST include a `content` field (LaTeX string representation) when formulas are embedded in slides (e.g., MathType, Equation Editor objects).

- **FR-014**: SmartArt elements MUST include a `content` field (hierarchical markdown text extracted from the SmartArt diagram), a `smartart_type` field (string: e.g., "process", "cycle", "hierarchy", "relationship", "pyramid"), and an `image` field (base64-encoded SmartArt rendering as fallback).

- **FR-015**: Notes elements MUST include a `content` field (string, the speaker notes text in plain markdown), and MUST be associated with the `page_no` of their parent slide.

- **FR-016**: Group elements MUST include a `content` field (string describing the group) and a `child_count` field (integer, number of grouped child shapes). Each child shape within the group is extracted as a separate element with a `parent_id` referencing the group's `element_id`.

- **FR-017**: Footer elements MUST include a `content` field (string) indicating the slide footer text or placeholder text.

- **FR-017a**: Comment elements MUST include a `content` field (string, the comment text), an `author` field (string, the comment author when available), and MUST be associated with the `page_no` of the slide the comment is anchored to. Comments are extracted from the presentation's OOXML comment parts.

- **FR-018**: Elements in the JSON MUST be ordered by the slide's geometric reading order (top-to-bottom, left-to-right by bounding box) as the primary sort key, with z-order (shape-tree authoring order) used as the tie-breaker for overlapping or co-located shapes. Speaker notes MUST appear after all slide content elements for a given slide. Elements across slides MUST be ordered by slide number.

- **FR-019**: System MUST skip re-processing if a bronze JSON file already exists for a given presentation hash.

**Bronze Level Processing — PPT (soffice backend):**

- **FR-020**: System MUST detect .ppt files and route them to the soffice backend, which converts the presentation to an intermediate PDF via LibreOffice, processes it through the existing PyMuPDF backend, and then deletes the intermediate PDF after successful bronze JSON generation.

- **FR-021**: System MUST verify that LibreOffice (soffice) is available on the system PATH. If not found, the system MUST log a clear error message and skip .ppt files without crashing the pipeline.

- **FR-022**: The soffice backend MUST produce output in the same format as bronze PPTX processing (JSON elements with type and page_no), while noting that element type richness is limited to what the PyMuPDF backend can extract from the converted PDF (text, table, title, image only).

**Silver Level Processing:**

- **FR-023**: System MUST accept a bronze JSON file path as input and produce a JSONL file with the same base name (e.g., `filename_stem_hash6.jsonl`).

- **FR-024**: Each line in the JSONL file MUST represent one slide of the presentation.

- **FR-025**: Each JSONL line MUST be a valid JSON object with `metadata` and `page_content` fields.

- **FR-026**: The `metadata` field MUST include: `uuid` (unique identifier), `source` (filename), `page_no` (e.g., "page1"), and `session_title` (slide title hierarchy).

- **FR-027**: System MUST track slide title hierarchy across slides when PPTX section headers are present (sections become H1 titles, slide titles become H2).

- **FR-028**: The `page_content` field MUST render all elements from that slide in markdown format, handling the following element type renderings:
  - Tables: `[[TableN]]` / `[/TableN]` markers with global numbering (only tables with >1 data row receive numbered markers)
  - Charts: `[[ChartN]]` / `[/ChartN]` markers with global numbering, rendered as markdown tables
  - Formulas: `[[FormulaN]]` / `[/FormulaN]` markers with LaTeX content
  - SmartArt: `[[SmartArtN]]` / `[/SmartArtN]` markers with hierarchical markdown text
  - Speaker Notes: `[Notes]` / `[/Notes]` markers containing the notes text
  - Comments: `[Comment: author]` / `[/Comment]` markers containing the comment text
  - Footers: `[Footer]` / `[/Footer]` markers
  - Images: `[[Image: description]]` placeholder
  - Titles: markdown headings (`#`, `##`, `###`) based on level

- **FR-029**: Numbering for tables, charts, formulas, and SmartArt MUST each be independent global sequences across the entire presentation (Table1, Table2, ...; Chart1, Chart2, ...; Formula1, Formula2, ...; SmartArt1, SmartArt2, ...).

- **FR-030**: System MUST skip re-processing if a silver JSONL file already exists for a given bronze JSON.

**Gold Level Processing:**

- **FR-031**: System MUST accept a silver JSONL file path as input and produce an enriched JSONL file with a `_gold` suffix (e.g., `filename_hash6_gold.jsonl`) in the same output folder, preserving the original silver JSONL file.

- **FR-032**: System MUST use DeepSeek-chat API to analyze each slide's `page_content` and extract semantic metadata. API credentials MUST be provided via the `DEEPSEEK_API_KEY` environment variable (required). An optional `DEEPSEEK_API_ENDPOINT` environment variable MAY be used to specify custom API endpoints. The system MUST support loading these variables from a `.env.local` file at the repository root.

- **FR-033**: For each slide, the system MUST add a `description` field (string, one-line summary) to the metadata.

- **FR-034**: For each slide, the system MUST add a `keywords` field (list of strings) to the metadata.

- **FR-035**: System MUST handle API rate limiting by implementing exponential backoff with up to 3 retry attempts.

- **FR-036**: System MUST continue processing remaining slides if one slide fails gold enrichment, marking failed slides with `"gold_processing_failed": true`.

- **FR-037**: System MUST skip re-processing if a gold JSONL file already exists (determined by presence of `description` and `keywords` fields in metadata).

**General Requirements:**

- **FR-038**: System MUST provide progress indicators when processing multiple files (e.g., "Processing 3/10 files...").

- **FR-039**: System MUST log all errors with sufficient context (filename, slide number, error message) to a timestamped log file named `docmeld_YYYYMMDD_HHMMSS.log` in the current working directory. A new log file is created per pipeline invocation.

- **FR-040**: System MUST generate a summary report after processing showing: total files processed, successful conversions, failed conversions, and processing time.

- **FR-041**: System MUST be idempotent — running the same processing step multiple times produces the same result without duplicating work.

- **FR-042**: When processing multiple files in batch mode, the system MUST continue processing all remaining files even if one file fails, logging each error and including all failures in the final summary report (fail-fast disabled).

- **FR-043**: System MUST support a `--backend` CLI flag that allows users to select the processing backend: `pptx` (default for .pptx), `pymupdf` (for .ppt via soffice conversion), or `auto` (detect based on file extension).

### Key Entities

- **Presentation File**: The source file to be processed (.ppt or .pptx). Attributes: original filename, sanitized filename, MD5 hash, file size, slide count, format (ppt/pptx).

- **Slide Element**: A structural component extracted from a slide. Attributes: type (text/table/title/image/chart/formula/smartart/notes/group/footer/comment), page_no, content, additional type-specific fields. Elements contain an `element_id` (unique string) and optional `parent_id` (for grouped child shapes).

- **Chart Element**: A structured representation of an embedded chart. Attributes: chart_type (bar/line/pie/scatter/area), content (markdown table of data), image (base64 fallback).

- **SmartArt Element**: A diagrammatic representation of structured information. Attributes: smartart_type (process/cycle/hierarchy/relationship/pyramid), content (hierarchical markdown text), image (base64 fallback).

- **Notes Element**: Speaker notes attached to a slide. Attributes: content (plain markdown text), page_no (parent slide number).

- **Group Element**: A container for grouped shapes. Attributes: content (description), child_count, element_id (referenced by child shapes via parent_id).

- **Footer Element**: Slide footer or placeholder text. Attributes: content, page_no.

- **Comment Element**: An author-attributed annotation anchored to a slide. Attributes: content (comment text), author (comment author when available), page_no (anchored slide number).

- **Bronze JSON**: The intermediate structured representation of a presentation. Contains an ordered list of slide elements.

- **Silver Slide**: A single slide represented as a standalone JSON object. Attributes: metadata (uuid, source, page_no, session_title), page_content (markdown-formatted).

- **Gold Slide**: An enriched silver slide with semantic metadata. Additional attributes: description (string), keywords (list of strings).

- **Processing Pipeline**: The three-stage transformation process. Stages: Bronze (PPTX/PPT → JSON), Silver (JSON → JSONL by slide), Gold (JSONL → enriched JSONL with AI metadata).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single .pptx file (10-50 slides) can be processed through all three pipeline stages (bronze → silver → gold) in under 5 minutes on standard hardware.

- **SC-002**: A single .ppt file (10-50 slides) can be processed through all three pipeline stages in under 8 minutes (accounting for LibreOffice conversion overhead).

- **SC-003**: The system successfully processes 95% of digital-native .pptx files without errors or data loss.

- **SC-004**: The system successfully processes 85% of legacy .ppt files without errors (lower threshold due to format complexity and conversion fidelity).

- **SC-005**: Bronze JSON output preserves 100% of extractable text content from the source presentation in correct slide order, with within-slide elements ordered by geometric reading order and z-order tie-breaking.

- **SC-006**: Tables extracted from .pptx slides are recognized with at least 90% accuracy (correct structure, headers, and cell content).

- **SC-007**: Charts in .pptx files are detected and at minimum captured as images; chart data extraction succeeds for at least 70% of common chart types (bar, line, pie, scatter, area).

- **SC-008**: SmartArt diagrams in .pptx files are detected and their textual content is extracted with at least 80% accuracy for common diagram types (process, cycle, hierarchy, relationship).

- **SC-009**: Speaker notes are correctly associated with their parent slide and fully extracted for 95% of slides that contain notes.

- **SC-010**: Silver JSONL output contains exactly one line per slide, with each slide including complete slide title context and correctly rendered markers for all element types.

- **SC-011**: Gold metadata extraction produces relevant descriptions and keywords for 90% of slides as validated by manual review of sample outputs.

- **SC-012**: Batch processing of 100 mixed-format presentations (.ppt and .pptx) completes without manual intervention, with a detailed summary report of successes and failures.

- **SC-013**: Re-running the pipeline on already-processed files completes in under 10 seconds (skipping existing outputs).

- **SC-014**: The system handles filenames with special characters, spaces, and unicode without errors or data corruption.

- **SC-015**: Memory usage stays under 500MB when processing .pptx files up to 100 slides.

- **SC-016**: The pipeline produces outputs that are directly consumable by downstream agent systems without additional transformation, with the same JSONL contract as the PDF and DOC pipelines.

## Assumptions

1. The primary parsing approach for .pptx files uses python-pptx for slide-level shape extraction (text, speaker notes, comments, groups, SmartArt shapes, footers) and docling for structured content where it provides richer results (tables, embedded chart data). No PDF conversion is needed for the modern format. This preserves element-type richness that would be lost in PDF conversion.

2. LibreOffice is required for .ppt file processing only. The system will check for its availability and skip .ppt files with a clear error if not found, rather than failing the entire pipeline. PPTX processing does not require LibreOffice.

3. The existing PyMuPDF backend (from 001-mvp-pdf-pipeline) can be reused for processing the PDF generated from .ppt conversion via LibreOffice.

4. The silver and gold pipeline stages (JSON → JSONL and JSONL → enriched JSONL) can be mostly reused from the PDF pipeline, with extensions for the new element types (chart, formula, smartart, notes, group, footer).

5. DeepSeek-chat API usage mirrors the existing PDF and DOC gold pipelines.

6. Slide numbers ("page_no") use 1-indexed continuous physical slide numbers. Hidden slides are extracted at their actual physical position (numbering is not skipped), marked with a `hidden: true` flag in Bronze, and carried through Silver and Gold output so downstream consumers can filter them if desired.

7. Animations, transitions, video embeds, and audio embeds in .pptx files are intentionally excluded from extraction. Only static visual and textual content is processed.

8. Embedded OLE objects in .pptx (Excel charts, Visio diagrams, etc.) are logged as warnings and not individually extracted, as no open-source Python library reliably extracts these.

9. Slide master and layout-level content (repeating elements from the slide master template) are extracted once per slide as they appear, with inherited placeholders resolved to their actual content.

10. The pipeline targets the same output contract as 001-mvp-pdf-pipeline and 006-mvp-doc-pipeline, ensuring all three pipelines produce interchangeable JSONL for downstream agent consumption.
