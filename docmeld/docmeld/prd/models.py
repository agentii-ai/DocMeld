"""Pydantic models for PRD generation."""

from __future__ import annotations

from pydantic import BaseModel


class PrdResult(BaseModel):
    """Result of PRD generation."""

    output_path: str
    sections: int
    source_pdf: str
    skipped: bool = False
