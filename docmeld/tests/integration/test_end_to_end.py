"""End-to-end integration tests for the full pipeline."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


class TestEndToEnd:
    def test_single_pdf_bronze_silver(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        """Test bronze → silver pipeline without gold (no API key needed)."""
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor

        shutil.copy(sample_simple_pdf, tmp_path / "report.pdf")

        # Bronze
        bronze = BronzeProcessor()
        bronze_result = bronze.process_file(str(tmp_path / "report.pdf"))
        assert Path(bronze_result.output_path).exists()

        # Verify bronze JSON
        with open(bronze_result.output_path) as f:
            elements = json.load(f)
        assert len(elements) > 0
        assert all("type" in e and "page_no" in e for e in elements)

        # Silver
        silver = SilverProcessor()
        silver_result = silver.process(bronze_result.output_path)
        assert Path(silver_result.output_path).exists()

        # Verify silver JSONL
        with open(silver_result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]
        assert len(pages) == 3  # sample_simple has 3 pages
        for page in pages:
            assert "metadata" in page
            assert "page_content" in page
            assert "uuid" in page["metadata"]
            assert "source" in page["metadata"]
            assert page["metadata"]["page_no"].startswith("page")

    def test_batch_bronze_silver(
        self, sample_simple_pdf: Path, sample_complex_pdf: Path, tmp_path: Path
    ) -> None:
        """Test batch processing through bronze and silver."""
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor

        shutil.copy(sample_simple_pdf, tmp_path / "doc1.pdf")
        shutil.copy(sample_complex_pdf, tmp_path / "doc2.pdf")

        # Bronze batch
        bronze = BronzeProcessor()
        result = bronze.process_folder(str(tmp_path))
        assert result.total_files == 2
        assert result.successful == 2

        # Silver for each
        silver = SilverProcessor()
        for subdir in sorted(tmp_path.iterdir()):
            if subdir.is_dir():
                json_files = list(subdir.glob("*.json"))
                for jf in json_files:
                    silver_result = silver.process(str(jf))
                    assert Path(silver_result.output_path).exists()
                    assert silver_result.page_count > 0

    def test_idempotency_full_pipeline(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        """Test that re-running the pipeline skips existing outputs."""
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor

        shutil.copy(sample_simple_pdf, tmp_path / "report.pdf")

        bronze = BronzeProcessor()
        silver = SilverProcessor()

        # First run
        b1 = bronze.process_file(str(tmp_path / "report.pdf"))
        s1 = silver.process(b1.output_path)
        assert not b1.skipped
        assert not s1.skipped

        # Second run — should skip
        b2 = bronze.process_file(str(tmp_path / "report.pdf"))
        s2 = silver.process(b2.output_path)
        assert b2.skipped
        assert s2.skipped

    def test_gold_with_mock_api(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        """Test full pipeline including gold stage with mocked API."""
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.gold.processor import GoldProcessor
        from docmeld.silver.processor import SilverProcessor

        shutil.copy(sample_simple_pdf, tmp_path / "report.pdf")

        # Bronze + Silver
        bronze = BronzeProcessor()
        bronze_result = bronze.process_file(str(tmp_path / "report.pdf"))
        silver = SilverProcessor()
        silver_result = silver.process(bronze_result.output_path)

        # Gold with mock
        def mock_extract(page_content: str) -> dict:  # type: ignore[type-arg]
            return {
                "description": f"Summary of page content",
                "keywords": ["test", "document"],
            }

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = mock_extract

            gold = GoldProcessor(api_key="test_key")
            gold_result = gold.process(silver_result.output_path)

        assert Path(gold_result.output_path).exists()
        assert gold_result.output_path.endswith("_gold.jsonl")
        assert gold_result.pages_enriched == 3
        assert gold_result.pages_failed == 0

        # Verify gold output
        with open(gold_result.output_path) as f:
            gold_pages = [json.loads(line) for line in f if line.strip()]
        for page in gold_pages:
            assert "description" in page["metadata"]
            assert "keywords" in page["metadata"]

    def test_log_file_created(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        """Test that processing creates a timestamped log file."""
        import os

        from docmeld.utils.logging import setup_logging

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            logger = setup_logging()
            logger.info("Test log entry")
            log_files = list(tmp_path.glob("docmeld_*.log"))
            assert len(log_files) == 1
            assert "docmeld_" in log_files[0].name
            logger.handlers.clear()
        finally:
            os.chdir(original_cwd)


class TestEndToEndPptx:
    """T064: PPTX bronze → silver end-to-end traversal (no API key needed)."""

    def test_single_pptx_bronze_silver(self, tmp_path: Path) -> None:
        import shutil
        from docmeld.bronze.processor import BronzeProcessor
        from docmeld.silver.processor import SilverProcessor

        src = Path(__file__).resolve().parents[3] / "samples" / "ppt" / "sample_pptx_basic.pptx"
        if not src.exists():
            pytest.skip("sample_pptx_basic.pptx not found")
        shutil.copy(src, tmp_path / "deck.pptx")

        bronze_result = BronzeProcessor().process_file(str(tmp_path / "deck.pptx"), backend="auto")
        assert Path(bronze_result.output_path).exists()
        with open(bronze_result.output_path) as f:
            elements = json.load(f)
        assert elements and all("type" in e and "page_no" in e for e in elements)

        silver_result = SilverProcessor().process(bronze_result.output_path)
        assert Path(silver_result.output_path).exists()
        with open(silver_result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]
        assert pages
        assert all(p["metadata"]["page_no"].startswith("page") for p in pages)
