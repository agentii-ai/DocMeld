"""DocMeld CLI interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(args: list[str] | None = None) -> int:
    """CLI entry point for DocMeld."""
    parser = argparse.ArgumentParser(
        prog="docmeld",
        description="Lightweight PDF to agent-ready knowledge pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline stage to run")

    # process (all stages)
    p_all = subparsers.add_parser("process", help="Run full pipeline (bronze → silver → gold)")
    p_all.add_argument("path", help="Path to a document/presentation file or folder (.pdf/.docx/.doc/.pptx/.ppt)")
    p_all.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="auto",
        help="Parsing backend (default: auto — detects format)",
    )

    # bronze
    p_bronze = subparsers.add_parser("bronze", help="Run bronze stage only (PDF → JSON)")
    p_bronze.add_argument("path", help="Path to a document/presentation file or folder (.pdf/.docx/.doc/.pptx/.ppt)")
    p_bronze.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="auto",
        help="Parsing backend (default: auto — detects format)",
    )

    # silver
    p_silver = subparsers.add_parser("silver", help="Run silver stage only (JSON → JSONL)")
    p_silver.add_argument("path", help="Path to bronze JSON file")

    # gold
    p_gold = subparsers.add_parser("gold", help="Run gold stage only (JSONL → enriched JSONL)")
    p_gold.add_argument("path", help="Path to silver JSONL file")

    # categorize
    p_cat = subparsers.add_parser("categorize", help="Batch process + categorize papers by topic")
    p_cat.add_argument("path", help="Path to folder of PDFs")
    p_cat.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="pymupdf",
        help="PDF parsing backend (default: pymupdf)",
    )
    p_cat.add_argument(
        "--reorganize",
        action="store_true",
        help="Move files into category subdirectories",
    )

    # prd
    p_prd = subparsers.add_parser("prd", help="Generate PRD from a research paper PDF")
    p_prd.add_argument("path", help="Path to a single PDF file")
    p_prd.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="pymupdf",
        help="PDF parsing backend (default: pymupdf)",
    )

    # workflow
    p_wf = subparsers.add_parser("workflow", help="Generate workflow from a research paper PDF")
    p_wf.add_argument("path", help="Path to a single PDF file")
    p_wf.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="pymupdf",
        help="PDF parsing backend (default: pymupdf)",
    )

    # skills
    p_sk = subparsers.add_parser("skills", help="Extract Claude Code skills from a book PDF")
    p_sk.add_argument("path", help="Path to a single PDF file")
    p_sk.add_argument(
        "--backend",
        choices=["pymupdf", "docling", "pptx", "soffice", "auto"],
        default="pymupdf",
        help="PDF parsing backend (default: pymupdf)",
    )

    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    path = parsed.path
    if not Path(path).exists():
        print(f"Error: path not found: {path}", file=sys.stderr)
        return 1

    from docmeld.parser import DocMeldParser
    from docmeld.utils.logging import setup_logging

    logger = setup_logging()

    try:
        backend = getattr(parsed, "backend", "auto")
        if parsed.command == "process":
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_all()
            print(f"Done: {result.successful}/{result.total_files} files processed")
            if result.failed > 0:
                print(f"Failed: {result.failed} files")
                for f in result.failures:
                    print(f"  - {f.filename}: {f.error}")
            print(f"Time: {result.processing_time_seconds}s")

        elif parsed.command == "bronze":
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_bronze()
            if hasattr(result, "element_count"):
                print(f"Bronze: {result.element_count} elements, {result.page_count} pages")
                print(f"Output: {result.output_path}")
            else:
                print(f"Bronze batch: {result.successful}/{result.total_files} files")

        elif parsed.command == "silver":
            doc = DocMeldParser(path)
            result = doc.process_silver(path)
            print(f"Silver: {result.page_count} pages")
            print(f"Output: {result.output_path}")

        elif parsed.command == "gold":
            doc = DocMeldParser(path)
            result = doc.process_gold(path)
            print(f"Gold: {result.pages_enriched} enriched, {result.pages_failed} failed")
            print(f"Output: {result.output_path}")

        elif parsed.command == "categorize":
            if not Path(path).is_dir():
                print(f"Error: categorize requires a folder path, got: {path}", file=sys.stderr)
                return 1
            reorganize = getattr(parsed, "reorganize", False)
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_categorize(reorganize=reorganize)
            if result.total_papers == 0:
                print("No PDFs found to categorize")
            else:
                print(f"Categorized {result.total_papers} papers into {result.total_categories} categories")
                print(f"Index: {result.index_path}")
                if result.reorganized:
                    print("Files reorganized into category subdirectories")

        elif parsed.command == "prd":
            if Path(path).is_dir():
                print(f"Error: prd requires a single PDF file, got folder: {path}", file=sys.stderr)
                return 1
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_prd()
            if result.skipped:
                print(f"PRD already exists: {result.output_path}")
            else:
                print(f"PRD generated: {result.sections} sections")
                print(f"Output: {result.output_path}")

        elif parsed.command == "workflow":
            if Path(path).is_dir():
                print(f"Error: workflow requires a single PDF file, got folder: {path}", file=sys.stderr)
                return 1
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_workflow()
            if result.skipped:
                print(f"Workflow already exists: {result.output_path}")
            else:
                print(f"Workflow generated: {result.sections} sections")
                print(f"Output: {result.output_path}")

        elif parsed.command == "skills":
            if Path(path).is_dir():
                print(f"Error: skills requires a single PDF file, got folder: {path}", file=sys.stderr)
                return 1
            doc = DocMeldParser(path, backend=backend)
            result = doc.process_skills()
            if result.skipped:
                print(f"Skills already exist: {result.output_dir} ({result.skill_count} skills)")
            else:
                print(f"Extracted {result.skill_count} skills")
                print(f"Output: {result.output_dir}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
