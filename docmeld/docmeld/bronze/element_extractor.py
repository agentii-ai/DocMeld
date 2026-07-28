"""Extract structured elements from PDF pages.

Dispatches to a backend (pymupdf or docling) and applies shared
post-processing: element_id assignment, parent_id hierarchy, table
summaries, and structured table_data.
"""

from __future__ import annotations

import base64
import glob
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docmeld.bronze.backends import ParserBackend


def extract_elements(
    pdf_path: str, output_dir: str, backend: str = "pymupdf"
) -> list[dict[str, Any]]:
    """Extract all elements from a PDF file using the specified backend.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory for auxiliary outputs (images, etc.).
        backend: Parser backend name ("pymupdf" or "docling").

    Returns:
        Ordered list of element dicts with type, page_no, element_id, parent_id.
    """
    b: ParserBackend
    if backend == "docling":
        from docmeld.bronze.backends.docling_backend import DoclingBackend

        b = DoclingBackend()
    elif backend == "soffice":
        from docmeld.bronze.backends.soffice_backend import SofficeBackend

        b = SofficeBackend()
    elif backend == "pptx":
        from docmeld.bronze.backends.pptx_backend import PptxBackend

        b = PptxBackend()
    else:
        from docmeld.bronze.backends.pymupdf_backend import PyMuPDFBackend

        b = PyMuPDFBackend()

    elements = b.extract_elements(pdf_path, output_dir)

    # Shared post-processing across all backends
    for elem in elements:
        if elem["type"] == "table":
            elem["summary"] = generate_table_summary(elem["content"])
            elem["table_data"] = parse_table_data(elem["content"])

    _assign_element_ids(elements)
    _assign_parent_ids(elements)
    _resolve_group_parents(elements)

    return elements


def _resolve_group_parents(elements: list[dict[str, Any]]) -> None:
    """Link grouped child shapes to their parent group element.

    The pptx backend tags group elements with a temporary ``_gid`` and each
    grouped child with ``_pgid``. After element_ids are assigned, rewrite each
    child's ``parent_id`` to the group's ``element_id`` (overriding the
    title-based parent), then strip the temporary keys so they never reach
    the JSON output.
    """
    gid_to_element_id: dict[int, str] = {}
    for elem in elements:
        gid = elem.get("_gid")
        if gid is not None:
            gid_to_element_id[gid] = elem.get("element_id", "")

    for elem in elements:
        pgid = elem.get("_pgid")
        if pgid is not None and pgid in gid_to_element_id:
            elem["parent_id"] = gid_to_element_id[pgid]
        elem.pop("_gid", None)
        elem.pop("_pgid", None)


def _assign_element_ids(elements: list[dict[str, Any]]) -> None:
    """Assign sequential element_id values (e_0001, e_0002, ...)."""
    for i, elem in enumerate(elements):
        elem["element_id"] = f"e_{i + 1:04d}"


def _assign_parent_ids(elements: list[dict[str, Any]]) -> None:
    """Assign parent_id based on nearest ancestor title at a higher level.

    Tracks a title stack keyed by level. Non-title elements get the
    element_id of the most recent title. Titles get the element_id of
    the most recent title at a strictly higher (lower-numbered) level.
    """
    # Stack: level -> element_id of the most recent title at that level
    title_stack: dict[int, str] = {}

    for elem in elements:
        if elem["type"] == "title":
            level = elem.get("level", 0)
            # Find nearest ancestor: closest title with level < current
            parent_id = ""
            for ancestor_level in range(level - 1, -1, -1):
                if ancestor_level in title_stack:
                    parent_id = title_stack[ancestor_level]
                    break
            elem["parent_id"] = parent_id

            # Register this title and clear deeper levels
            title_stack[level] = elem["element_id"]
            for deeper in list(title_stack.keys()):
                if deeper > level:
                    del title_stack[deeper]
        else:
            # Non-title: parent is the most recent title (highest level number present)
            parent_id = ""
            if title_stack:
                max_level = max(title_stack.keys())
                parent_id = title_stack[max_level]
            elem["parent_id"] = parent_id


