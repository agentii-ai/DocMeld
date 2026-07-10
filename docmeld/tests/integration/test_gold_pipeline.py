"""Integration tests for gold pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestGoldPipeline:
    def _create_silver_jsonl(self, tmp_path: Path) -> Path:
        """Create a silver JSONL file for testing."""
        output_dir = tmp_path / "test_doc_abc123"
        output_dir.mkdir()
        jsonl_path = output_dir / "test_doc_abc123.jsonl"

        pages = [
            {
                "metadata": {
                    "uuid": "uuid-1",
                    "source": "test_doc_abc123.pdf",
                    "page_no": "page1",
                    "session_title": "# Report\n",
                },
                "page_content": "# Report\n\nThis is about revenue growth and EBITDA margins.",
            },
            {
                "metadata": {
                    "uuid": "uuid-2",
                    "source": "test_doc_abc123.pdf",
                    "page_no": "page2",
                    "session_title": "# Report\n## Financials\n",
                },
                "page_content": "## Financials\n\nQuarterly results show strong performance.",
            },
        ]

        with open(jsonl_path, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")

        return jsonl_path

    def _mock_extract(self, page_content: str) -> dict:  # type: ignore[type-arg]
        """Mock metadata extraction."""
        return {
            "description": f"Page about: {page_content[:30]}",
            "keywords": ["test", "mock"],
        }

    def test_creates_gold_jsonl_with_suffix(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_silver_jsonl(tmp_path)

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = self._mock_extract

            processor = GoldProcessor(api_key="test_key")
            result = processor.process(str(jsonl_path))

        assert result.output_path.endswith("_gold.jsonl")
        assert Path(result.output_path).exists()

    def test_preserves_original_silver(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_silver_jsonl(tmp_path)
        original_content = jsonl_path.read_text()

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = self._mock_extract

            processor = GoldProcessor(api_key="test_key")
            processor.process(str(jsonl_path))

        assert jsonl_path.read_text() == original_content

    def test_adds_description_and_keywords(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_silver_jsonl(tmp_path)

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = self._mock_extract

            processor = GoldProcessor(api_key="test_key")
            result = processor.process(str(jsonl_path))

        with open(result.output_path) as f:
            for line in f:
                if not line.strip():
                    continue
                page = json.loads(line)
                assert "description" in page["metadata"]
                assert "keywords" in page["metadata"]
                assert isinstance(page["metadata"]["keywords"], list)

    def test_idempotency(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_silver_jsonl(tmp_path)

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = self._mock_extract

            processor = GoldProcessor(api_key="test_key")
            result1 = processor.process(str(jsonl_path))
            assert not result1.skipped

            result2 = processor.process(str(jsonl_path))
            assert result2.skipped

    def test_partial_failure_continues(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_silver_jsonl(tmp_path)
        call_count = 0

        def failing_first(page_content: str) -> dict:  # type: ignore[type-arg]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("API error")
            return {"description": "OK", "keywords": ["test"]}

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = failing_first

            processor = GoldProcessor(api_key="test_key")
            result = processor.process(str(jsonl_path))

        assert result.pages_enriched == 1
        assert result.pages_failed == 1

        with open(result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]

        failed_page = pages[0]
        assert failed_page["metadata"].get("gold_processing_failed") is True


class TestGoldPptxPipeline:
    """T062/T063: gold enrichment consumes PPTX silver JSONL unchanged."""

    def _create_pptx_silver(self, tmp_path: Path) -> Path:
        output_dir = tmp_path / "deck_abc123"
        output_dir.mkdir()
        jsonl_path = output_dir / "deck_abc123.jsonl"
        pages = [
            {
                "metadata": {
                    "uuid": "u-1", "source": "deck_abc123.pptx",
                    "page_no": "page1", "session_title": "# Q4 Strategy\n",
                },
                "page_content": "# Q4 Strategy\n\n[[Chart1 type=bar]]\n| Q | Rev |\n| --- | --- |\n| Q1 | 100 |\n[/Chart1]\n[Notes]\nEmphasize growth\n[/Notes]",
            },
            {
                "metadata": {
                    "uuid": "u-2", "source": "deck_abc123.pptx",
                    "page_no": "page2", "session_title": "# Q4 Strategy\n",
                },
                "page_content": "[[SmartArt1 type=process]]\n- Plan\n- Build\n- Ship\n[/SmartArt1]",
            },
        ]
        with open(jsonl_path, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")
        return jsonl_path

    def test_gold_enriches_each_slide(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_pptx_silver(tmp_path)

        def mock_extract(page_content: str) -> dict:  # type: ignore[type-arg]
            return {"description": f"About: {page_content[:20]}", "keywords": ["q4", "strategy"]}

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            instance = MockExtractor.return_value
            instance.extract.side_effect = mock_extract
            processor = GoldProcessor(api_key="fake-key")
            result = processor.process(str(jsonl_path))

        out = Path(result.output_path)
        assert out.exists()
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            md = json.loads(line)["metadata"]
            assert "description" in md
            assert isinstance(md["keywords"], list) and md["keywords"]

    def test_gold_idempotent_on_pptx(self, tmp_path: Path) -> None:
        from docmeld.gold.processor import GoldProcessor

        jsonl_path = self._create_pptx_silver(tmp_path)

        def mock_extract(page_content: str) -> dict:  # type: ignore[type-arg]
            return {"description": "x", "keywords": ["k"]}

        with patch("docmeld.gold.processor.MetadataExtractor") as MockExtractor:
            MockExtractor.return_value.extract.side_effect = mock_extract
            proc = GoldProcessor(api_key="fake-key")
            r1 = proc.process(str(jsonl_path))
            r2 = proc.process(str(jsonl_path))
        assert Path(r1.output_path).exists()
        # second run skips (gold file already present)
        assert getattr(r2, "skipped", False) is True
