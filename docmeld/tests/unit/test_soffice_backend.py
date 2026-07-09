"""Unit tests for SofficeBackend (LibreOffice bridge for .doc files)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestSofficeBackend:
    def test_libreoffice_not_found_raises_runtime_error(self) -> None:
        """When soffice is not on PATH, extract_elements raises RuntimeError."""
        from docmeld.bronze.backends.soffice_backend import SofficeBackend

        backend = SofficeBackend()
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="LibreOffice"):
                backend.extract_elements("/fake.doc", "/tmp/out")

    def test_non_doc_extension_raises_value_error(self) -> None:
        """Non-.doc files raise ValueError."""
        from docmeld.bronze.backends.soffice_backend import SofficeBackend

        backend = SofficeBackend()
        with patch("shutil.which", return_value="/usr/bin/soffice"):
            with pytest.raises(ValueError, match="only supports .doc"):
                backend.extract_elements("/fake.docx", "/tmp/out")

    def test_conversion_integration(self) -> None:
        """Integration test: requires LibreOffice installed."""
        import shutil
        if not shutil.which("soffice"):
            pytest.skip("LibreOffice (soffice) not installed")

        from pathlib import Path
        from docmeld.bronze.backends.soffice_backend import SofficeBackend

        samples_dir = Path(__file__).resolve().parents[3] / "samples"
        doc_file = samples_dir / "sample_tables.doc"
        if not doc_file.exists():
            pytest.skip("sample_tables.doc fixture not found")

        backend = SofficeBackend()
        elements = backend.extract_elements(str(doc_file), str(samples_dir))
        assert len(elements) > 0
        types_found = {e["type"] for e in elements}
        assert "text" in types_found or "title" in types_found