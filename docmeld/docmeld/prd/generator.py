"""PRD generator - create Product Requirements Documents from paper content."""

from __future__ import annotations

import logging
from pathlib import Path

from docmeld.gold.provider import LLMProvider
from docmeld.prd.models import PrdResult
from docmeld.utils.content import aggregate_content
from docmeld.utils.silver_io import load_silver_content
from docmeld.utils.text import strip_code_fences

logger = logging.getLogger("docmeld")

PRD_SECTIONS = [
    "Problem Statement",
    "Proposed Solution",
    "Key Features",
    "Technical Requirements",
    "Target Users",
    "Success Metrics",
]


def generate_prd(silver_jsonl_path: str, client: LLMProvider, source_pdf: str = "") -> PrdResult:
    """Generate a PRD markdown file from a silver JSONL file.

    Args:
        silver_jsonl_path: Path to the silver JSONL file.
        client: An LLMProvider (e.g. DeepSeekClient).
        source_pdf: Original PDF filename for metadata.

    Returns:
        PrdResult with output path and section count.
    """
    jsonl_path = Path(silver_jsonl_path)
    output_dir = jsonl_path.parent
    prd_path = output_dir / (jsonl_path.stem.replace("_gold", "") + "_prd.md")

    # Idempotency check
    if prd_path.exists():
        content = prd_path.read_text(encoding="utf-8")
        section_count = sum(1 for s in PRD_SECTIONS if f"## {s}" in content)
        return PrdResult(
            output_path=str(prd_path),
            sections=section_count,
            source_pdf=source_pdf,
            skipped=True,
        )

    # Load silver pages
    pages = load_silver_content(str(jsonl_path))
    if not pages:
        msg = f"No content found in {silver_jsonl_path}"
        raise ValueError(msg)

    # Aggregate content (truncate for long papers)
    aggregated = aggregate_content(pages)

    # Generate PRD via API
    prompt = _build_prd_prompt(aggregated, source_pdf)
    logger.info(f"Generating PRD for {source_pdf or jsonl_path.name}...")

    response_text = client.generate(prompt)
    prd_content = _parse_prd_response(response_text, source_pdf)

    # Atomic write — only create file if generation succeeded
    prd_path.write_text(prd_content, encoding="utf-8")

    section_count = sum(1 for s in PRD_SECTIONS if f"## {s}" in prd_content)
    logger.info(f"PRD written to {prd_path} ({section_count} sections)")

    return PrdResult(
        output_path=str(prd_path),
        sections=section_count,
        source_pdf=source_pdf,
    )


def _build_prd_prompt(content: str, source_name: str = "") -> str:
    """Build the prompt for PRD generation."""
    source_label = f' "{source_name}"' if source_name else ""

    return (
        f"You are a product manager analyzing a research paper{source_label}. "
        "Based on the paper content below, generate a Product Requirements Document (PRD) "
        "that describes how this research could be turned into a product.\n\n"
        "The PRD MUST have exactly these six sections as markdown H2 headers:\n"
        "## Problem Statement\n"
        "## Proposed Solution\n"
        "## Key Features\n"
        "## Technical Requirements\n"
        "## Target Users\n"
        "## Success Metrics\n\n"
        "Rules:\n"
        "- All content must be derived from the paper — do not invent features not described\n"
        "- Problem Statement: extract from abstract/introduction\n"
        "- Proposed Solution: extract from methodology/approach sections\n"
        "- Key Features: list 3-8 concrete capabilities described in the paper\n"
        "- Technical Requirements: extract from implementation/system design sections\n"
        "- Target Users: infer from the paper's application domain\n"
        "- Success Metrics: extract from evaluation/results sections\n"
        "- Write in clear, concise product language (not academic)\n"
        "- Use bullet points for Key Features and Technical Requirements\n\n"
        f"Paper content:\n\n{content}"
    )


def _parse_prd_response(response_text: str, source_name: str = "") -> str:
    """Parse the API response into a formatted PRD markdown document."""
    text = response_text.strip()

    # Strip code fences if present
    text = strip_code_fences(text)

    # Add title header if not present
    if not text.startswith("# "):
        title = "# Product Requirements Document"
        if source_name:
            title += f": {source_name}"
        text = f"{title}\n\n{text}"

    return text
