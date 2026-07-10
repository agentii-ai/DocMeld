"""Integration tests for silver pipeline."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


class TestSilverPipeline:
    def _create_bronze_json(self, tmp_path: Path) -> Path:
        """Helper to create a bronze JSON file for testing."""
        elements = [
            {"type": "title", "level": 0, "content": "Report Title", "page_no": 1},
            {"type": "text", "content": "Introduction paragraph.", "page_no": 1},
            {"type": "title", "level": 1, "content": "Section A", "page_no": 1},
            {"type": "text", "content": "Section A content.", "page_no": 1},
            {"type": "table", "content": "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |", "summary": "Items: A", "page_no": 2},
            {"type": "text", "content": "After table text.", "page_no": 2},
            {"type": "title", "level": 1, "content": "Section B", "page_no": 3},
            {"type": "text", "content": "Section B content.", "page_no": 3},
        ]
        output_dir = tmp_path / "test_doc_abc123"
        output_dir.mkdir()
        json_path = output_dir / "test_doc_abc123.json"
        with open(json_path, "w") as f:
            json.dump(elements, f)
        return json_path

    def test_creates_jsonl_with_one_line_per_page(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result = processor.process(str(json_path))

        assert result.page_count == 3
        assert Path(result.output_path).exists()

        with open(result.output_path) as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 3

    def test_each_page_has_metadata(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result = processor.process(str(json_path))

        with open(result.output_path) as f:
            for line in f:
                if not line.strip():
                    continue
                page = json.loads(line)
                assert "metadata" in page
                assert "page_content" in page
                assert "uuid" in page["metadata"]
                assert "source" in page["metadata"]
                assert "page_no" in page["metadata"]
                assert "session_title" in page["metadata"]

    def test_title_hierarchy_across_pages(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result = processor.process(str(json_path))

        with open(result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]

        # Page 2 should include title hierarchy from page 1
        page2_content = pages[1]["page_content"]
        assert "Report Title" in pages[1]["metadata"]["session_title"]

    def test_global_table_numbering(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result = processor.process(str(json_path))

        with open(result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]

        # Page 2 has a table — should be Table1
        page2_content = pages[1]["page_content"]
        assert "[[Table1]]" in page2_content

    def test_idempotency(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result1 = processor.process(str(json_path))
        assert not result1.skipped

        result2 = processor.process(str(json_path))
        assert result2.skipped

    def test_page_no_format(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        json_path = self._create_bronze_json(tmp_path)
        processor = SilverProcessor()
        result = processor.process(str(json_path))

        with open(result.output_path) as f:
            pages = [json.loads(line) for line in f if line.strip()]

        assert pages[0]["metadata"]["page_no"] == "page1"
        assert pages[1]["metadata"]["page_no"] == "page2"
        assert pages[2]["metadata"]["page_no"] == "page3"


class TestSilverPptxPipeline:
    """T057/T058: silver processing of PPTX bronze output."""

    def _make_pptx_bronze(self, tmp_path: Path) -> Path:
        elements = [
            {"type": "title", "level": 0, "content": "Slide One", "page_no": 1,
             "element_id": "e_0001", "parent_id": "", "hidden": False},
            {"type": "text", "content": "Body text", "page_no": 1,
             "element_id": "e_0002", "parent_id": "e_0001", "hidden": False},
            {"type": "chart", "chart_type": "bar", "content": "| a |\n| --- |\n| 1 |",
             "image": "", "image_name": "c.png", "page_no": 1,
             "element_id": "e_0003", "parent_id": "e_0001", "hidden": False},
            {"type": "notes", "content": "Speaker note", "page_no": 1,
             "element_id": "e_0004", "parent_id": "", "hidden": False},
            {"type": "comment", "content": "Please review", "author": "JR", "page_no": 1,
             "element_id": "e_0005", "parent_id": "", "hidden": False},
            {"type": "title", "level": 0, "content": "Hidden Slide", "page_no": 2,
             "element_id": "e_0006", "parent_id": "", "hidden": True},
            {"type": "smartart", "smartart_type": "process", "content": "- A\n- B",
             "image": "", "image_name": "s.png", "page_no": 2,
             "element_id": "e_0007", "parent_id": "", "hidden": True},
        ]
        d = tmp_path / "deck_abc123"
        d.mkdir()
        jp = d / "deck_abc123.json"
        jp.write_text(json.dumps(elements), encoding="utf-8")
        return jp

    def test_one_line_per_slide_with_markers(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        bronze = self._make_pptx_bronze(tmp_path)
        result = SilverProcessor().process(str(bronze))

        lines = Path(result.output_path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2  # two slides

        page1 = json.loads(lines[0])
        assert page1["metadata"]["page_no"] == "page1"
        content = page1["page_content"]
        assert "[[Chart1 type=bar]]" in content
        assert "[Notes]" in content and "Speaker note" in content
        assert "[Comment: JR]" in content

        page2 = json.loads(lines[1])
        assert page2["metadata"]["page_no"] == "page2"
        assert "[[SmartArt1 type=process]]" in page2["page_content"]

    def test_hidden_slide_retained_in_silver(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        bronze = self._make_pptx_bronze(tmp_path)
        result = SilverProcessor().process(str(bronze))
        lines = Path(result.output_path).read_text(encoding="utf-8").strip().split("\n")
        pages = {json.loads(x)["metadata"]["page_no"] for x in lines}
        assert "page2" in pages  # hidden slide still emitted

    def test_silver_skip_reprocessing(self, tmp_path: Path) -> None:
        from docmeld.silver.processor import SilverProcessor

        bronze = self._make_pptx_bronze(tmp_path)
        proc = SilverProcessor()
        r1 = proc.process(str(bronze))
        assert r1.skipped is False
        r2 = proc.process(str(bronze))
        assert r2.skipped is True

    def test_cross_pipeline_jsonl_contract(self, tmp_path: Path) -> None:
        """SC-016: PPT silver JSONL matches the PDF/DOC contract shape."""
        from docmeld.silver.processor import SilverProcessor

        bronze = self._make_pptx_bronze(tmp_path)
        result = SilverProcessor().process(str(bronze))
        for line in Path(result.output_path).read_text(encoding="utf-8").strip().split("\n"):
            obj = json.loads(line)
            assert set(obj.keys()) == {"metadata", "page_content"}
            md = obj["metadata"]
            for key in ("uuid", "source", "page_no", "session_title"):
                assert key in md
            assert md["page_no"].startswith("page")
