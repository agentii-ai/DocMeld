"""Write categories.json index file."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docmeld.categorize.models import PaperMetadata

logger = logging.getLogger("docmeld")


def write_category_index(
    folder_path: str,
    papers: list[PaperMetadata],
    categories: list[dict[str, Any]],
) -> str:
    """Write a categories.json file to the folder root.

    Args:
        folder_path: Path to the folder containing the papers.
        papers: List of PaperMetadata from the aggregator.
        categories: List of category dicts from the categorizer.

    Returns:
        Path to the written categories.json file.
    """
    # Build paper-to-category mapping
    paper_category_map: dict[str, str] = {}
    for cat in categories:
        for filename in cat.get("papers", []):
            paper_category_map[filename] = cat["name"]

    # Build paper entries sorted by filename for determinism
    paper_entries = []
    for p in sorted(papers, key=lambda x: x.filename):
        paper_entries.append(
            {
                "filename": p.filename,
                "category": paper_category_map.get(p.filename, "Uncategorized"),
                "description": p.description,
                "keywords": p.keywords,
            }
        )

    # Sort categories by name for determinism
    sorted_categories = sorted(categories, key=lambda c: c.get("name", ""))

    index = {
        "created": datetime.now(timezone.utc).isoformat(),
        "source_folder": str(Path(folder_path).resolve()),
        "total_papers": len(paper_entries),
        "total_categories": len(sorted_categories),
        "categories": sorted_categories,
        "papers": paper_entries,
    }

    output_path = Path(folder_path) / "categories.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(
        f"Wrote {output_path}: {len(paper_entries)} papers, {len(sorted_categories)} categories"
    )
    return str(output_path)
