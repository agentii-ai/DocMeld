# Data Model: OSS-Standard Optimization & Launch Readiness

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-07-28

This is a non-feature hygiene release. No new persistent data entities are introduced. The only new interface contract is the `LLMProvider` Protocol.

## New: LLMProvider Protocol

**File**: `docmeld/docmeld/gold/provider.py` (new)

### Protocol Definition

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for swappable LLM backends in DocMeld gold stage."""

    def extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract structured metadata from document content."""
        ...

    def generate(self, prompt: str) -> str:
        """Generate free-form text from a prompt."""
        ...

    def categorize(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Categorize papers into thematic groups."""
        ...
```

### Implemented By

| Class | File | Status |
|---|---|---|
| `DeepSeekClient` | `docmeld/docmeld/gold/deepseek_client.py` | Existing, structurally conforms after rename: `generate_prd` → `generate` (with deprecated alias) |

### Consumers (updated from `client: Any` → `client: LLMProvider`)

| Module | File | Current Type | New Type |
|---|---|---|---|
| PRD generator | `docmeld/docmeld/prd/generator.py` | `Any` | `LLMProvider` |
| Workflow generator | `docmeld/docmeld/workflow/generator.py` | `Any` | `LLMProvider` |
| Skills generator | `docmeld/docmeld/skills/generator.py` | `Any` | `LLMProvider` |
| Categorizer | `docmeld/docmeld/categorize/categorizer.py` | `Any` | `LLMProvider` |

### Injection Seam

`DocMeldParser.__init__` gains an optional `provider: LLMProvider | None = None` parameter. When `None` (default), a `DeepSeekClient` is constructed from environment variables — byte-for-byte identical to current behavior. When provided, it is threaded to all 5 instantiation sites.

## Changed: Parser Return Types (already fixed in Phase C)

`parser.py` return annotations now resolve via `TYPE_CHECKING` imports:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docmeld.prd.models import PrdResult
    from docmeld.workflow.models import WorkflowResult
    from docmeld.skills.models import SkillsResult
```

## Changed: BronzeElement (already fixed in Phase C)

Runtime-safe union for Python 3.9:

```python
from typing import Union
from typing_extensions import TypeAlias

BronzeElement: TypeAlias = Union[TitleElement, TextElement, TableElement, ...]
```

## Removed Entities

| Entity | Location | Reason |
|---|---|---|
| `DocMeldParser.output_dir` | `parser.py` | Stored, never used |
| `gold_failed` variable | `parser.py` | Set, never read |
| `_merge_categories` | `categorize/categorizer.py` | Never called |
| Personal scripts (5 files) | `docmeld/docmeld/` → `docmeld/scripts/` | Not library code, excluded from wheel |
| `summarize_rl.py` | repo root → `docmeld/scripts/` | Not library code |

## New Shared Utilities

| Module | Function | Replaces |
|---|---|---|
| `utils/silver_io.py` | `load_silver_content(jsonl_path)` | 4 verbatim copies in prd/workflow/skills/aggregator |
| `utils/content.py` | `aggregate_content(pages, max_chars, head_ratio)` | 3 copies of the 30k/60-40 split logic |
| `utils/text.py` | `strip_code_fences(text)` | 6+ copies in deepseek_client, prd, workflow, skills, categorizer |
