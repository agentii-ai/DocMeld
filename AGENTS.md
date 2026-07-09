# DocMeld Development Guidelines

## Project Overview

DocMeld is a lightweight PDF-to-agent-ready knowledge pipeline. Three-stage architecture: Bronze (PDF → JSON elements) → Silver (JSON → page-by-page JSONL) → Gold (JSONL → AI-enriched metadata).

## Active Technologies
- Python 3.9+ + PyMuPDF (fitz), pymupdf4llm, pydantic, langchain-deepseek (all existing) (002-paper-batch-categorize)
- Filesystem (JSON files) — no database (002-paper-batch-categorize)

- Python 3.9+
- PyMuPDF (fitz), pymupdf4llm, Docling (optional)
- pandas, openpyxl, pydantic, python-dotenv, langchain-deepseek
- Testing: pytest, pytest-cov, ruff, black, mypy

## Project Structure

```text
docmeld/
├── docmeld/           # Source code
│   ├── bronze/        # PDF → JSON extraction
│   │   └── backends/  # ParserBackend implementations (pymupdf, docling)
│   ├── silver/        # JSON → JSONL page conversion
│   ├── gold/          # JSONL → AI-enriched metadata
│   ├── utils/         # Shared utilities
│   ├── parser.py      # Main DocMeldParser class
│   └── cli.py         # CLI entry point
├── tests/             # Unit, integration, contract tests
├── pyproject.toml
└── venv/
specs/                 # Feature specifications (speckit managed)
references/00-core/    # Reference docs, examples, use cases
```

## Commands

```bash
cd /Users/frank/A/DocMeld/docmeld
source venv/bin/activate
pytest tests/ -v                              # Run all tests
pytest tests/ -v --cov=docmeld               # With coverage
ruff check docmeld/                           # Lint
black --check docmeld/                        # Format check
mypy docmeld/                                 # Type check
```

## Code Style

- Python 3.9+ minimum, use `from __future__ import annotations`
- Black formatting (line-length=100)
- Ruff linting, Mypy strict mode
- TDD: write tests first per project constitution

## Git Branching Strategy

```
main                          ← stable, tested, merge target
├── 001-mvp-pdf-pipeline      ← completed MVP
├── 002-use-case-*            ← next use case feature branch
├── 003-use-case-*            ← ...
└── NNN-feature-name          ← each feature gets a numbered branch
```

- `main` is the integration branch. All feature branches merge to main after passing tests.
- Each use case / feature gets its own numbered branch via `/speckit.specify`.
- Never push directly to main. Always merge from a feature branch.

## Harness Coding Loop

This project uses a structured harness loop for autonomous development. Each use case from `references/00-core/use-cases.md` is processed through this pipeline:

### The Loop

```
┌─────────────────────────────────────────────────────┐
│              USE CASE BACKLOG                        │
│  references/00-core/use-cases.md                    │
│  Pick next unprocessed use case                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1: SPECIFY                                    │
│  /speckit.specify "NNN-use-case-short-name"         │
│  → Creates branch, writes specs/NNN-*/spec.md       │
│  → Validates spec quality checklist                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2: PLAN                                       │
│  /speckit.plan                                      │
│  → Generates plan.md with architecture + file map   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3: TASKS                                      │
│  /speckit.tasks                                     │
│  → Generates tasks.md with ordered, testable tasks  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 4: IMPLEMENT                                  │
│  /speckit.implement                                 │
│  → TDD: write tests first, then implement           │
│  → Mark tasks [x] as completed                      │
│  → Phase-by-phase execution                         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 5: TEST & EVALUATE                            │
│  pytest tests/ -v --cov=docmeld                     │
│  ruff check docmeld/ && black --check docmeld/      │
│  → All tests must pass                              │
│  → Coverage must not regress                        │
│  → If failures: fix and re-run (do not skip)        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 6: MERGE TO MAIN                              │
│  git checkout main                                  │
│  git merge NNN-feature-branch                       │
│  pytest tests/ -v  (verify post-merge)              │
│  → If merge conflicts: resolve, re-test             │
│  → If tests fail: fix on feature branch, re-merge   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              Pick next use case → STEP 1
```

### Loop Rules

1. **One use case at a time.** Complete the full loop before starting the next.
2. **Never skip testing.** Every step 4 ends with a full test run. Step 5 is the gate.
3. **Fix, don't skip.** If tests fail, fix the code. Do not mark tasks complete with failing tests.
4. **Branch per feature.** Each `/speckit.specify` creates a new numbered branch. Work stays isolated until merge.
5. **Main stays green.** Only merge to main after all tests pass on the feature branch.
6. **Track progress.** Update use-cases.md with status after each use case completes.

### Use Case Status Tracking

In `references/00-core/use-cases.md`, mark each use case with status:

- `[PENDING]` — not yet started
- `[IN PROGRESS]` — currently being implemented
- `[DONE]` — merged to main, all tests passing
- `[BLOCKED]` — needs clarification or external dependency

### Quick Reference: Running the Loop

```bash
# 1. Pick use case, create spec
/speckit.specify "NNN-use-case-description"

# 2. Generate plan
/speckit.plan

# 3. Generate tasks
/speckit.tasks

# 4. Implement all tasks
/speckit.implement

# 5. Test & evaluate
cd /Users/frank/A/DocMeld/docmeld && source venv/bin/activate
pytest tests/ -v --cov=docmeld --cov-report=term-missing
ruff check docmeld/
black --check docmeld/

# 6. Merge to main (after all tests pass)
git checkout main
git merge NNN-feature-branch
pytest tests/ -v
```

## Autonomy Rules

- For tasks < 200 lines changed: implement fully autonomously
- For tasks > 200 lines: create implementation plan first, get approval
- Never modify files outside the current task's declared scope
- On ambiguity: make the conservative choice, document in commit message

## Quality Gates (before every commit)

- `pytest tests/` — must pass 100%
- `ruff check docmeld/` — zero errors
- No secrets in committed files (.env, credentials, API keys)

## Recent Changes
- 006-mvp-doc-pipeline: Added Python 3.9+ + docling>=2.0.0, soffice LibreOffice bridge, 10 element types (chart, formula, header, footer, footnote, endnote), --backend auto CLI flag

- 002-paper-batch-categorize: Added Python 3.9+ + PyMuPDF (fitz), pymupdf4llm, pydantic, langchain-deepseek (all existing)

- 001-mvp-pdf-pipeline: MVP Bronze→Silver→Gold pipeline, 144 tests
  - ParserBackend abstraction (pymupdf + docling backends)
  - element_id, parent_id, table_data schema enhancements
  - --backend CLI flag for engine selection
