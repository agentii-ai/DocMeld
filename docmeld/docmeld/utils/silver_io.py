"""Shared helpers for loading silver-stage JSONL content.

Used by prd, workflow, skills generators and the categorize aggregator.
"""

from __future__ import annotations

import json


def load_silver_content(jsonl_path: str) -> list[str]:
    """Load page content strings from a silver JSONL file.

    Args:
        jsonl_path: Path to the silver JSONL file.

    Returns:
        List of page_content strings for each non-empty page.

    Raises:
        FileNotFoundError: If the JSONL file does not exist.
    """
    from pathlib import Path

    path = Path(jsonl_path)
    if not path.exists():
        msg = f"Silver JSONL not found: {jsonl_path}"
        raise FileNotFoundError(msg)

    pages: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            content = data.get("page_content", "")
            if content.strip():
                pages.append(content)

    return pages
