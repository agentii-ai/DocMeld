"""Shared text helper: strip markdown code fences.

Used by deepseek_client, prd, workflow, skills generators, and categorizer.
"""

from __future__ import annotations


def strip_code_fences(text: str) -> str:
    """Remove surrounding markdown code fences (```` ``` ... ``` ````).

    Args:
        text: Raw response text that may be wrapped in code fences.

    Returns:
        Text with leading/trailing code fence markers removed.
    """
    stripped = text.strip()

    # Remove leading fence line
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Drop the opening fence line
        if len(lines) > 1:
            lines = lines[1:]
            # Drop closing fence line if present
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        else:
            # Single line starting with ``` — just strip the backticks
            stripped = stripped.lstrip("`").strip()

    return stripped
