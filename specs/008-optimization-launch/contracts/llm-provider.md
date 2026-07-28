# Interface Contract: LLMProvider

**Status**: Proposed (Phase D) · **Spec**: [spec.md](../spec.md) · **Data Model**: [data-model.md](../data-model.md)

## Overview

The `LLMProvider` Protocol is the swappable LLM backend contract for DocMeld's gold stage. Any object
structurally conforming to this Protocol can be injected into `DocMeldParser` to replace the default
DeepSeek backend.

## Protocol

```python
from typing import Any, Protocol

class LLMProvider(Protocol):
    """Gold-stage LLM backend for metadata extraction, text generation, and categorization."""

    def extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract structured metadata from aggregated document content.
        
        Args:
            content: Aggregated document text (up to MAX_CONTENT_CHARS, 60/40 head/tail split).
        
        Returns:
            dict with metadata fields (document_type, topics, summary, keywords, etc.).
        """
        ...

    def generate(self, prompt: str) -> str:
        """Generate free-form text from a prompt.
        
        Used by PRD, workflow, and skills generators. Replaces the misnamed
        `generate_prd` (which is not PRD-specific).
        
        Args:
            prompt: The complete prompt string to send to the LLM.
        
        Returns:
            Raw text response from the LLM.
        """
        ...

    def categorize(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Categorize papers/documents into thematic groups.
        
        Args:
            papers: List of paper dicts with content and metadata.
        
        Returns:
            List of categorized paper dicts with assigned categories.
        """
        ...
```

## Conformance Rules

1. **Structural subtyping only** — no inheritance required. Any object with the three methods matches.
2. **No side effects on environment** — providers read their own config (env vars, constructor args)
   but do NOT mutate global state (log handlers, env vars, sys.path).
3. **Default behavior preserved** — when `provider=None` is passed to `DocMeldParser`, a
   `DeepSeekClient` is constructed from `DEEPSEEK_API_KEY` / `DEEPSEEK_API_BASE` env vars. This
   path is byte-for-byte identical to the current behavior.
4. **Type annotations** — all fields currently typed `client: Any` become `client: LLMProvider`.
5. **Error handling** — providers raise exceptions on failure; callers in gold stage handle them
   (no bare `except:`).

## Built-in Implementation

| Provider | Module | Notes |
|---|---|---|
| `DeepSeekClient` | `docmeld.gold.deepseek_client` | Default. Reads `DEEPSEEK_API_KEY`, `DEEPSEEK_API_BASE`. Model name `deepseek-chat` is a constructor default. |

## Injection Seam

```python
from docmeld import DocMeldParser
from docmeld.gold.provider import LLMProvider

# Default: DeepSeek from env
parser = DocMeldParser()

# Custom: inject any LLMProvider
class MyProvider:
    def extract_metadata(self, content: str) -> dict: ...
    def generate(self, prompt: str) -> str: ...
    def categorize(self, papers: list) -> list: ...

parser = DocMeldParser(provider=MyProvider())
```

## Verification

1. `from docmeld.gold.provider import LLMProvider` imports without error.
2. A dummy object with the three methods passes `isinstance(obj, LLMProvider)`.
3. Dummy provider injects into `DocMeldParser` and drives `process_prd`/`process_workflow`/
   `process_skills` without network calls.
4. Default `DocMeldParser()` still works identically (DeepSeek from env).
