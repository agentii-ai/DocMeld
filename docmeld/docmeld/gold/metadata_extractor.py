"""Metadata extractor for gold stage - LLMProvider-agnostic."""

from __future__ import annotations

import logging
from typing import Any

from docmeld.gold.provider import LLMProvider

logger = logging.getLogger("docmeld")


class MetadataExtractor:
    """Extracts description and keywords from page content using an LLMProvider."""

    def __init__(self, client: LLMProvider) -> None:
        self.client = client

    def extract(self, page_content: str) -> dict[str, Any]:
        """Extract metadata from page content.

        Args:
            page_content: Markdown-formatted page content.

        Returns:
            Dict with 'description', 'keywords', and optionally
            'gold_processing_failed'.
        """
        if not page_content.strip():
            return {
                "description": "Blank page",
                "keywords": [],
            }

        try:
            result = self.client.extract_metadata(page_content)
            return {
                "description": result.get("description", ""),
                "keywords": result.get("keywords", []),
            }
        except Exception as e:
            logger.error(f"Gold extraction failed: {e}")
            return {
                "description": "",
                "keywords": [],
                "gold_processing_failed": True,
            }
