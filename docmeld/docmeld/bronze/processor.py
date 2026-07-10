"""Bronze stage processor — document to structured JSON elements."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from docmeld.bronze.element_extractor import extract_elements
from docmeld.bronze.filename_sanitizer import get_output_name
from docmeld.silver.page_models import BronzeResult, ProcessingFailure, ProcessingResult

logger = logging.getLogger("docmeld")

# Supported file extensions
WORD_EXTENSIONS = {".doc", ".docx"}
PDF_EXTENSIONS = {".pdf"}
PPT_EXTENSIONS = {".ppt", ".pptx"}
SUPPORTED_EXTENSIONS = WORD_EXTENSIONS | PDF_EXTENSIONS | PPT_EXTENSIONS
UNSUPPORTED_WORD_EXTENSIONS = {".docm", ".dotx", ".dot", ".rtf"}
UNSUPPORTED_PPT_EXTENSIONS = {".pptm", ".potx", ".pot", ".ppsx", ".odp"}


def _should_process(file_path: Path) -> bool:
    """Check if a file should be processed."""
    ext = file_path.suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return True
    if ext in UNSUPPORTED_WORD_EXTENSIONS:
        logger.warning(
            f"Skipping unsupported Word format: {file_path.name} "
            f"(.docm/.dotx/.dot/.rtf not supported in this version)"
        )
        return False
    if ext in UNSUPPORTED_PPT_EXTENSIONS:
        logger.warning(
            f"Skipping unsupported presentation format: {file_path.name} "
            f"(.pptm/.potx/.pot/.ppsx/.odp not supported in this version)"
        )
        return False
    if ext:
        logger.warning(f"Skipping non-document file: {file_path.name}")
    return False


def _detect_backend(file_path: Path, backend: str) -> str:
    """Detect appropriate backend for a file."""
    if backend == "auto":
        ext = file_path.suffix.lower()
        if ext in WORD_EXTENSIONS:
            if ext == ".doc":
                return "soffice"
            return "docling"
        if ext in PPT_EXTENSIONS:
            if ext == ".ppt":
                return "soffice"
            return "pptx"
        return "pymupdf"
    return backend


class BronzeProcessor:
    """Orchestrates bronze-level document processing."""

    def process_file(self, doc_path: str, backend: str = "pymupdf") -> BronzeResult:
        """Process a single document (PDF or DOCX) into structured JSON elements.

        Args:
            doc_path: Path to the document file (.pdf, .docx, .doc).
            backend: Parser backend name ("pymupdf", "docling", "soffice", "auto").

        Returns:
            BronzeResult with output paths and statistics.
        """
        path = Path(doc_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {doc_path}")

        # Detect backend if auto
        resolved_backend = _detect_backend(path, backend)

        output_name = get_output_name(doc_path)
        output_dir = path.parent / output_name
        output_json = output_dir / f"{output_name}.json"

        # Idempotency check
        if output_json.exists():
            with open(output_json) as f:
                elements = json.load(f)
            page_nos = {e.get("page_no", 0) for e in elements}
            return BronzeResult(
                output_path=str(output_json),
                output_dir=str(output_dir),
                element_count=len(elements),
                page_count=len(page_nos),
                skipped=True,
            )

        # Create output directory
        output_dir.mkdir(exist_ok=True)

        try:
            # Get page count (fitz for PDF, docling for DOCX/DOC)
            ext = path.suffix.lower()
            if ext in PDF_EXTENSIONS:
                import fitz
                doc = fitz.open(doc_path)
                page_count = len(doc)
                doc.close()
            else:
                # For .docx/.doc/.pptx/.ppt, get page count from extracted elements
                page_count = 0

            # Extract elements
            elements = extract_elements(doc_path, str(output_dir), backend=resolved_backend)
        except Exception:
            # Do not leave an orphan empty output directory behind on failure
            try:
                if output_dir.exists() and not any(output_dir.iterdir()):
                    output_dir.rmdir()
            except OSError:
                pass
            raise

        # Get page count from elements if not set
        if page_count == 0:
            page_nos_from_elements = {e.get("page_no", 0) for e in elements}
            page_count = len(page_nos_from_elements)

        # Save JSON
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(elements, f, indent=4, ensure_ascii=False)

        logger.info(f"Bronze: {path.name} → {len(elements)} elements, {page_count} pages")

        return BronzeResult(
            output_path=str(output_json),
            output_dir=str(output_dir),
            element_count=len(elements),
            page_count=page_count,
            skipped=False,
        )

    def process_folder(self, folder_path: str, backend: str = "auto") -> ProcessingResult:
        """Process all supported documents in a folder (fail-fast disabled).

        Supports .pdf, .docx, .doc files. Skips unsupported Word formats
        (.docm, .dotx, .dot, .rtf) with a warning.

        Args:
            folder_path: Path to folder containing documents.
            backend: Parser backend ("pymupdf", "docling", "soffice", "auto").

        Returns:
            ProcessingResult with summary statistics.
        """
        start_time = time.time()
        folder = Path(folder_path)

        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        # Collect all files and filter
        all_files = sorted(folder.iterdir())
        doc_files = [f for f in all_files if f.is_file() and _should_process(f)]
        total = len(doc_files)
        successful = 0
        failed = 0
        failures: list[ProcessingFailure] = []

        for i, doc_file in enumerate(doc_files, 1):
            logger.info(f"Processing {i}/{total}: {doc_file.name}")
            try:
                self.process_file(str(doc_file), backend=backend)
                successful += 1
            except Exception as e:
                failed += 1
                failures.append(
                    ProcessingFailure(filename=doc_file.name, error=str(e))
                )
                logger.error(f"Failed to process {doc_file.name}: {e}")

        elapsed = time.time() - start_time

        return ProcessingResult(
            total_files=total,
            successful=successful,
            failed=failed,
            failures=failures,
            processing_time_seconds=round(elapsed, 2),
            output_directory=str(folder),
            log_file="",
        )
