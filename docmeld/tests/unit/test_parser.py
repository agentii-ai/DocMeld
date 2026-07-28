"""Tests for DocMeldParser orchestrator.

Phase E TDD: This file is written FIRST. Tests for single-file process_all
gold-failure reporting MUST fail before T054–T055 fix the hardcoded values.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docmeld.parser import DocMeldParser
from docmeld.silver.page_models import ProcessingResult


class TestProcessAllSingleFile:
    """Verify single-file process_all behavior."""

    def test_reports_gold_failure(self, tmp_path: Path) -> None:
        """process_all reports failed=1 when gold stage raises an exception.

        Currently process_all hardcodes successful=1, failed=0 regardless of
        gold failure. This test verifies the fix (T055).
        """
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor
        from docmeld.gold.processor import GoldProcessor
        from docmeld.silver.page_models import BronzeResult, SilverResult

        # Use Dict[str, str] for path; parser only checks _is_folder
        parser = DocMeldParser(str(tmp_path / "nonexistent.pdf"))

        bronze_out = tmp_path / "test_out" / "test.json"
        bronze_out.parent.mkdir(parents=True, exist_ok=True)
        bronze_out.write_text("{}")

        silver_out = tmp_path / "test_out" / "test.jsonl"
        silver_out.write_text("{}")

        with patch.object(BronzeProcessor, "process_file",
                          return_value=BronzeResult(
                              output_path=str(bronze_out),
                              output_dir=str(bronze_out.parent),
                              element_count=1,
                              page_count=1,
                          )), \
             patch.object(SilverProcessor, "process",
                          return_value=SilverResult(
                              output_path=str(silver_out),
                              page_count=1,
                          )), \
             patch.object(GoldProcessor, "process",
                          side_effect=RuntimeError("API unreachable")):

            result = parser.process_all()

            assert isinstance(result, ProcessingResult)
            assert result.total_files == 1
            assert result.successful == 0, (
                f"Expected successful=0 when gold fails, got {result.successful}"
            )
            assert result.failed == 1, (
                f"Expected failed=1 when gold fails, got {result.failed}"
            )

    def test_reports_gold_success(self, tmp_path: Path) -> None:
        """process_all reports successful=1 when all stages pass."""
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor
        from docmeld.gold.processor import GoldProcessor
        from docmeld.silver.page_models import BronzeResult, SilverResult, GoldResult

        parser = DocMeldParser(str(tmp_path / "nonexistent.pdf"))

        bronze_out = tmp_path / "test_out" / "test.json"
        bronze_out.parent.mkdir(parents=True, exist_ok=True)
        bronze_out.write_text("{}")

        silver_out = tmp_path / "test_out" / "test.jsonl"
        silver_out.write_text("{}")

        gold_out = tmp_path / "test_out" / "test_gold.jsonl"
        gold_out.write_text("{}")

        with patch.object(BronzeProcessor, "process_file",
                          return_value=BronzeResult(
                              output_path=str(bronze_out),
                              output_dir=str(bronze_out.parent),
                              element_count=1,
                              page_count=1,
                          )), \
             patch.object(SilverProcessor, "process",
                          return_value=SilverResult(
                              output_path=str(silver_out),
                              page_count=1,
                          )), \
             patch.object(GoldProcessor, "process",
                          return_value=GoldResult(
                              output_path=str(gold_out),
                              pages_enriched=1,
                              pages_failed=0,
                              skipped=False,
                          )):

            result = parser.process_all()

            assert result.total_files == 1
            assert result.successful == 1
            assert result.failed == 0


class TestProviderInjection:
    """Verify LLMProvider injection through DocMeldParser (cross-check from Phase D)."""

    def test_provider_passed_to_gold_processor(self, tmp_path: Path) -> None:
        """Injected provider is forwarded to GoldProcessor."""
        from docmeld.gold.provider import LLMProvider

        class DummyProvider:
            def extract_metadata(self, page_content: str) -> dict:
                return {"description": "x", "keywords": []}
            def generate(self, prompt: str) -> str:
                return "ok"
            def categorize(self, prompt: str) -> str:
                return "ok"

        provider = DummyProvider()
        parser = DocMeldParser("nonexistent.pdf", provider=provider)
        client = parser._get_client()
        assert client is provider, "_get_client should return injected provider"
