"""Unit tests for PRD generator."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestPrdGenerator:
    def _write_silver_jsonl(self, path: Path, pages: list) -> None:
        with open(path, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")

    def test_generates_prd_file(self, tmp_path: Path) -> None:
        from docmeld.prd.generator import generate_prd

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {"uuid": "1", "source": "test.pdf", "page_no": "1", "session_title": "Test"}, "page_content": "This paper proposes a novel approach to real-time video generation using diffusion models."},
            {"metadata": {"uuid": "2", "source": "test.pdf", "page_no": "2", "session_title": "Test"}, "page_content": "Our system achieves 30fps on consumer GPUs with quality comparable to state-of-the-art."},
        ])

        mock_client = MagicMock()
        mock_client.generate.return_value = (
            "## Problem Statement\nReal-time video generation is slow.\n\n"
            "## Proposed Solution\nDiffusion-based pipeline.\n\n"
            "## Key Features\n- 30fps generation\n- Consumer GPU support\n\n"
            "## Technical Requirements\n- GPU with 8GB VRAM\n\n"
            "## Target Users\nContent creators and game developers.\n\n"
            "## Success Metrics\n- 30fps at 720p resolution\n"
        )

        result = generate_prd(str(jsonl), mock_client, source_pdf="test.pdf")

        assert Path(result.output_path).exists()
        assert result.sections == 6
        assert result.source_pdf == "test.pdf"
        assert not result.skipped
        mock_client.generate.assert_called_once()

    def test_idempotency_skips_existing(self, tmp_path: Path) -> None:
        from docmeld.prd.generator import generate_prd

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {}, "page_content": "content"},
        ])

        # Pre-create the PRD file
        prd_path = tmp_path / "paper_abc_prd.md"
        prd_path.write_text(
            "# PRD\n\n## Problem Statement\nX\n\n## Proposed Solution\nY\n\n"
            "## Key Features\nZ\n\n## Technical Requirements\nA\n\n"
            "## Target Users\nB\n\n## Success Metrics\nC\n"
        )

        mock_client = MagicMock()
        result = generate_prd(str(jsonl), mock_client, source_pdf="test.pdf")

        assert result.skipped
        assert result.sections == 6
        mock_client.generate.assert_not_called()

    def test_raises_on_empty_content(self, tmp_path: Path) -> None:
        from docmeld.prd.generator import generate_prd

        jsonl = tmp_path / "paper_abc.jsonl"
        jsonl.write_text("")

        mock_client = MagicMock()
        with pytest.raises(ValueError, match="No content found"):
            generate_prd(str(jsonl), mock_client)

    def test_no_partial_file_on_api_failure(self, tmp_path: Path) -> None:
        from docmeld.prd.generator import generate_prd

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {}, "page_content": "some content"},
        ])

        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("API down")

        prd_path = tmp_path / "paper_abc_prd.md"
        with pytest.raises(RuntimeError):
            generate_prd(str(jsonl), mock_client)

        assert not prd_path.exists()


class TestAggregateContent:
    def test_short_content_unchanged(self) -> None:
        from docmeld.utils.content import aggregate_content

        pages = ["Page 1 content", "Page 2 content"]
        result = aggregate_content(pages)
        assert "Page 1 content" in result
        assert "Page 2 content" in result

    def test_long_content_truncated(self) -> None:
        from docmeld.utils.content import aggregate_content

        pages = ["x" * 20000, "y" * 20000]
        result = aggregate_content(pages, max_chars=1000)
        assert len(result) <= 1100  # Some overhead for separator
        assert "truncated" in result


class TestBuildPrdPrompt:
    def test_includes_all_sections(self) -> None:
        from docmeld.prd.generator import _build_prd_prompt

        prompt = _build_prd_prompt("paper content", "test.pdf")
        assert "Problem Statement" in prompt
        assert "Proposed Solution" in prompt
        assert "Key Features" in prompt
        assert "Technical Requirements" in prompt
        assert "Target Users" in prompt
        assert "Success Metrics" in prompt
        assert "test.pdf" in prompt

    def test_includes_paper_content(self) -> None:
        from docmeld.prd.generator import _build_prd_prompt

        prompt = _build_prd_prompt("my unique content here", "")
        assert "my unique content here" in prompt


class TestParsePrdResponse:
    def test_strips_code_fences(self) -> None:
        from docmeld.prd.generator import _parse_prd_response

        response = "```markdown\n## Problem Statement\nContent\n```"
        result = _parse_prd_response(response)
        assert "```" not in result
        assert "## Problem Statement" in result

    def test_adds_title_if_missing(self) -> None:
        from docmeld.prd.generator import _parse_prd_response

        response = "## Problem Statement\nContent"
        result = _parse_prd_response(response, "paper.pdf")
        assert result.startswith("# Product Requirements Document: paper.pdf")
