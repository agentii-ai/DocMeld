"""Full batch pipeline: bronze → silver → article → categorize → summarize → reorganize.

Orchestrates the complete workflow for a folder of PDFs:
1. Bronze + Silver for all PDFs (skip already processed)
2. Generate _article.md from silver JSONL page_content
3. Categorize papers by topic via DeepSeek (x_y prefix ordering)
4. Generate _summary.md for papers missing summaries
5. Reorganize into category subdirectories

Usage:
    cd docmeld
    source venv/bin/activate
    python scripts/batch_pipeline.py "/path/to/folder" --workers 10
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict

from docmeld.bronze.filename_sanitizer import get_output_name
from docmeld.bronze.processor import BronzeProcessor
from docmeld.categorize.aggregator import aggregate_paper_metadata, generate_article_md
from docmeld.categorize.categorizer import categorize_papers
from docmeld.categorize.index_writer import write_category_index
from docmeld.categorize.reorganizer import reorganize_by_category
from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.silver.processor import SilverProcessor
from docmeld.utils.env_loader import load_env
from docmeld.utils.logging import setup_logging

# summarize.py is a sibling script in this folder, not part of the installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize import (
    SUMMARIZE_PROMPT,
    _call_summarize_api,
    assemble_paper_content,
)

logger = logging.getLogger("docmeld")

DEFAULT_WORKERS = 10


def _find_jsonl_for_pdf(pdf_path: Path) -> Path | None:
    """Find the silver JSONL file for a given PDF."""
    output_name = get_output_name(str(pdf_path))
    output_dir = pdf_path.parent / output_name
    jsonl_path = output_dir / f"{output_name}.jsonl"
    if jsonl_path.exists():
        return jsonl_path
    return None


def _summarize_one(client: DeepSeekClient, jsonl_path: Path, pdf_name: str, output_path: Path) -> Dict:
    """Summarize a single paper. Returns dict with 'ok' field."""
    if output_path.exists():
        return {"pdf_name": pdf_name, "ok": True, "skipped": True}

    full_content = assemble_paper_content(jsonl_path)
    if not full_content:
        return {"pdf_name": pdf_name, "ok": False, "error": "empty content"}

    truncated = full_content[:200000]
    prompt = SUMMARIZE_PROMPT + truncated

    try:
        response = call_with_retry(
            lambda: _call_summarize_api(client, prompt),
            max_retries=3,
            base_delay=2.0,
        )

        if not response.startswith(pdf_name):
            response = f"{pdf_name}\n\n{response}"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response)
            if not response.endswith("\n"):
                f.write("\n")

        return {"pdf_name": pdf_name, "ok": True, "skipped": False}

    except Exception as e:
        return {"pdf_name": pdf_name, "ok": False, "error": str(e)}


def run_pipeline(folder_path: str, workers: int = DEFAULT_WORKERS) -> None:
    """Run the full batch pipeline."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: folder not found: {folder_path}")
        sys.exit(1)

    env = load_env(env_path=str(Path(__file__).resolve().parents[2] / ".env.local"), require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )

    pdf_files = sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF"))
    if not pdf_files:
        print("No PDFs found.")
        return

    print(f"Found {len(pdf_files)} PDFs in {folder}")

    # ── Step 1: Bronze → Silver ──────────────────────────────────────────
    print("\n=== Step 1: Bronze → Silver ===")
    bronze = BronzeProcessor()
    silver = SilverProcessor()
    processed = 0
    skipped = 0

    for i, pdf in enumerate(pdf_files, 1):
        output_name = get_output_name(str(pdf))
        output_dir = pdf.parent / output_name
        json_path = output_dir / f"{output_name}.json"
        jsonl_path = output_dir / f"{output_name}.jsonl"

        if jsonl_path.exists():
            skipped += 1
            print(f"  [{i}/{len(pdf_files)}] skip {pdf.name[:70]}")
            continue

        try:
            bronze_result = bronze.process_file(str(pdf))
            silver.process(bronze_result.output_path)
            processed += 1
            print(f"  [{i}/{len(pdf_files)}] done {pdf.name[:70]}")
        except Exception as e:
            print(f"  [{i}/{len(pdf_files)}] FAIL {pdf.name[:70]} — {e}")

    print(f"Bronze→Silver: {processed} new, {skipped} skipped")

    # ── Step 2: Generate article .md from silver JSONL ───────────────────
    print("\n=== Step 2: Generate article markdown ===")
    article_count = 0
    for pdf in pdf_files:
        jsonl_path = _find_jsonl_for_pdf(pdf)
        if jsonl_path:
            md = generate_article_md(jsonl_path)
            if md:
                article_count += 1
    print(f"Articles: {article_count} generated/verified")

    # ── Step 3: Categorize ───────────────────────────────────────────────
    print("\n=== Step 3: Categorize papers ===")
    papers = aggregate_paper_metadata(folder_path)
    if not papers:
        print("No silver content found to categorize.")
        return

    print(f"Aggregated {len(papers)} papers, sending to DeepSeek for categorization...")
    categories, paper_descs = categorize_papers(papers, client)

    # Enrich papers with descriptions/keywords
    desc_map = {d["filename"]: d for d in paper_descs}
    for p in papers:
        info = desc_map.get(p.filename, {})
        p.description = info.get("description", "")
        p.keywords = info.get("keywords", [])

    index_path = write_category_index(folder_path, papers, categories)
    print(f"Categorized into {len(categories)} categories → {index_path}")

    # Print category summary
    for cat in sorted(categories, key=lambda c: c.get("name", "")):
        name = cat.get("name", "?")
        count = len(cat.get("papers", []))
        print(f"  {name} ({count} papers)")

    # ── Step 4: Summarize (before reorganize, in flat folder) ────────────
    print(f"\n=== Step 4: Summarize papers (workers={workers}) ===")
    summary_tasks = []
    for pdf in pdf_files:
        summary_path = pdf.parent / (pdf.stem + "_summary.md")
        jsonl_path = _find_jsonl_for_pdf(pdf)
        if jsonl_path and not summary_path.exists():
            summary_tasks.append({
                "jsonl": jsonl_path,
                "pdf_name": pdf.name,
                "output": summary_path,
            })

    existing = len(pdf_files) - len(summary_tasks)
    print(f"Summaries: {existing} exist, {len(summary_tasks)} to generate")

    if summary_tasks:
        success = 0
        failed = 0
        start = time.time()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _summarize_one, client,
                    task["jsonl"], task["pdf_name"], task["output"]
                ): task
                for task in summary_tasks
            }

            for future in as_completed(futures):
                result = future.result()
                idx = existing + success + failed + 1
                name = result["pdf_name"][:65]

                if result.get("ok"):
                    if result.get("skipped"):
                        print(f"  [{idx}/{len(pdf_files)}] skip {name}")
                    else:
                        success += 1
                        print(f"  [{idx}/{len(pdf_files)}] done {name}")
                else:
                    failed += 1
                    err = result.get("error", "unknown")
                    print(f"  [{idx}/{len(pdf_files)}] FAIL {name} — {err}")

        elapsed = time.time() - start
        print(f"Summarized: {success} new, {failed} failed, {elapsed:.0f}s")

    # ── Step 5: Reorganize into category folders ─────────────────────────
    print("\n=== Step 5: Reorganize into category folders ===")

    # Build PDF stem → summary path mapping BEFORE reorganize moves files
    summary_map: Dict[str, Path] = {}
    for pdf in pdf_files:
        summary_path = folder / (pdf.stem + "_summary.md")
        if summary_path.exists():
            summary_map[pdf.stem] = summary_path

    # Read categories.json to know where each paper goes
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    # Build PDF stem → category name mapping via hash matching
    stem_to_cat: Dict[str, str] = {}
    for entry in index.get("papers", []):
        jsonl_stem = entry["filename"].replace(".jsonl", "")
        cat_name = entry["category"]
        # Match back to PDF stem by finding the PDF whose hash matches
        for pdf in pdf_files:
            output_name = get_output_name(str(pdf))
            if output_name == jsonl_stem:
                stem_to_cat[pdf.stem] = cat_name
                break

    # Do the standard reorganize (moves PDFs + output dirs)
    reorganize_by_category(folder_path)

    # Now move summary files that are still in the root folder
    moved_summaries = 0
    for pdf_stem, summary_path in summary_map.items():
        if not summary_path.exists():
            continue
        cat_name = stem_to_cat.get(pdf_stem)
        if not cat_name:
            continue
        import re
        safe_cat = re.sub(r'[/\\:*?"<>|&;]', "_", cat_name.strip())
        safe_cat = re.sub(r"[_ ]+", " ", safe_cat).strip()
        if len(safe_cat) > 100:
            safe_cat = safe_cat[:100].rstrip()

        cat_dir = folder / safe_cat
        if cat_dir.exists():
            dest = cat_dir / summary_path.name
            if not dest.exists():
                shutil.move(str(summary_path), str(dest))
                moved_summaries += 1
                print(f"  Moved summary: {summary_path.name} → {safe_cat}/")

    print(f"Reorganized. Moved {moved_summaries} summary files.")
    print("\nDone!")


if __name__ == "__main__":
    import argparse

    setup_logging()

    parser = argparse.ArgumentParser(description="Full batch pipeline: bronze→silver→categorize→summarize→reorganize")
    parser.add_argument("folder", help="Path to folder of PDFs")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent API calls for summarization (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()

    run_pipeline(args.folder, workers=args.workers)
