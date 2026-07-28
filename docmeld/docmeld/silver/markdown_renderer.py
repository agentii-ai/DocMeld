"""Markdown renderer for silver stage - converts elements to page content."""

from __future__ import annotations

from typing import Any

from docmeld.silver.title_tracker import TitleTracker


def _count_data_rows(table_content: str) -> int:
    """Count data rows in a markdown table (excluding header and separator)."""
    lines = [line.strip() for line in table_content.strip().split("\n") if line.strip()]
    data_rows = 0
    for i, line in enumerate(lines):
        if i == 0:
            continue  # header
        if all(c in "-|: " for c in line):
            continue  # separator
        data_rows += 1
    return data_rows


# Extended counter type for all element counters
PageCounters = dict[str, int]


def new_counters() -> PageCounters:
    """Create a new counters dict for element numbering."""
    return {"table": 0, "chart": 0, "formula": 0, "smartart": 0}


def render_page(
    elements: list[dict[str, Any]],
    title_tracker: TitleTracker,
    counters: PageCounters | None = None,
) -> tuple[str, PageCounters]:
    """Render a list of elements into markdown page content.

    Supports 14 element types: title, text, table, image, chart,
    formula, header, footer, footnote, endnote, smartart, notes,
    group, comment.

    Args:
        elements: List of element dicts for this page.
        title_tracker: TitleTracker instance (mutated with new titles).
        counters: Dict with table, chart, formula counters (mutated).

    Returns:
        Tuple of (page_content_string, updated_counters).
    """
    if counters is None:
        counters = new_counters()

    parts: list[str] = []

    for elem in elements:
        elem_type = elem["type"]

        if elem_type == "title":
            level = elem["level"]
            content = elem["content"]
            title_tracker.update(level, content)
            heading = "#" * (level + 1)
            parts.append(f"{heading} {content}")

        elif elem_type == "text":
            parts.append(elem["content"])

        elif elem_type == "table":
            table_content = elem["content"]
            data_rows = _count_data_rows(table_content)

            if data_rows > 1:
                counters["table"] += 1
                parts.append(f"[[Table{counters['table']}]]")
                parts.append(table_content)
                parts.append(f"[/Table{counters['table']}]")
            else:
                parts.append("[[Table]]")
                parts.append(table_content)
                parts.append("[/Table]")

        elif elem_type == "image":
            image_name = elem.get("image_name", "image")
            description = (elem.get("content") or "").strip().splitlines()
            desc = description[0] if description else image_name
            parts.append(f"[[Image: {desc}]]")

        elif elem_type == "chart":
            chart_content = elem["content"]
            chart_type = elem.get("chart_type", "unknown")
            counters["chart"] += 1
            n = counters["chart"]
            parts.append(f"[[Chart{n} type={chart_type}]]")
            if chart_content.strip():
                parts.append(chart_content)
            parts.append(f"[/Chart{n}]")

        elif elem_type == "formula":
            formula_content = elem["content"]
            formula_type = elem.get("formula_type", "LaTeX")
            counters["formula"] += 1
            n = counters["formula"]
            parts.append(f"[[Formula{n} type={formula_type}]]")
            parts.append(formula_content)
            parts.append(f"[/Formula{n}]")

        elif elem_type == "header":
            content = elem["content"]
            scope = elem.get("page_scope", "all")
            parts.append(f"[Header scope={scope}] {content} [/Header]")

        elif elem_type == "footer":
            content = elem["content"]
            scope = elem.get("page_scope", "all")
            parts.append(f"[Footer scope={scope}] {content} [/Footer]")

        elif elem_type == "footnote" or elem_type == "endnote":
            ref = elem.get("reference_id", "N")
            parts.append(f"[^{ref}]: {elem['content']}")

        elif elem_type == "smartart":
            counters["smartart"] += 1
            n = counters["smartart"]
            sa_type = elem.get("smartart_type", "unknown")
            parts.append(f"[[SmartArt{n} type={sa_type}]]")
            if elem.get("content", "").strip():
                parts.append(elem["content"])
            parts.append(f"[/SmartArt{n}]")

        elif elem_type == "notes":
            parts.append("[Notes]")
            parts.append(elem["content"])
            parts.append("[/Notes]")

        elif elem_type == "comment":
            author = elem.get("author", "")
            parts.append(f"[Comment: {author}]")
            parts.append(elem["content"])
            parts.append("[/Comment]")

        elif elem_type == "group":
            # Group is a structural container; children render on their own.
            content = elem.get("content", "")
            if content:
                parts.append(f"[Group] {content} [/Group]")

    page_content = "\n\n".join(parts)
    return page_content, counters
