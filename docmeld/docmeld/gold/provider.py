"""LLM provider abstraction for the gold stage and knowledge-generation features.

DocMeld's AI-dependent stages (gold enrichment, categorize, prd, workflow, skills)
talk to a language model through this narrow ``LLMProvider`` protocol rather than a
concrete client. The bundled :class:`docmeld.gold.deepseek_client.DeepSeekClient`
implements it, but any object exposing the same three methods can be injected into
:class:`docmeld.parser.DocMeldParser`, making the provider swappable.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Structural interface for a language-model backend used by DocMeld.

    Implementations are expected to handle their own retries and to return plain
    Python values (no provider-specific response objects leak through this seam).
    """

    def extract_metadata(self, page_content: str) -> dict[str, Any]:
        """Return ``{"description": str, "keywords": list[str]}`` for a page."""
        ...

    def generate(self, prompt: str) -> str:
        """Return free-form text for a prompt (PRD / workflow / skills generation)."""
        ...

    def categorize(self, prompt: str) -> str:
        """Return the raw text response for a categorization prompt."""
        ...


__all__ = ["LLMProvider"]
