"""PyMuPDF + pymupdf4llm backend for PDF element extraction."""

from __future__ import annotations

from typing import Any

import fitz
import pymupdf4llm

from docmeld.bronze.element_extractor import _discover_images, parse_markdown_to_elements


class PyMuPDFBackend:
    """Extract elements using PyMuPDF (fitz) and pymupdf4llm."""

    def extract_elements(self, pdf_path: str, output_dir: str) -> list[dict[str, Any]]:
        """Extract all elements from a PDF file.

        Opens the PDF with PyMuPDF, extracts text via pymupdf4llm per page,
        parses markdown into structured elements, and discovers images.
        """
        doc = fitz.open(pdf_path)
        all_elements: list[dict[str, Any]] = []

        for page_num in range(len(doc)):
            page_no = page_num + 1

            try:
                md_content = pymupdf4llm.to_markdown(doc, pages=[page_num])
            except Exception:
                md_content = ""

            if md_content:
                page_elements = parse_markdown_to_elements(md_content, page_no)
                all_elements.extend(page_elements)

            image_elements = _discover_images(output_dir, page_num)
            all_elements.extend(image_elements)

        doc.close()
        return all_elements
