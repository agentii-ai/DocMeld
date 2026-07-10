"""Integration tests for CLI interface."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest


class TestCLI:
    def test_help_output(self) -> None:
        from docmeld.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_no_command_returns_1(self) -> None:
        from docmeld.cli import main

        result = main([])
        assert result == 1

    def test_invalid_path_returns_1(self) -> None:
        from docmeld.cli import main

        result = main(["bronze", "/nonexistent/path.pdf"])
        assert result == 1

    def test_bronze_single_file(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        from docmeld.cli import main

        shutil.copy(sample_simple_pdf, tmp_path / "test.pdf")
        result = main(["bronze", str(tmp_path / "test.pdf")])
        assert result == 0

    def test_bronze_folder(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        from docmeld.cli import main

        shutil.copy(sample_simple_pdf, tmp_path / "doc1.pdf")
        shutil.copy(sample_simple_pdf, tmp_path / "doc2.pdf")
        result = main(["bronze", str(tmp_path)])
        assert result == 0

    def test_silver_from_bronze(
        self, sample_simple_pdf: Path, tmp_path: Path
    ) -> None:
        from docmeld.cli import main
        from docmeld.bronze.processor import BronzeProcessor

        shutil.copy(sample_simple_pdf, tmp_path / "test.pdf")
        processor = BronzeProcessor()
        bronze_result = processor.process_file(str(tmp_path / "test.pdf"))

        result = main(["silver", bronze_result.output_path])
        assert result == 0


class TestCliPptx:
    """T068: CLI backend selection for PPT/PPTX."""

    PPT_SAMPLES = Path(__file__).resolve().parents[3] / "samples" / "ppt"

    def test_bronze_pptx_auto(self, tmp_path: Path) -> None:
        import shutil
        from docmeld.cli import main

        src = self.PPT_SAMPLES / "sample_pptx_basic.pptx"
        if not src.exists():
            pytest.skip("sample not found")
        shutil.copy(src, tmp_path / "deck.pptx")
        result = main(["bronze", str(tmp_path / "deck.pptx"), "--backend", "auto"])
        assert result == 0
        outputs = list(tmp_path.glob("deck_*/deck_*.json"))
        assert outputs, "expected bronze JSON output"

    def test_bronze_pptx_explicit_backend(self, tmp_path: Path) -> None:
        import shutil
        from docmeld.cli import main

        src = self.PPT_SAMPLES / "sample_pptx_image.pptx"
        if not src.exists():
            pytest.skip("sample not found")
        shutil.copy(src, tmp_path / "img.pptx")
        result = main(["bronze", str(tmp_path / "img.pptx"), "--backend", "pptx"])
        assert result == 0

    def test_pptx_backend_choice_accepted(self) -> None:
        from docmeld.cli import main

        # invalid path but valid backend choice → returns 1 (not argparse error 2)
        result = main(["bronze", "/nonexistent/deck.pptx", "--backend", "pptx"])
        assert result == 1
