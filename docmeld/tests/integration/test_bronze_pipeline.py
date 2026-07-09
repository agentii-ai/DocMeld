"""Integration tests for bronze pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestBronzePipelineSingleFile:
    def test_processes_simple_pdf(self, sample_simple_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        # Copy PDF to tmp_path so output folder is created there
        import shutil
        pdf_copy = tmp_path / "sample_simple.pdf"
        shutil.copy(sample_simple_pdf, pdf_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(pdf_copy))

        assert not result.skipped
        assert result.element_count > 0
        assert result.page_count == 3
        assert Path(result.output_path).exists()

        # Verify JSON structure
        with open(result.output_path) as f:
            elements = json.load(f)
        assert isinstance(elements, list)
        assert len(elements) > 0
        for elem in elements:
            assert "type" in elem
            assert "page_no" in elem
            assert elem["page_no"] >= 1

    def test_processes_complex_pdf(self, sample_complex_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        import shutil
        pdf_copy = tmp_path / "sample_complex.pdf"
        shutil.copy(sample_complex_pdf, pdf_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(pdf_copy))

        assert result.page_count == 5
        assert result.element_count > 0

        with open(result.output_path) as f:
            elements = json.load(f)

        types_found = {e["type"] for e in elements}
        assert "text" in types_found or "title" in types_found

    def test_creates_output_folder(self, sample_simple_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        import shutil
        pdf_copy = tmp_path / "test_doc.pdf"
        shutil.copy(sample_simple_pdf, pdf_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(pdf_copy))

        output_dir = Path(result.output_dir)
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_idempotency_skips_existing(self, sample_simple_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        import shutil
        pdf_copy = tmp_path / "test_doc.pdf"
        shutil.copy(sample_simple_pdf, pdf_copy)

        processor = BronzeProcessor()
        result1 = processor.process_file(str(pdf_copy))
        assert not result1.skipped

        result2 = processor.process_file(str(pdf_copy))
        assert result2.skipped

    def test_sanitized_filename_in_output(self, sample_simple_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        import shutil
        pdf_copy = tmp_path / "My Report (2024).pdf"
        shutil.copy(sample_simple_pdf, pdf_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(pdf_copy))

        output_name = Path(result.output_path).stem
        assert "(" not in output_name
        assert ")" not in output_name
        assert " " not in output_name

    def test_elements_ordered_by_page(self, sample_complex_pdf: Path, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor

        import shutil
        pdf_copy = tmp_path / "complex.pdf"
        shutil.copy(sample_complex_pdf, pdf_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(pdf_copy))

        with open(result.output_path) as f:
            elements = json.load(f)

        page_nos = [e["page_no"] for e in elements]
        assert page_nos == sorted(page_nos)


class TestBronzeDocxProcessing:
    """Tests for .docx bronze processing."""

    def test_processes_docx_via_docling(self, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor
        import shutil

        samples_dir = Path(__file__).resolve().parents[3] / "samples"
        docx_file = samples_dir / "sample_tables.docx"
        if not docx_file.exists():
            pytest.skip("sample_tables.docx not found")

        docx_copy = tmp_path / "sample_tables.docx"
        shutil.copy(docx_file, docx_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(docx_copy), backend="docling")

        assert result.element_count > 0, "Should extract elements from .docx"
        assert result.page_count >= 1
        assert Path(result.output_path).exists()

        with open(result.output_path) as f:
            elements = json.load(f)
        assert isinstance(elements, list)
        for elem in elements:
            assert "type" in elem
            assert "page_no" in elem
            assert elem["page_no"] >= 1

    def test_docx_output_has_element_id_and_parent_id(self, tmp_path: Path) -> None:
        from docmeld.bronze.processor import BronzeProcessor
        import shutil

        samples_dir = Path(__file__).resolve().parents[3] / "samples"
        docx_file = samples_dir / "sample_multipage.docx"
        if not docx_file.exists():
            pytest.skip("sample_multipage.docx not found")

        docx_copy = tmp_path / "sample_multipage.docx"
        shutil.copy(docx_file, docx_copy)

        processor = BronzeProcessor()
        result = processor.process_file(str(docx_copy), backend="docling")

        with open(result.output_path) as f:
            elements = json.load(f)
        for elem in elements:
            assert "element_id" in elem
            assert "parent_id" in elem

    def test_docx_filename_sanitization(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import get_output_name
        import shutil

        samples_dir = Path(__file__).resolve().parents[3] / "samples"
        docx_file = samples_dir / "sample_tables.docx"
        if not docx_file.exists():
            pytest.skip("sample_tables.docx not found")

        docx_copy = tmp_path / "sample_tables.docx"
        shutil.copy(docx_file, docx_copy)

        output_name = get_output_name(str(docx_copy))
        assert "_" in output_name
        assert len(output_name) > 0
        # Check it doesn't end with the hash (stem only)
        assert "." not in output_name
