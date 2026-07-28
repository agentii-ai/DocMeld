"""Unit tests for workflow generator."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestWorkflowGenerator:
    def _write_silver_jsonl(self, path: Path, pages: list) -> None:
        with open(path, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")

    def test_generates_workflow_file(self, tmp_path: Path) -> None:
        from docmeld.workflow.generator import generate_workflow

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {"uuid": "1", "source": "test.pdf", "page_no": "1", "session_title": "Test"}, "page_content": "This paper proposes a three-stage pipeline for video generation."},
            {"metadata": {"uuid": "2", "source": "test.pdf", "page_no": "2", "session_title": "Test"}, "page_content": "Step 1: encode frames. Step 2: apply diffusion. Step 3: decode output."},
        ])

        mock_client = MagicMock()
        mock_client.generate.return_value = (
            "## Prerequisites\n- Python 3.9+\n- GPU with 8GB VRAM\n\n"
            "## Steps\n1. Install dependencies\n2. Prepare dataset\n3. Run training\n\n"
            "## Decision Points\n- Choose batch size based on GPU memory\n\n"
            "## Expected Outputs\n- Trained model checkpoint\n\n"
            "## Validation Criteria\n- FID score below 50\n"
        )

        result = generate_workflow(str(jsonl), mock_client, source_pdf="test.pdf")

        assert Path(result.output_path).exists()
        assert result.sections == 5
        assert result.source_pdf == "test.pdf"
        assert not result.skipped
        mock_client.generate.assert_called_once()

    def test_idempotency_skips_existing(self, tmp_path: Path) -> None:
        from docmeld.workflow.generator import generate_workflow

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {}, "page_content": "content"},
        ])

        wf_path = tmp_path / "paper_abc_workflow.md"
        wf_path.write_text(
            "# Workflow\n\n## Prerequisites\nX\n\n## Steps\n1. Y\n\n"
            "## Decision Points\nZ\n\n## Expected Outputs\nA\n\n"
            "## Validation Criteria\nB\n"
        )

        mock_client = MagicMock()
        result = generate_workflow(str(jsonl), mock_client, source_pdf="test.pdf")

        assert result.skipped
        assert result.sections == 5
        mock_client.generate.assert_not_called()

    def test_raises_on_empty_content(self, tmp_path: Path) -> None:
        from docmeld.workflow.generator import generate_workflow

        jsonl = tmp_path / "paper_abc.jsonl"
        jsonl.write_text("")

        mock_client = MagicMock()
        with pytest.raises(ValueError, match="No content found"):
            generate_workflow(str(jsonl), mock_client)

    def test_no_partial_file_on_api_failure(self, tmp_path: Path) -> None:
        from docmeld.workflow.generator import generate_workflow

        jsonl = tmp_path / "paper_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {}, "page_content": "some content"},
        ])

        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("API down")

        wf_path = tmp_path / "paper_abc_workflow.md"
        with pytest.raises(RuntimeError):
            generate_workflow(str(jsonl), mock_client)

        assert not wf_path.exists()


class TestBuildWorkflowPrompt:
    def test_includes_all_sections(self) -> None:
        from docmeld.workflow.generator import _build_workflow_prompt

        prompt = _build_workflow_prompt("paper content", "test.pdf")
        assert "Prerequisites" in prompt
        assert "Steps" in prompt
        assert "Decision Points" in prompt
        assert "Expected Outputs" in prompt
        assert "Validation Criteria" in prompt
        assert "test.pdf" in prompt

    def test_includes_paper_content(self) -> None:
        from docmeld.workflow.generator import _build_workflow_prompt

        prompt = _build_workflow_prompt("my unique content here", "")
        assert "my unique content here" in prompt


class TestParseWorkflowResponse:
    def test_strips_code_fences(self) -> None:
        from docmeld.workflow.generator import _parse_workflow_response

        response = "```markdown\n## Prerequisites\nContent\n```"
        result = _parse_workflow_response(response)
        assert "```" not in result
        assert "## Prerequisites" in result

    def test_adds_title_if_missing(self) -> None:
        from docmeld.workflow.generator import _parse_workflow_response

        response = "## Prerequisites\nContent"
        result = _parse_workflow_response(response, "paper.pdf")
        assert result.startswith("# Workflow: paper.pdf")
