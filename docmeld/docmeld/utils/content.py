"""Shared content aggregation helper (head/tail truncation strategy).

Used by prd, workflow, and skills generators to fit document content
within LLM context windows.
"""

from __future__ import annotations

#: Maximum characters sent to the LLM per document (30k).
MAX_CONTENT_CHARS: int = 30000

#: Fraction of content budget reserved for the document head (first pages).
HEAD_RATIO: float = 0.6


def aggregate_content(
    pages: list[str],
    max_chars: int = MAX_CONTENT_CHARS,
    head_ratio: float = HEAD_RATIO,
) -> str:
    """Aggregate page content with head/tail truncation for LLM context windows.

    When total content exceeds ``max_chars``, the first ``head_ratio`` fraction
    comes from the head (early pages) and the remainder from the tail (late pages),
    with a truncation marker in between.

    Args:
        pages: List of page content strings in reading order.
        max_chars: Maximum total characters to include.
        head_ratio: Fraction of ``max_chars`` to take from the head.

    Returns:
        A single string with the aggregated content.
    """
    if not pages:
        return ""

    total = sum(len(p) for p in pages)
    if total <= max_chars:
        return "\n\n".join(pages)

    head_chars = int(max_chars * head_ratio)
    tail_chars = max_chars - head_chars

    # Build head
    head_parts: list[str] = []
    used = 0
    for p in pages:
        if used + len(p) <= head_chars:
            head_parts.append(p)
            used += len(p)
        else:
            remaining = head_chars - used
            if remaining > 100:
                head_parts.append(p[:remaining] + "...")
            break

    # Build tail
    tail_parts: list[str] = []
    used = 0
    for p in reversed(pages):
        if used + len(p) <= tail_chars:
            tail_parts.append(p)
            used += len(p)
        else:
            remaining = tail_chars - used
            if remaining > 100:
                tail_parts.append("..." + p[-remaining:])
            break
    tail_parts.reverse()

    truncation_marker = f"\n\n[... {total - max_chars} characters truncated ...]\n\n"
    return "\n\n".join(head_parts) + truncation_marker + "\n\n".join(tail_parts)