def parse_markdown_to_elements(md_content: str, page_no: int) -> list[dict[str, Any]]:
    """Parse markdown content into structured elements.

    Identifies titles (# lines), tables (| lines), and text blocks.
    """
    elements: list[dict[str, Any]] = []
    lines = md_content.split("\n")
    text_buffer: list[str] = []
    table_buffer: list[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Empty line: flush text buffer, preserve as newline
            text_buffer.append("\n")

            # Flush table buffer on empty line
            if table_buffer:
                content = "\n".join(table_buffer).strip()
                if content:
                    elements.append(
                        {"type": "table", "summary": "", "content": content, "page_no": page_no}
                    )
                table_buffer = []
            continue

        if stripped.startswith("#"):
            # Flush text buffer
            if text_buffer:
                content = "\n".join(text_buffer).strip()
                if content:
                    elements.append({"type": "text", "content": content, "page_no": page_no})
                text_buffer = []

            # Flush table buffer
            if table_buffer:
                content = "\n".join(table_buffer).strip()
                if content:
                    elements.append(
                        {"type": "table", "summary": "", "content": content, "page_no": page_no}
                    )
                table_buffer = []

            # Count heading level
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break

            title = stripped[level:].strip()
            if title:
                elements.append(
                    {"type": "title", "level": level - 1, "content": title, "page_no": page_no}
                )

        elif stripped.startswith("|"):
            # Flush text buffer before table
            if text_buffer:
                content = "\n".join(text_buffer).strip()
                if content:
                    elements.append({"type": "text", "content": content, "page_no": page_no})
                text_buffer = []

            table_buffer.append(stripped)

        else:
            # Flush table buffer before text
            if table_buffer:
                content = "\n".join(table_buffer).strip()
                if content:
                    elements.append(
                        {"type": "table", "summary": "", "content": content, "page_no": page_no}
                    )
                table_buffer = []

            text_buffer.append(stripped)

    # Flush remaining buffers
    if text_buffer:
        content = "\n".join(text_buffer).strip()
        if content:
            elements.append({"type": "text", "content": content, "page_no": page_no})

    if table_buffer:
        content = "\n".join(table_buffer).strip()
        if content:
            elements.append(
                {"type": "table", "summary": "", "content": content, "page_no": page_no}
            )

    return elements


def generate_table_summary(table_md: str) -> str:
    """Generate a summary from a markdown table's first column values.

    Returns: 'Items: val1, val2, ...' or empty string.
    """
    if not table_md.strip():
        return ""

    lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]
    items: list[str] = []

    for i, line in enumerate(lines):
        if i == 0:
            continue  # Skip header row
        # Skip separator lines
        if all(c in "-|: " for c in line):
            continue
        # Extract first column value
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if parts:
            items.append(parts[0])

    if not items:
        return ""

    if len(items) <= 5:
        return f"Items: {', '.join(items)}"
    return f"Items: {', '.join(items[:5])} (+{len(items) - 5} more)"


def parse_table_data(table_md: str) -> dict[str, Any]:
    """Parse a markdown table into structured data.

    Returns:
        {"headers": [...], "rows": [[...], ...], "num_rows": N, "num_cols": M}
    """
    if not table_md.strip():
        return {"headers": [], "rows": [], "num_rows": 0, "num_cols": 0}

    lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]

    headers: list[str] = []
    rows: list[list[str]] = []

    for _i, line in enumerate(lines):
        # Skip separator lines (e.g. |---|---|)
        if all(c in "-|: " for c in line):
            continue

        cells = [c.strip() for c in line.split("|") if c.strip()]

        if not headers:
            headers = cells
        else:
            rows.append(cells)

    return {
        "headers": headers,
        "rows": rows,
        "num_rows": len(rows),
        "num_cols": len(headers),
    }


def _discover_images(output_dir: str, page_num: int) -> list[dict[str, Any]]:
    """Discover pre-extracted image files for a page."""
    elements: list[dict[str, Any]] = []
    page_prefix = f"page{page_num + 1:03d}"
    search_pattern = str(Path(output_dir) / f"{page_prefix}_*.png")
    image_files = sorted(glob.glob(search_pattern))

    for image_path_str in image_files:
        image_path = Path(image_path_str)
        image_id = image_path.stem

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            base64_content = base64.b64encode(image_bytes).decode("utf-8")

            # Check for markdown description file
            md_path = Path(output_dir) / f"{image_id}.md"
            md_content = ""
            if md_path.exists():
                md_content = md_path.read_text(encoding="utf-8")

            elements.append(
                {
                    "type": "image",
                    "image_name": image_path.name,
                    "content": md_content,
                    "image": base64_content,
                    "page_no": page_num + 1,
                    "image_id": image_id,
                    "bbox": (0.0, 0.0, 0.0, 0.0),
                }
            )
        except Exception:
            pass

    return elements
