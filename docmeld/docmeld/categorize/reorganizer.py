"""Reorganize files into category subdirectories."""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from docmeld.bronze.filename_sanitizer import calculate_hash

logger = logging.getLogger("docmeld")


def _build_pdf_hash_map(folder: Path) -> dict[str, Path]:
    """Build a mapping from MD5 hash suffix to original PDF path."""
    result: dict[str, Path] = {}
    for pdf in sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF")):
        hash6 = calculate_hash(str(pdf))
        result[hash6] = pdf
    return result


def reorganize_by_category(folder_path: str) -> None:
    """Move PDFs and their output folders into category-named subdirectories.

    Reads categories.json from the folder, creates subdirectories for each
    category, and moves both the output directory and the original PDF into them.
    Matches PDFs to output dirs via the MD5 hash suffix in the dir name.

    Args:
        folder_path: Path to the folder containing categories.json.

    Raises:
        FileNotFoundError: If categories.json does not exist.
    """
    folder = Path(folder_path)
    index_path = folder / "categories.json"

    if not index_path.exists():
        msg = f"categories.json not found in {folder_path}"
        raise FileNotFoundError(msg)

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    # Build hash → PDF mapping for matching originals
    pdf_hash_map = _build_pdf_hash_map(folder)

    moves: list[dict[str, str]] = []

    for paper_entry in index.get("papers", []):
        filename = paper_entry["filename"]
        category = paper_entry["category"]
        safe_category = _sanitize_category_name(category)

        # The filename is like paper1_abc123.jsonl (silver) or paper1_abc123_gold.jsonl (legacy)
        # The output dir is paper1_abc123
        stem = filename.replace("_gold.jsonl", "").replace(".jsonl", "")
        output_dir = folder / stem

        if not output_dir.exists():
            # Maybe already reorganized — check inside category dirs
            candidate = folder / safe_category / stem
            if candidate.exists():
                continue  # Already moved
            logger.warning(f"Output dir not found: {output_dir}")
            continue

        # Create category directory
        cat_dir = folder / safe_category
        cat_dir.mkdir(exist_ok=True)

        # Move output directory (bronze folder)
        dest = cat_dir / stem
        if not dest.exists():
            # Find and move the original PDF by matching the hash suffix
            hash6 = stem.rsplit("_", 1)[-1] if "_" in stem else ""
            pdf_path = pdf_hash_map.get(hash6)
            if pdf_path and pdf_path.exists():
                pdf_dest = cat_dir / pdf_path.name
                if not pdf_dest.exists():
                    shutil.move(str(pdf_path), str(pdf_dest))
                    moves.append({"source": str(pdf_path), "dest": str(pdf_dest), "type": "pdf"})
                    logger.info(f"Moved {pdf_path.name} → {safe_category}/")

            shutil.move(str(output_dir), str(dest))
            moves.append({"source": str(output_dir), "dest": str(dest), "type": "output_dir"})
            logger.info(f"Moved {output_dir.name} → {safe_category}/")

    # Write manifest
    manifest = {
        "reorganized_at": datetime.now(timezone.utc).isoformat(),
        "moves": moves,
    }
    manifest_path = folder / "_reorganized.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Reorganized {len(moves)} items into category directories")


def _sanitize_category_name(name: str) -> str:
    """Sanitize a category name for use as a directory name.

    Replaces unsafe characters with underscores, strips whitespace.
    """
    name = name.strip()
    # Replace characters that are unsafe in filenames
    name = re.sub(r'[/\\:*?"<>|&;]', "_", name)
    # Collapse multiple underscores/spaces
    name = re.sub(r"[_ ]+", " ", name).strip()
    # Truncate to reasonable length
    if len(name) > 100:
        name = name[:100].rstrip()
    return name
