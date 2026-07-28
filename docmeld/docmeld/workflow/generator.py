"""Workflow generator - extract step-by-step workflows from paper content."""

from __future__ import annotations

import logging
from pathlib import Path

from docmeld.gold.provider import LLMProvider
from docmeld.utils.content import aggregate_content
from docmeld.utils.silver_io import load_silver_content
from docmeld.utils.text import strip_code_fences
from docmeld.workflow.models import WorkflowResult

logger = logging.getLogger("docmeld")

WORKFLOW_SECTIONS = [
    "Prerequisites",
    "Steps",
    "Decision Points",
    "Expected Outputs",
    "Validation Criteria",
]


def generate_workflow(
    silver_jsonl_path: str, client: LLMProvider, source_pdf: str = ""
) -> WorkflowResult:
    """Generate a workflow markdown file from a silver JSONL file.

    Args:
        silver_jsonl_path: Path to the silver JSONL file.
        client: DeepSeekClient instance with generate_prd() method (reused for API calls).
        source_pdf: Original PDF filename for metadata.

    Returns:
        WorkflowResult with output path and section count.
    """
    jsonl_path = Path(silver_jsonl_path)
    output_dir = jsonl_path.parent
    wf_path = output_dir / (jsonl_path.stem.replace("_gold", "") + "_workflow.md")

    # Idempotency check
    if wf_path.exists():
        content = wf_path.read_text(encoding="utf-8")
        section_count = sum(1 for s in WORKFLOW_SECTIONS if f"## {s}" in content)
        return WorkflowResult(
            output_path=str(wf_path),
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

    # Generate workflow via API
    prompt = _build_workflow_prompt(aggregated, source_pdf)
    logger.info(f"Generating workflow for {source_pdf or jsonl_path.name}...")

    response_text = client.generate(prompt)
    wf_content = _parse_workflow_response(response_text, source_pdf)

    # Atomic write
    wf_path.write_text(wf_content, encoding="utf-8")

    section_count = sum(1 for s in WORKFLOW_SECTIONS if f"## {s}" in wf_content)
    logger.info(f"Workflow written to {wf_path} ({section_count} sections)")

    return WorkflowResult(
        output_path=str(wf_path),
        sections=section_count,
        source_pdf=source_pdf,
    )


def _build_workflow_prompt(content: str, source_name: str = "") -> str:
    """Build the prompt for workflow generation."""
    source_label = f' "{source_name}"' if source_name else ""

    return (
        f"You are a technical analyst extracting a reproducible workflow from a research paper{source_label}. "
        "Based on the paper content below, generate a step-by-step workflow document.\n\n"
        "The workflow MUST have exactly these five sections as markdown H2 headers:\n"
        "## Prerequisites\n"
        "## Steps\n"
        "## Decision Points\n"
        "## Expected Outputs\n"
        "## Validation Criteria\n\n"
        "Rules:\n"
        "- Prerequisites: list required tools, data, knowledge, and environment setup\n"
        "- Steps: numbered, ordered, actionable steps to reproduce the paper's approach\n"
        "- Decision Points: branching logic or choices the practitioner must make\n"
        "- Expected Outputs: what each major step should produce\n"
        "- Validation Criteria: how to verify the workflow was executed correctly\n"
        "- All content must be derived from the paper\n"
        "- Steps must be concrete and actionable, not vague\n"
        "- Use numbered lists for Steps, bullet points for other sections\n\n"
        f"Paper content:\n\n{content}"
    )


def _parse_workflow_response(response_text: str, source_name: str = "") -> str:
    """Parse the API response into a formatted workflow markdown document."""
    text = response_text.strip()

    # Strip code fences if present
    text = strip_code_fences(text)

    # Add title header if not present
    if not text.startswith("# "):
        title = "# Workflow"
        if source_name:
            title += f": {source_name}"
        text = f"{title}\n\n{text}"

    return text
