"""Pydantic models for silver and gold pipeline stages."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SilverMetadata(BaseModel):
    uuid: str
    source: str
    page_no: str
    session_title: str


class SilverPage(BaseModel):
    metadata: SilverMetadata
    page_content: str


class GoldMetadata(SilverMetadata):
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    gold_processing_failed: bool | None = None


class GoldPage(BaseModel):
    metadata: GoldMetadata
    page_content: str


class ProcessingFailure(BaseModel):
    filename: str
    error: str


class ProcessingResult(BaseModel):
    total_files: int
    successful: int
    failed: int
    failures: list[ProcessingFailure] = Field(default_factory=list)
    processing_time_seconds: float = Field(ge=0)
    output_directory: str
    log_file: str


class BronzeResult(BaseModel):
    output_path: str
    output_dir: str
    element_count: int
    page_count: int
    skipped: bool = False


class SilverResult(BaseModel):
    output_path: str
    page_count: int
    skipped: bool = False


class GoldResult(BaseModel):
    output_path: str
    pages_enriched: int
    pages_failed: int
    skipped: bool = False


class CategorizeResult(BaseModel):
    index_path: str
    total_papers: int
    total_categories: int
    papers_failed: int = 0
    reorganized: bool = False
