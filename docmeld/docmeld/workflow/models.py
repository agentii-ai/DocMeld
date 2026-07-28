"""Pydantic models for workflow generation."""

from __future__ import annotations

from pydantic import BaseModel


class WorkflowResult(BaseModel):
    """Result of workflow generation."""

    output_path: str
    sections: int
    source_pdf: str
    skipped: bool = False
