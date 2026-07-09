"""Run bronze → silver → _summary.md for all PDFs in a folder.

No gold layer. No categorization. Just .json, .jsonl, and _summary.md.

Usage:
    cd /Users/frank/A/DocMeld/docmeld
    source venv/bin/activate
    python run_bronze_silver_summary.py "/path/to/folder" --workers 10
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict

from docmeld.bronze.processor import BronzeProcessor
from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.silver.processor import SilverProcessor
from docmeld.summarize import SUMMARIZE_PROMPT, _call_summarize_api, assemble_paper_content
from docmeld.utils.env_loader import load_env
from docmeld.utils.logging import setup_logging

DEFAULT_WORKERS = 8


def run(folder_path: str, workers: int = DEFAULT_WORKERS) -> None:
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: folder not found: {folder_path}")
        sys.exit(1)

    # Find .env.local: try CWD first, then repo root
    env_path = Path.cwd() / ".env.local"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[1] / ".env.local"
    env = load_env(env_path=str(env_path), require_api_key=True)
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
    silver_proc = SilverProcessor()
    bronze_count = 0
    silver_count = 0
    skipped = 0

    for i, pdf in enumerate(pdf_files, 1):
        from docmeld.bronze.filename_sanitizer import get_output_name
        output_name = get_output_name(str(pdf))
        output_dir = pdf.parent / output_name
        json_path = output_dir / f"{output_name}.json"
        jsonl_path = output_dir / f"{output_name}.jsonl"

        if json_path.exists() and jsonl_path.exists():
            skipped += 1
            print(f"  [{i}/{len(pdf_files)}] skip (already done) {pdf.name[:70]}")
            continue

        try:
            if not json_path.exists():
                bronze_result = bronze.process_file(str(pdf))
                bronze_count += 1
            else:
                bronze_result = bronze.process_file(str(pdf))
            silver_proc.process(bronze_result.output_path)
            silver_count += 1
            print(f"  [{i}/{len(pdf_files)}] done {pdf.name[:70]}")
        except Exception as e:
            print(f"  [{i}/{len(pdf_files)}] FAIL {pdf.name[:70]} — {e}")

    print(f"Bronze: {bronze_count} new, Silver: {silver_count} new, {skipped} skipped")

    # ── Step 2: Generate _summary.md ─────────────────────────────────────
    print(f"\n=== Step 2: Generate _summary.md (workers={workers}) ===")
    tasks = []
    existing = 0
    for pdf in pdf_files:
        summary_path = folder / (pdf.stem + "_summary.md")
        from docmeld.bronze.filename_sanitizer import get_output_name
        output_name = get_output_name(str(pdf))
        output_dir = pdf.parent / output_name
        jsonl_path = output_dir / f"{output_name}.jsonl"
        if summary_path.exists():
            existing += 1
        elif jsonl_path.exists():
            tasks.append({
                "jsonl": jsonl_path,
                "pdf_name": pdf.name,
                "output": summary_path,
            })

    print(f"Summaries: {existing} exist, {len(tasks)} to generate")

    if tasks:
        success = 0
        failed = 0
        start = time.time()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for task in tasks:
                f = pool.submit(_summarize_one, client, task["jsonl"], task["pdf_name"], task["output"])
                futures[f] = task

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

    # ── Summary ──────────────────────────────────────────────────────────
    json_count = len(list(folder.glob("*/*.json")))
    jsonl_count = len(list(folder.glob("*/*.jsonl")))
    summary_count = len(list(folder.glob("*_summary.md")))

    print(f"\n=== Pipeline Complete ===")
    print(f"  .json files:    {json_count}")
    print(f"  .jsonl files:   {jsonl_count}")
    print(f"  _summary.md:    {summary_count}")
    print("Done!")


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


if __name__ == "__main__":
    import argparse

    setup_logging()

    parser = argparse.ArgumentParser(
        description="Run bronze → silver → _summary.md (no gold, no categorization)"
    )
    parser.add_argument("folder", help="Path to folder of PDFs")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent API calls for summarization (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()

    run(args.folder, workers=args.workers)
