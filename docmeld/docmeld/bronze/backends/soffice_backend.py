"""Soffice backend — LibreOffice bridge for legacy .doc files."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("docmeld")


class SofficeBackend:
    """Extract elements from legacy .doc/.ppt files via LibreOffice → PDF → PyMuPDF.

    Converts the source document to PDF using soffice --headless, then delegates
    to the existing PyMuPDF backend. Deletes the intermediate PDF after extraction.
    Element richness is limited to what PDF extraction provides (text, table,
    title, image).
    """

    SUPPORTED_SUFFIXES = {".doc", ".ppt"}

    def extract_elements(self, doc_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """Convert a legacy binary document to PDF and extract elements via PyMuPDF.

        Args:
            doc_path: Path to the .doc or .ppt file.
            output_dir: Directory for outputs (intermediate PDF goes here).

        Returns:
            List of element dicts in DocMeld format (limited to 4 types).
        """
        # Check LibreOffice availability
        soffice = shutil.which("soffice")
        if not soffice:
            raise RuntimeError(
                "LibreOffice (soffice) is not installed or not on PATH. "
                "Install LibreOffice to process .doc/.ppt files. "
                "See https://www.libreoffice.org/download/"
            )

        doc_path_obj = Path(doc_path)
        if doc_path_obj.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValueError(
                f"SofficeBackend only supports .doc/.ppt files, got: {doc_path_obj.suffix}"
            )

        # Convert to PDF in a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = subprocess.run(
                    [
                        soffice,
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", tmpdir,
                        str(doc_path_obj),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"LibreOffice conversion failed: {result.stderr.strip()}"
                    )
            except subprocess.TimeoutExpired:
                raise RuntimeError("LibreOffice conversion timed out after 120s")

            # Find the generated PDF
            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if not pdf_files:
                raise RuntimeError(
                    "LibreOffice conversion produced no PDF output"
                )

            pdf_path = str(pdf_files[0])

            # Delegate to PyMuPDF backend
            from docmeld.bronze.backends.pymupdf_backend import PyMuPDFBackend

            pymupdf = PyMuPDFBackend()
            try:
                elements = pymupdf.extract_elements(pdf_path, output_dir)
            except Exception:
                # Retry once if conversion produced corrupted PDF
                logger.warning(
                    f"First extraction attempt failed for {doc_path_obj.name}, retrying..."
                )
                # Re-convert
                pdf_files[0].unlink(missing_ok=True)
                subprocess.run(
                    [soffice, "--headless", "--convert-to", "pdf",
                     "--outdir", tmpdir, str(doc_path_obj)],
                    capture_output=True, text=True, timeout=120,
                )
                pdf_files2 = list(Path(tmpdir).glob("*.pdf"))
                if not pdf_files2:
                    raise RuntimeError(
                        "LibreOffice retry also produced no PDF output"
                    )
                elements = pymupdf.extract_elements(str(pdf_files2[0]), output_dir)

            logger.info(
                f"Soffice: {doc_path_obj.name} → "
                f"{len(elements)} elements via LibreOffice bridge"
            )
            return elements
