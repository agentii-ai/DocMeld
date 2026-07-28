"""Page aggregator - groups bronze elements by page number."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def group_by_page(elements: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group elements by their page_no field.

    Args:
        elements: Flat list of element dicts.

    Returns:
        Dict mapping page_no to list of elements for that page,
        preserving element order within each page.
    """
    pages: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for elem in elements:
        page_no = elem.get("page_no", 1)
        pages[page_no].append(elem)
    return dict(pages)
