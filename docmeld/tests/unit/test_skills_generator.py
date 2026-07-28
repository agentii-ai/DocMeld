"""Unit tests for skills generator."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestSkillsGenerator:
    def _write_silver_jsonl(self, path: Path, pages: list) -> None:
        with open(path, "w") as f:
            for page in pages:
                f.write(json.dumps(page) + "\n")

    def test_generates_skill_files(self, tmp_path: Path) -> None:
        from docmeld.skills.generator import generate_skills

        jsonl = tmp_path / "book_abc.jsonl"
        self._write_silver_jsonl(jsonl, [
            {"metadata": {}, "page_content": "Chapter 1: Always write tests first. Step 1: identify the behavior. Step 2: write a failing test."},
        ])

        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({
            "skills": [
                {
                    "title": "Write Tests First",
                    "description": "Apply TDD methodology",
                    "steps": ["Identify the behavior", "Write a failing test", "Implement minimum code"],
                    "examples": ["When adding a new API endpoint, write the request/response test first"],
                },
                {
                    "title": "Apply Single Responsibility",
                    "description": "Each class should have one reason to change",
                    "steps": ["Identify responsibilities", "Extract into separate classes"],
                    "examples": ["A UserService should not handle email sending"],
                },
            ]
        })

        result = generate_skills(str(jsonl), mock_client, source_pdf="clean_code.pdf")

        assert Path(result.output_dir).exists()
        assert result.skill_count == 2
        assert not result.skipped

        skill_files = list(Path(result.output_dir).glob("*.md"))
        assert len(skill_files) == 2

        # Check filenames are kebab-case
        names = sorted(f.name for f in skill_files)
        assert "write-tests-first.md" in names
        assert "apply-single-responsibility.md" in names

    def test_idempotency_skips_existing(self, tmp_path: Path) -> None:
        from docmeld.skills.generator import generate_skills

        jsonl = tmp_path / "book_abc.jsonl"
        self._write_silver_jsonl(jsonl, [{"metadata": {}, "page_content": "content"}])

        skills_dir = tmp_path / "_skills"
        skills_dir.mkdir()
        (skills_dir / "existing-skill.md").write_text("# Existing Skill\n")

        mock_client = MagicMock()
        result = generate_skills(str(jsonl), mock_client, source_pdf="book.pdf")

        assert result.skipped
        assert result.skill_count == 1
        mock_client.generate.assert_not_called()

    def test_raises_on_empty_content(self, tmp_path: Path) -> None:
        from docmeld.skills.generator import generate_skills

        jsonl = tmp_path / "book_abc.jsonl"
        jsonl.write_text("")

        mock_client = MagicMock()
        with pytest.raises(ValueError, match="No content found"):
            generate_skills(str(jsonl), mock_client)

    def test_raises_on_no_skills_extracted(self, tmp_path: Path) -> None:
        from docmeld.skills.generator import generate_skills

        jsonl = tmp_path / "book_abc.jsonl"
        self._write_silver_jsonl(jsonl, [{"metadata": {}, "page_content": "content"}])

        mock_client = MagicMock()
        mock_client.generate.return_value = '{"skills": []}'

        with pytest.raises(ValueError, match="No skills could be extracted"):
            generate_skills(str(jsonl), mock_client)

    def test_no_partial_output_on_api_failure(self, tmp_path: Path) -> None:
        from docmeld.skills.generator import generate_skills

        jsonl = tmp_path / "book_abc.jsonl"
        self._write_silver_jsonl(jsonl, [{"metadata": {}, "page_content": "content"}])

        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("API down")

        skills_dir = tmp_path / "_skills"
        with pytest.raises(RuntimeError):
            generate_skills(str(jsonl), mock_client)

        assert not skills_dir.exists()


class TestToKebabCase:
    def test_basic(self) -> None:
        from docmeld.skills.generator import _to_kebab_case

        assert _to_kebab_case("Write Tests First") == "write-tests-first"

    def test_special_characters(self) -> None:
        from docmeld.skills.generator import _to_kebab_case

        assert _to_kebab_case("Apply S.O.L.I.D. Principles!") == "apply-solid-principles"

    def test_multiple_spaces(self) -> None:
        from docmeld.skills.generator import _to_kebab_case

        assert _to_kebab_case("  Too   Many   Spaces  ") == "too-many-spaces"

    def test_empty_string(self) -> None:
        from docmeld.skills.generator import _to_kebab_case

        assert _to_kebab_case("") == "skill"

    def test_truncation(self) -> None:
        from docmeld.skills.generator import _to_kebab_case

        long_title = "a " * 100
        result = _to_kebab_case(long_title)
        assert len(result) <= 80


class TestParseSkillsResponse:
    def test_parses_valid_json(self) -> None:
        from docmeld.skills.generator import _parse_skills_response

        response = json.dumps({
            "skills": [{"title": "Test Skill", "description": "Desc", "steps": ["Do X"], "examples": ["Ex"]}]
        })
        result = _parse_skills_response(response)
        assert len(result) == 1
        assert result[0]["title"] == "Test Skill"
        assert "# Test Skill" in result[0]["content"]
        assert "Do X" in result[0]["content"]

    def test_strips_code_fences(self) -> None:
        from docmeld.skills.generator import _parse_skills_response

        response = '```json\n{"skills": [{"title": "A", "description": "", "steps": ["B"], "examples": []}]}\n```'
        result = _parse_skills_response(response)
        assert len(result) == 1

    def test_raises_on_malformed_json(self) -> None:
        from docmeld.skills.generator import _parse_skills_response

        with pytest.raises(ValueError, match="Failed to parse"):
            _parse_skills_response("not json")

    def test_skips_skills_without_title(self) -> None:
        from docmeld.skills.generator import _parse_skills_response

        response = json.dumps({
            "skills": [
                {"title": "", "description": "No title", "steps": [], "examples": []},
                {"title": "Valid", "description": "Has title", "steps": ["X"], "examples": []},
            ]
        })
        result = _parse_skills_response(response)
        assert len(result) == 1
        assert result[0]["title"] == "Valid"
