"""Unit tests for the categorize categorizer."""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from docmeld.categorize.models import PaperMetadata


def _make_paper(filename: str, content: str = "") -> PaperMetadata:
    return PaperMetadata(
        filename=filename,
        file_path=f"/tmp/{filename}",
        output_dir=f"/tmp/{filename}_out",
        content=content or f"Content about {filename}",
        page_count=1,
    )


class TestCategorizer:
    def test_builds_sorted_prompt(self) -> None:
        from docmeld.categorize.categorizer import _build_categorization_prompt

        papers = [
            _make_paper("z_paper.jsonl"),
            _make_paper("a_paper.jsonl"),
        ]
        prompt = _build_categorization_prompt(papers)
        assert prompt.index("a_paper.jsonl") < prompt.index("z_paper.jsonl")

    def test_parses_valid_response(self) -> None:
        from docmeld.categorize.categorizer import _parse_categorization_response

        response = '{"categories": [{"name": "NLP", "papers": ["a.jsonl"], "keywords": ["nlp"]}], "paper_descriptions": []}'
        categories, descs = _parse_categorization_response(response)
        assert len(categories) == 1
        assert categories[0]["name"] == "NLP"
        assert categories[0]["papers"] == ["a.jsonl"]

    def test_parses_response_with_code_fences(self) -> None:
        from docmeld.categorize.categorizer import _parse_categorization_response

        response = '```json\n{"categories": [{"name": "CV", "papers": ["b.jsonl"], "keywords": ["vision"]}]}\n```'
        categories, descs = _parse_categorization_response(response)
        assert len(categories) == 1
        assert categories[0]["name"] == "CV"

    def test_parses_paper_descriptions(self) -> None:
        from docmeld.categorize.categorizer import _parse_categorization_response

        response = '{"categories": [{"name": "NLP", "papers": ["a.jsonl"], "keywords": ["nlp"]}], "paper_descriptions": [{"filename": "a.jsonl", "description": "About NLP", "keywords": ["nlp"]}]}'
        categories, descs = _parse_categorization_response(response)
        assert len(descs) == 1
        assert descs[0]["description"] == "About NLP"

    def test_raises_on_malformed_response(self) -> None:
        from docmeld.categorize.categorizer import _parse_categorization_response

        with pytest.raises(ValueError, match="Failed to parse"):
            _parse_categorization_response("not json at all")

    def test_raises_on_missing_categories_key(self) -> None:
        from docmeld.categorize.categorizer import _parse_categorization_response

        with pytest.raises(ValueError, match="Missing 'categories'"):
            _parse_categorization_response('{"data": []}')

    def test_categorize_papers_calls_api(self) -> None:
        from docmeld.categorize.categorizer import categorize_papers

        papers = [
            _make_paper("paper1.jsonl", "NLP transformers content"),
            _make_paper("paper2.jsonl", "Computer vision CNN content"),
        ]

        mock_response = '{"categories": [{"name": "NLP", "papers": ["paper1.jsonl"], "keywords": ["nlp"]}, {"name": "CV", "papers": ["paper2.jsonl"], "keywords": ["vision"]}], "paper_descriptions": []}'

        mock_client = MagicMock()
        mock_client.categorize.return_value = mock_response

        categories, descs = categorize_papers(papers, mock_client)
        assert len(categories) == 2
        assert mock_client.categorize.call_count >= 2

    def test_deterministic_sorting(self) -> None:
        from docmeld.categorize.categorizer import _build_categorization_prompt

        papers_a = [_make_paper("c.jsonl"), _make_paper("a.jsonl"), _make_paper("b.jsonl")]
        papers_b = [_make_paper("b.jsonl"), _make_paper("a.jsonl"), _make_paper("c.jsonl")]

        prompt_a = _build_categorization_prompt(papers_a)
        prompt_b = _build_categorization_prompt(papers_b)
        assert prompt_a == prompt_b
