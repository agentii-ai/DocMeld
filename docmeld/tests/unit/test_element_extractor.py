"""Unit tests for element extractor."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


class TestParseMarkdownToElements:
    def test_title_detection(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "# Main Title\n\nSome text here."
        elements = parse_markdown_to_elements(md, page_no=1)
        titles = [e for e in elements if e["type"] == "title"]
        assert len(titles) == 1
        assert titles[0]["content"] == "Main Title"
        assert titles[0]["level"] == 0  # H1 = level 0

    def test_title_level_counting(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "## Sub Title\n\n### Sub Sub"
        elements = parse_markdown_to_elements(md, page_no=1)
        titles = [e for e in elements if e["type"] == "title"]
        assert titles[0]["level"] == 1  # H2 = level 1
        assert titles[1]["level"] == 2  # H3 = level 2

    def test_table_detection(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nAfter table."
        elements = parse_markdown_to_elements(md, page_no=1)
        tables = [e for e in elements if e["type"] == "table"]
        assert len(tables) == 1
        assert "| A | B |" in tables[0]["content"]

    def test_text_extraction(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "Just a paragraph of text.\nWith two lines."
        elements = parse_markdown_to_elements(md, page_no=1)
        texts = [e for e in elements if e["type"] == "text"]
        assert len(texts) >= 1
        assert "Just a paragraph" in texts[0]["content"]

    def test_element_ordering(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "# Title\n\nParagraph text.\n\n| A |\n|---|\n| 1 |\n\nMore text."
        elements = parse_markdown_to_elements(md, page_no=1)
        types = [e["type"] for e in elements]
        assert types[0] == "title"
        assert "text" in types
        assert "table" in types

    def test_page_no_assigned(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "# Title\n\nText."
        elements = parse_markdown_to_elements(md, page_no=5)
        for elem in elements:
            assert elem["page_no"] == 5

    def test_empty_content_skipped(self) -> None:
        from docmeld.bronze.element_extractor import parse_markdown_to_elements

        md = "\n\n\n"
        elements = parse_markdown_to_elements(md, page_no=1)
        assert len(elements) == 0


class TestTableSummary:
    def test_generates_summary_from_first_column(self) -> None:
        from docmeld.bronze.element_extractor import generate_table_summary

        table_md = "| Metric | Value |\n|--------|-------|\n| Revenue | $100 |\n| EBITDA | $50 |"
        summary = generate_table_summary(table_md)
        assert "Revenue" in summary
        assert "EBITDA" in summary

    def test_empty_table_returns_empty(self) -> None:
        from docmeld.bronze.element_extractor import generate_table_summary

        summary = generate_table_summary("")
        assert summary == ""

    def test_items_prefix(self) -> None:
        from docmeld.bronze.element_extractor import generate_table_summary

        table_md = "| Name | Val |\n|------|-----|\n| A | 1 |\n| B | 2 |"
        summary = generate_table_summary(table_md)
        assert summary.startswith("Items: ")


class TestParseTableData:
    def test_basic_table(self) -> None:
        from docmeld.bronze.element_extractor import parse_table_data

        table_md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        result = parse_table_data(table_md)
        assert result["headers"] == ["A", "B"]
        assert result["rows"] == [["1", "2"], ["3", "4"]]
        assert result["num_rows"] == 2
        assert result["num_cols"] == 2

    def test_empty_table(self) -> None:
        from docmeld.bronze.element_extractor import parse_table_data

        result = parse_table_data("")
        assert result == {"headers": [], "rows": [], "num_rows": 0, "num_cols": 0}

    def test_header_only_table(self) -> None:
        from docmeld.bronze.element_extractor import parse_table_data

        table_md = "| X | Y |\n|---|---|"
        result = parse_table_data(table_md)
        assert result["headers"] == ["X", "Y"]
        assert result["rows"] == []
        assert result["num_rows"] == 0
        assert result["num_cols"] == 2

    def test_single_column(self) -> None:
        from docmeld.bronze.element_extractor import parse_table_data

        table_md = "| Name |\n|------|\n| Alice |\n| Bob |"
        result = parse_table_data(table_md)
        assert result["headers"] == ["Name"]
        assert result["num_cols"] == 1
        assert result["num_rows"] == 2


class TestAssignElementIds:
    def test_sequential_ids(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids

        elements: List[Dict[str, Any]] = [
            {"type": "title", "level": 0, "content": "A", "page_no": 1},
            {"type": "text", "content": "B", "page_no": 1},
            {"type": "table", "content": "C", "summary": "", "page_no": 1},
        ]
        _assign_element_ids(elements)
        assert elements[0]["element_id"] == "e_0001"
        assert elements[1]["element_id"] == "e_0002"
        assert elements[2]["element_id"] == "e_0003"

    def test_empty_list(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids

        elements: List[Dict[str, Any]] = []
        _assign_element_ids(elements)
        assert elements == []


class TestAssignParentIds:
    def test_text_under_title(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids, _assign_parent_ids

        elements: List[Dict[str, Any]] = [
            {"type": "title", "level": 0, "content": "H1", "page_no": 1},
            {"type": "text", "content": "para", "page_no": 1},
        ]
        _assign_element_ids(elements)
        _assign_parent_ids(elements)
        assert elements[0]["parent_id"] == ""  # top-level title has no parent
        assert elements[1]["parent_id"] == "e_0001"

    def test_nested_titles(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids, _assign_parent_ids

        elements: List[Dict[str, Any]] = [
            {"type": "title", "level": 0, "content": "H1", "page_no": 1},
            {"type": "title", "level": 1, "content": "H2", "page_no": 1},
            {"type": "text", "content": "under H2", "page_no": 1},
            {"type": "title", "level": 2, "content": "H3", "page_no": 1},
            {"type": "text", "content": "under H3", "page_no": 1},
        ]
        _assign_element_ids(elements)
        _assign_parent_ids(elements)
        assert elements[0]["parent_id"] == ""       # H1 -> no parent
        assert elements[1]["parent_id"] == "e_0001"  # H2 -> H1
        assert elements[2]["parent_id"] == "e_0002"  # text -> H2 (deepest)
        assert elements[3]["parent_id"] == "e_0002"  # H3 -> H2
        assert elements[4]["parent_id"] == "e_0004"  # text -> H3

    def test_sibling_titles_reset_deeper(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids, _assign_parent_ids

        elements: List[Dict[str, Any]] = [
            {"type": "title", "level": 0, "content": "H1", "page_no": 1},
            {"type": "title", "level": 1, "content": "H2a", "page_no": 1},
            {"type": "title", "level": 0, "content": "H1b", "page_no": 2},
            {"type": "text", "content": "under H1b", "page_no": 2},
        ]
        _assign_element_ids(elements)
        _assign_parent_ids(elements)
        assert elements[2]["parent_id"] == ""       # H1b -> no parent (level 0)
        assert elements[3]["parent_id"] == "e_0003"  # text -> H1b (H2a was cleared)

    def test_no_titles(self) -> None:
        from docmeld.bronze.element_extractor import _assign_element_ids, _assign_parent_ids

        elements: List[Dict[str, Any]] = [
            {"type": "text", "content": "orphan", "page_no": 1},
        ]
        _assign_element_ids(elements)
        _assign_parent_ids(elements)
        assert elements[0]["parent_id"] == ""


class TestBackendDispatch:
    def test_default_backend_is_pymupdf(self) -> None:
        """Verify that extract_elements accepts a backend param defaulting to pymupdf."""
        import inspect

        from docmeld.bronze.element_extractor import extract_elements

        sig = inspect.signature(extract_elements)
        assert "backend" in sig.parameters
        assert sig.parameters["backend"].default == "pymupdf"

    def test_pymupdf_backend_dispatched(self) -> None:
        """Verify pymupdf backend is instantiated for default backend."""
        mock_backend_instance = MagicMock()
        mock_backend_instance.extract_elements.return_value = []
        mock_cls = MagicMock(return_value=mock_backend_instance)

        mock_module = MagicMock()
        mock_module.PyMuPDFBackend = mock_cls

        with patch.dict("sys.modules", {"docmeld.bronze.backends.pymupdf_backend": mock_module}):
            from docmeld.bronze import element_extractor
            # Clear cached import
            import importlib
            importlib.reload(element_extractor)
            element_extractor.extract_elements("/fake.pdf", "/fake_dir", backend="pymupdf")

        mock_cls.assert_called_once()
        mock_backend_instance.extract_elements.assert_called_once_with("/fake.pdf", "/fake_dir")

    def test_docling_backend_import_error(self) -> None:
        """Verify helpful error when docling is not installed."""
        from docmeld.bronze.backends.docling_backend import DoclingBackend

        backend = DoclingBackend()
        with patch.dict("sys.modules", {"docling": None, "docling.document_converter": None}):
            with pytest.raises(ImportError, match="Docling is not installed"):
                backend.extract_elements("/fake.pdf", "/fake_dir")
