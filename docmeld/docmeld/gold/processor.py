"""Gold stage processor - enrich silver JSONL with AI metadata."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from docmeld.gold.deepseek_client import DeepSeekClient
from docmeld.gold.metadata_extractor import MetadataExtractor
from docmeld.gold.provider import LLMProvider
from docmeld.silver.page_models import GoldResult

logger = logging.getLogger("docmeld")


class GoldProcessor:
    """Orchestrates gold-level processing: silver JSONL to enriched JSONL."""

    def __init__(
        self,
        api_key: str,
        endpoint: str | None = None,
        temperature: float = 1.0,
        provider: LLMProvider | None = None,
    ) -> None:
        self.client: LLMProvider = provider or DeepSeekClient(
            api_key=api_key,
            endpoint=endpoint,
            temperature=temperature,
        )
        self.extractor = MetadataExtractor(self.client)

    def process(self, silver_jsonl_path: str) -> GoldResult:
        """Enrich a silver JSONL file with AI-generated metadata.

        Creates a new file with '_gold' suffix preserving the original.

        Args:
            silver_jsonl_path: Path to the silver JSONL file.

        Returns:
            GoldResult with output path and enrichment statistics.
        """
        jsonl_path = Path(silver_jsonl_path)
        if not jsonl_path.exists():
            msg = f"Silver JSONL not found: {silver_jsonl_path}"
            raise FileNotFoundError(msg)

        # Output path with _gold suffix
        gold_path = jsonl_path.with_name(jsonl_path.stem + "_gold" + jsonl_path.suffix)

        # Idempotency check
        if gold_path.exists():
            with open(gold_path) as f:
                pages = [json.loads(line) for line in f if line.strip()]
            if pages and "description" in pages[0].get("metadata", {}):
                return GoldResult(
                    output_path=str(gold_path),
                    pages_enriched=sum(
                        1 for p in pages if not p.get("metadata", {}).get("gold_processing_failed")
                    ),
                    pages_failed=sum(
                        1 for p in pages if p.get("metadata", {}).get("gold_processing_failed")
                    ),
                    skipped=True,
                )

        # Load silver pages
        with open(jsonl_path, encoding="utf-8") as f:
            silver_lines = [line for line in f if line.strip()]

        pages_enriched = 0
        pages_failed = 0

        with open(gold_path, "w", encoding="utf-8") as out:
            for i, line in enumerate(silver_lines, 1):
                page = json.loads(line)
                page_content = page.get("page_content", "")

                logger.info(f"Gold: enriching page {i}/{len(silver_lines)}")

                try:
                    metadata = self.extractor.extract(page_content)
                except Exception as e:
                    logger.error(f"Gold extraction failed for page {i}: {e}")
                    metadata = {
                        "description": "",
                        "keywords": [],
                        "gold_processing_failed": True,
                    }

                if metadata.get("gold_processing_failed"):
                    pages_failed += 1
                else:
                    pages_enriched += 1

                # Merge metadata
                page["metadata"].update(metadata)
                out.write(json.dumps(page, ensure_ascii=False) + "\n")

        logger.info(f"Gold: {jsonl_path.name} → {pages_enriched} enriched, {pages_failed} failed")

        return GoldResult(
            output_path=str(gold_path),
            pages_enriched=pages_enriched,
            pages_failed=pages_failed,
            skipped=False,
        )
