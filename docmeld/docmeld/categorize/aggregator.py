"""Aggregate silver-stage content across all papers in a folder."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from docmeld.categorize.models import PaperMetadata

logger = logging.getLogger("docmeld")

# Max chars of page_content to collect per paper (~8k tokens)
MAX_CONTENT_CHARS = 30000


def generate_article_md(silver_path: Path) -> Path | None:
    """Read silver JSONL and write full page_content as a markdown article.

    Args:
        silver_path: Path to a silver JSONL file.

    Returns:
        Path to the generated .md file, or None if no content.
    """
    pages: List[Dict[str, Any]] = []
    with open(silver_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))

    if not pages:
        return None

    content_parts = [p.get("page_content", "") for p in pages if p.get("page_content")]
    if not content_parts:
        return None

    md_content = "\n\n---\n\n".join(content_parts)
    md_path = silver_path.with_name(silver_path.stem + "_article.md")
    if not md_path.exists():
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.debug(f"Generated article: {md_path.name}")
    return md_path


def aggregate_paper_metadata(folder_path: str) -> List[PaperMetadata]:
    """Scan a folder for silver JSONL files and collect per-paper content.

    Looks for *.jsonl files (excluding *_gold.jsonl) in subdirectories.
    Concatenates page_content from each page up to MAX_CONTENT_CHARS.
    Also generates a full markdown article for each paper.

    Args:
        folder_path: Path to the folder containing paper output directories.

    Returns:
        List of PaperMetadata, one per paper, sorted by filename.
    """
    folder = Path(folder_path)
    results: List[PaperMetadata] = []

    silver_files = sorted(
        p for p in folder.rglob("*.jsonl")
        if not p.name.endswith("_gold.jsonl")
    )

    for silver_path in silver_files:
        try:
            generate_article_md(silver_path)
            metadata = _parse_silver_file(silver_path)
            if metadata:
                results.append(metadata)
        except Exception as e:
            logger.warning(f"Failed to parse {silver_path}: {e}")

    results.sort(key=lambda p: p.filename)
    return results


def _parse_silver_file(silver_path: Path) -> PaperMetadata | None:
    """Parse a silver JSONL file into PaperMetadata with truncated content."""
    pages: List[Dict[str, Any]] = []
    with open(silver_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))

    if not pages:
        return None

    # Concatenate page_content up to the char limit
    content_parts: List[str] = []
    total_chars = 0
    for page in pages:
        page_content = page.get("page_content", "")
        if not page_content:
            continue
        remaining = MAX_CONTENT_CHARS - total_chars
        if remaining <= 0:
            break
        if len(page_content) > remaining:
            content_parts.append(page_content[:remaining])
            total_chars += remaining
            break
        content_parts.append(page_content)
        total_chars += len(page_content)

    combined_content = "\n\n---\n\n".join(content_parts)

    return PaperMetadata(
        filename=silver_path.name,
        file_path=str(silver_path),
        output_dir=str(silver_path.parent),
        content=combined_content,
        page_count=len(pages),
    )
