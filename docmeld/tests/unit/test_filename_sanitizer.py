"""Unit tests for filename sanitizer."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


class TestSanitizeFilename:
    def test_removes_dangerous_chars(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        result = sanitize_stem('report/test\\file:name*what?"yes<no>pipe|end')
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result

    def test_lowercases(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        assert sanitize_stem("MyReport") == "myreport"

    def test_replaces_spaces(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        assert sanitize_stem("my report file") == "my_report_file"

    def test_collapses_multiple_underscores(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        result = sanitize_stem("report---final!!!")
        assert "--" not in result
        assert "!!" not in result
        assert "__" not in result

    def test_truncates_at_200_chars(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        long_name = "a" * 300
        result = sanitize_stem(long_name)
        assert len(result) <= 200

    def test_unicode_normalization(self) -> None:
        from docmeld.bronze.filename_sanitizer import sanitize_stem

        # café with combining accent vs precomposed
        result = sanitize_stem("café")
        assert isinstance(result, str)
        assert len(result) > 0


class TestCalculateHash:
    def test_returns_6_hex_digits(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import calculate_hash

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake pdf content")
        result = calculate_hash(str(pdf))
        assert len(result) == 6
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import calculate_hash

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"same content")
        h1 = calculate_hash(str(pdf))
        h2 = calculate_hash(str(pdf))
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import calculate_hash

        pdf1 = tmp_path / "a.pdf"
        pdf1.write_bytes(b"content A")
        pdf2 = tmp_path / "b.pdf"
        pdf2.write_bytes(b"content B")
        assert calculate_hash(str(pdf1)) != calculate_hash(str(pdf2))

    def test_is_last_6_of_md5(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import calculate_hash

        content = b"test content for md5"
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(content)
        expected = hashlib.md5(content).hexdigest()[-6:]
        assert calculate_hash(str(pdf)) == expected


class TestGetOutputName:
    def test_format(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import get_output_name

        pdf = tmp_path / "My Report.pdf"
        pdf.write_bytes(b"content")
        name = get_output_name(str(pdf))
        # Should be sanitized_stem + _ + 6 hex chars
        assert name.startswith("my_report_")
        assert len(name.split("_")[-1]) == 6

    def test_special_chars_in_name(self, tmp_path: Path) -> None:
        from docmeld.bronze.filename_sanitizer import get_output_name

        pdf = tmp_path / "Report (2024) - Final!.pdf"
        pdf.write_bytes(b"content")
        name = get_output_name(str(pdf))
        assert "(" not in name
        assert ")" not in name
        assert "!" not in name
        assert " " not in name


class TestPptxExtensionHandling:
    """T022: sanitizer works for .pptx/.ppt files."""

    def test_pptx_output_name(self, tmp_path):
        from docmeld.bronze.filename_sanitizer import get_output_name

        f = tmp_path / "Q4 Earnings (Final)!.pptx"
        f.write_bytes(b"pptx-bytes")
        name = get_output_name(str(f))
        assert name.startswith("q4_earnings_final_")
        assert "(" not in name and ")" not in name and "!" not in name
        assert len(name.split("_")[-1]) == 6

    def test_ppt_output_name(self, tmp_path):
        from docmeld.bronze.filename_sanitizer import get_output_name

        f = tmp_path / "old deck.ppt"
        f.write_bytes(b"ppt-bytes")
        name = get_output_name(str(f))
        assert name.startswith("old_deck_")
        assert " " not in name
