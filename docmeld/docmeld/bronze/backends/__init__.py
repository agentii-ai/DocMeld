"""Parser backend abstraction for PDF element extraction."""

from __future__ import annotations

from typing import Any, Protocol


class ParserBackend(Protocol):
    """Protocol for PDF parsing backends."""

    def extract_elements(self, pdf_path: str, output_dir: str) -> list[dict[str, Any]]:
        """Extract raw elements from a PDF file.

        Returns elements without element_id, parent_id, or table summaries —
        those are applied by the shared post-processing in element_extractor.
        """
        ...
