"""Pydantic models for the categorize module."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Aggregated metadata for a single paper from its silver JSONL output."""

    filename: str
    file_path: str
    output_dir: str
    content: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    page_count: int = 0


class Category(BaseModel):
    """A topic cluster identified by the AI model."""

    name: str
    papers: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class PaperEntry(BaseModel):
    """A single paper's entry in the category index."""

    filename: str
    category: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class CategoryIndex(BaseModel):
    """Top-level structure written to categories.json."""

    created: str
    source_folder: str
    total_papers: int
    total_categories: int
    categories: list[Category] = Field(default_factory=list)
    papers: list[PaperEntry] = Field(default_factory=list)
