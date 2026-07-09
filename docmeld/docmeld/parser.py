"""DocMeld main parser - orchestrates the full pipeline."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from docmeld.bronze.processor import BronzeProcessor
from docmeld.silver.page_models import (
    BronzeResult,
    CategorizeResult,
    GoldResult,
    ProcessingResult,
    SilverResult,
)
from docmeld.silver.processor import SilverProcessor

logger = logging.getLogger("docmeld")


class DocMeldParser:
    """Main entry point for the DocMeld pipeline.

    Supports processing a single PDF file or a folder of PDFs
    through bronze, silver, and gold stages.
    """

    def __init__(self, path: str, output_dir: Optional[str] = None, backend: str = "pymupdf") -> None:
        self.path = path
        self.output_dir = output_dir
        self.backend = backend
        self._is_folder = Path(path).is_dir()

    def process_bronze(self) -> BronzeResult | ProcessingResult:
        """Run bronze stage only."""
        processor = BronzeProcessor()
        if self._is_folder:
            return processor.process_folder(self.path, backend=self.backend)
        return processor.process_file(self.path, backend=self.backend)

    def process_silver(self, bronze_json_path: str) -> SilverResult:
        """Run silver stage on a bronze JSON file."""
        processor = SilverProcessor()
        return processor.process(bronze_json_path)

    def process_gold(self, silver_jsonl_path: str) -> GoldResult:
        """Run gold stage on a silver JSONL file."""
        from docmeld.gold.processor import GoldProcessor
        from docmeld.utils.env_loader import load_env

        env = load_env(require_api_key=True)
        processor = GoldProcessor(
            api_key=env["DEEPSEEK_API_KEY"],
            endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
            temperature=1.0,
        )
        return processor.process(silver_jsonl_path)

    def process_all(self) -> ProcessingResult:
        """Run the full pipeline: bronze → silver → gold.

        For folder input, processes all PDFs through all stages.
        For single file, processes through all three stages.
        """
        start_time = time.time()
        bronze_processor = BronzeProcessor()
        silver_processor = SilverProcessor()

        if self._is_folder:
            folder_result = bronze_processor.process_folder(self.path, backend=self.backend)
            # Process silver and gold for each successful bronze output
            folder = Path(self.path)
            for subdir in sorted(folder.iterdir()):
                json_files = list(subdir.glob("*.json")) if subdir.is_dir() else []
                for json_file in json_files:
                    try:
                        silver_result = silver_processor.process(str(json_file))
                        try:
                            self.process_gold(silver_result.output_path)
                        except Exception as e:
                            logger.warning(f"Gold stage skipped for {json_file.name}: {e}")
                    except Exception as e:
                        logger.warning(f"Silver stage failed for {json_file.name}: {e}")

            elapsed = time.time() - start_time
            folder_result.processing_time_seconds = round(elapsed, 2)
            return folder_result
        bronze_result = bronze_processor.process_file(self.path, backend=self.backend)
        silver_result = silver_processor.process(bronze_result.output_path)

        gold_failed = False
        try:
            self.process_gold(silver_result.output_path)
        except Exception as e:
            logger.warning(f"Gold stage skipped: {e}")
            gold_failed = True

        elapsed = time.time() - start_time
        return ProcessingResult(
            total_files=1,
            successful=1,
            failed=0,
            failures=[],
            processing_time_seconds=round(elapsed, 2),
            output_directory=bronze_result.output_dir,
            log_file="",
        )

    def process_categorize(self, reorganize: bool = False) -> CategorizeResult:
        """Run bronze→silver + categorization on a folder of PDFs.

        Skips the gold stage entirely. Instead, reads silver JSONL content
        directly (first 30k chars per paper) and sends it to DeepSeek
        for categorization in a single API call.

        Args:
            reorganize: If True, move files into category subdirectories.

        Returns:
            CategorizeResult with index path and statistics.
        """
        if not self._is_folder:
            raise ValueError("process_categorize() requires a folder path, not a single file")

        folder = Path(self.path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {self.path}")

        pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))
        if not pdf_files:
            logger.warning(f"No PDFs found in {self.path}")
            return CategorizeResult(
                index_path="",
                total_papers=0,
                total_categories=0,
                papers_failed=0,
                reorganized=False,
            )

        # Step 1: Run bronze → silver only (skip gold)
        bronze_processor = BronzeProcessor()
        silver_processor = SilverProcessor()

        logger.info(f"Processing {len(pdf_files)} PDFs through bronze → silver...")
        bronze_result = bronze_processor.process_folder(self.path, backend=self.backend)

        for subdir in sorted(folder.iterdir()):
            json_files = list(subdir.glob("*.json")) if subdir.is_dir() else []
            for json_file in json_files:
                try:
                    silver_processor.process(str(json_file))
                except Exception as e:
                    logger.warning(f"Silver stage failed for {json_file.name}: {e}")

        # Step 2: Aggregate silver content
        from docmeld.categorize.aggregator import aggregate_paper_metadata

        papers = aggregate_paper_metadata(self.path)
        if not papers:
            logger.warning("No silver content found to categorize")
            return CategorizeResult(
                index_path="",
                total_papers=0,
                total_categories=0,
                papers_failed=0,
                reorganized=False,
            )

        # Step 3: Categorize via DeepSeek (single API call)
        from docmeld.categorize.categorizer import categorize_papers
        from docmeld.gold.deepseek_client import DeepSeekClient
        from docmeld.utils.env_loader import load_env

        env = load_env(require_api_key=True)
        client = DeepSeekClient(
            api_key=env["DEEPSEEK_API_KEY"],
            endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
        )

        categories, paper_descs = categorize_papers(papers, client)

        # Enrich papers with descriptions/keywords from the API response
        desc_map = {d["filename"]: d for d in paper_descs}
        for p in papers:
            info = desc_map.get(p.filename, {})
            p.description = info.get("description", "")
            p.keywords = info.get("keywords", [])

        # Step 4: Write categories.json
        from docmeld.categorize.index_writer import write_category_index

        index_path = write_category_index(self.path, papers, categories)

        # Step 5: Optionally reorganize
        if reorganize:
            from docmeld.categorize.reorganizer import reorganize_by_category

            reorganize_by_category(self.path)

        return CategorizeResult(
            index_path=index_path,
            total_papers=len(papers),
            total_categories=len(categories),
            papers_failed=0,
            reorganized=reorganize,
        )

    def process_prd(self) -> PrdResult:
        """Generate a PRD from a single PDF research paper.

        Processes the PDF through bronze→silver, then sends aggregated
        content to DeepSeek to generate a structured PRD markdown file.

        Returns:
            PrdResult with output path and section count.
        """
        if self._is_folder:
            raise ValueError("process_prd() requires a single PDF file, not a folder")

        from docmeld.prd.generator import generate_prd

        # Step 1: Bronze
        bronze_result = self.process_bronze()
        if not hasattr(bronze_result, "output_path"):
            raise RuntimeError("Bronze processing failed")

        # Step 2: Silver
        silver_result = self.process_silver(bronze_result.output_path)

        # Step 3: Generate PRD
        from docmeld.gold.deepseek_client import DeepSeekClient
        from docmeld.utils.env_loader import load_env

        env = load_env(require_api_key=True)
        client = DeepSeekClient(
            api_key=env["DEEPSEEK_API_KEY"],
            endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
        )

        return generate_prd(
            silver_jsonl_path=silver_result.output_path,
            client=client,
            source_pdf=Path(self.path).name,
        )

    def process_workflow(self) -> WorkflowResult:
        """Generate a workflow from a single PDF research paper.

        Processes the PDF through bronze→silver, then sends aggregated
        content to DeepSeek to generate a structured workflow markdown file.

        Returns:
            WorkflowResult with output path and section count.
        """
        if self._is_folder:
            raise ValueError("process_workflow() requires a single PDF file, not a folder")

        from docmeld.workflow.generator import generate_workflow

        # Step 1: Bronze
        bronze_result = self.process_bronze()
        if not hasattr(bronze_result, "output_path"):
            raise RuntimeError("Bronze processing failed")

        # Step 2: Silver
        silver_result = self.process_silver(bronze_result.output_path)

        # Step 3: Generate Workflow
        from docmeld.gold.deepseek_client import DeepSeekClient
        from docmeld.utils.env_loader import load_env

        env = load_env(require_api_key=True)
        client = DeepSeekClient(
            api_key=env["DEEPSEEK_API_KEY"],
            endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
        )

        return generate_workflow(
            silver_jsonl_path=silver_result.output_path,
            client=client,
            source_pdf=Path(self.path).name,
        )

    def process_skills(self) -> SkillsResult:
        """Extract Claude Code skills from a single PDF book.

        Processes the PDF through bronze→silver, then sends aggregated
        content to DeepSeek to extract structured skill files.

        Returns:
            SkillsResult with output directory and skill count.
        """
        if self._is_folder:
            raise ValueError("process_skills() requires a single PDF file, not a folder")

        from docmeld.skills.generator import generate_skills

        # Step 1: Bronze
        bronze_result = self.process_bronze()
        if not hasattr(bronze_result, "output_path"):
            raise RuntimeError("Bronze processing failed")

        # Step 2: Silver
        silver_result = self.process_silver(bronze_result.output_path)

        # Step 3: Generate Skills
        from docmeld.gold.deepseek_client import DeepSeekClient
        from docmeld.utils.env_loader import load_env

        env = load_env(require_api_key=True)
        client = DeepSeekClient(
            api_key=env["DEEPSEEK_API_KEY"],
            endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
        )

        return generate_skills(
            silver_jsonl_path=silver_result.output_path,
            client=client,
            source_pdf=Path(self.path).name,
        )
