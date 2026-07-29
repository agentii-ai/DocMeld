# DocMeld Use Cases

Status legend: `[PENDING]` | `[IN PROGRESS]` | `[DONE]` | `[BLOCKED]`

---

## Use Case 1 — Research Papers General Reading [DONE]

**Branch**: `002-paper-batch-categorize`

**Description**: Given a folder path containing many PDFs downloaded from arXiv and Google Scholar, process all papers and produce a summary of each, then group them into categories based on their topics.

**What DocMeld needs to do**:
- Batch-process all PDFs in the folder through bronze stage (extract elements)
- Silver stage: produce page-by-page JSONL for each paper
- Gold stage: extract topics and keywords per paper via DeepSeek-chat
- New: aggregate gold metadata across all papers to identify topic clusters
- New: generate a category index (e.g., `categories.json`) mapping each paper to its assigned category
- New: optionally reorganize files — move each PDF and its output folder into a category subfolder

**Test input**: `~/Documents/research-papers/sample-folder`

**Acceptance criteria**:
- All PDFs in folder are processed through full pipeline
- Each paper has a summary and keyword list
- Papers are grouped into categories with a machine-readable index
- Category assignment is deterministic for the same input

---

## Use Case 2 — Research Paper to PRD [DONE]

**Branch**: `003-paper-to-prd`

**Description**: Given a single research paper (CS/engineering), generate a Product Requirements Document (PRD) from it. Many CS papers describe systems that can be productized.

**What DocMeld needs to do**:
- Extract text from PDF (bronze)
- Produce page-by-page content (silver)
- Gold stage: instead of generic description/keywords, generate a structured PRD containing:
  - Problem statement (from paper's abstract/introduction)
  - Proposed solution (from paper's methodology)
  - Key features / capabilities
  - Technical requirements
  - Target users
  - Success metrics (from paper's evaluation section)
- Output as a new `_prd.md` file alongside the gold JSONL

**Test input**: `~/Documents/research-papers/sample-paper.pdf`

**Acceptance criteria**:
- PRD is generated as markdown with all required sections
- PRD content is grounded in the actual paper content (no hallucination)
- Works for any single PDF input via CLI: `docmeld prd paper.pdf`

---

## Use Case 3 — Books to Claude Skills [DONE]

**Branch**: `004-books-to-skills`

**Description**: Given a technical book (PDF), extract its knowledge into structured Claude Code skill files (`.claude/commands/*.md`) that encode the book's methodology as reusable agent skills.

**What DocMeld needs to do**:
- Extract full book content through bronze + silver stages
- Gold stage: identify discrete skills/techniques/methodologies in the book
- New: for each identified skill, generate a Claude Code skill file with:
  - YAML frontmatter (description, handoffs)
  - Step-by-step instructions derived from the book's content
  - Examples and edge cases
- Output: a directory of `.md` skill files ready to drop into `.claude/commands/`

**Acceptance criteria**:
- Skills are extracted from book chapters/sections
- Each skill file follows Claude Code skill format
- Skills are self-contained and actionable

---

## Use Case 4 — Research Paper to Workflow [DONE]

**Branch**: `005-paper-to-workflow`

**Description**: Given a research paper that describes a process or algorithm, extract a step-by-step workflow that can be followed to reproduce or apply the paper's approach.

**What DocMeld needs to do**:
- Extract paper content through bronze + silver stages
- Gold stage: identify the paper's methodology/algorithm/process
- New: generate a structured workflow document with:
  - Prerequisites and inputs
  - Numbered steps with descriptions
  - Decision points and branching logic
  - Expected outputs at each stage
  - Validation criteria
- Output as `_workflow.md` or structured JSON

**Acceptance criteria**:
- Workflow steps are ordered and actionable
- Decision points are clearly marked
- Workflow is grounded in the paper's actual methodology

---

## Use Case 5 — (Reserved) [PENDING]

**Branch**: TBD

**Description**: TBD

---

## Implementation Order

Priority order for the harness coding loop:

1. **Use Case 1** (batch categorize) — extends existing batch processing, most natural next step
2. **Use Case 2** (paper to PRD) — single-file gold stage variant, moderate scope
3. **Use Case 4** (paper to workflow) — similar to PRD but different output format
4. **Use Case 3** (books to skills) — most complex, requires long-document handling
