"""Pydantic models for skills extraction."""

from __future__ import annotations

from pydantic import BaseModel


class SkillsResult(BaseModel):
    """Result of skills extraction."""

    output_dir: str
    skill_count: int
    source_pdf: str
    skipped: bool = False
