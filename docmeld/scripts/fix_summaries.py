"""Move root-level summaries into category folders, then re-summarize failed papers.

Usage:
    cd /Users/frank/A/DocMeld/docmeld
    source venv/bin/activate
    python scripts/fix_summaries.py "/path/to/folder" --workers 5
"""
from __future__ import annotations

import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from docmeld.bronze.filename_sanitizer import calculate_hash
from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.utils.env_loader import load_env

# summarize.py is a sibling script in this folder, not part of the installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize import (
    SUMMARIZE_PROMPT,
    _call_summarize_api,
    assemble_paper_content,
)

DEFAULT_WORKERS = 5


def move_summaries(folder: Path) -> int:
    """Move root-level *_summary.md files into their category folders."""
    # Build PDF stem → category dir mapping by scanning category dirs for PDFs
    pdf_to_catdir: Dict[str, Path] = {}
    for cat_dir in sorted(folder.iterdir()):
        if not cat_dir.is_dir():
            continue
        for pdf in cat_dir.glob("*.pdf"):
            pdf_to_catdir[pdf.stem] = cat_dir
        for pdf in cat_dir.glob("*.PDF"):
            pdf_to_catdir[pdf.stem] = cat_dir

    moved = 0
    for summary in sorted(folder.glob("*_summary.md")):
        if not summary.is_file():
            continue
        # Derive the PDF stem: remove "_summary" suffix
        pdf_stem = summary.stem.replace("_summary", "")
        cat_dir = pdf_to_catdir.get(pdf_stem)
        if cat_dir:
            dest = cat_dir / summary.name
            if not dest.exists():
                shutil.move(str(summary), str(dest))
                print(f"  Moved: {summary.name} → {cat_dir.name}/")
                moved += 1
            else:
                # Already exists in category dir, remove root copy
                summary.unlink()
                moved += 1
        else:
            print(f"  No match: {summary.name}")
    return moved


def summarize_missing(folder: Path, client: DeepSeekClient, workers: int) -> None:
    """Find papers missing summaries and generate them."""
    tasks: List[Dict] = []

    for cat_dir in sorted(folder.iterdir()):
        if not cat_dir.is_dir():
            continue
        if cat_dir.name.startswith(".") or cat_dir.name.startswith("_"):
            continue

        for pdf in sorted(list(cat_dir.glob("*.pdf")) + list(cat_dir.glob("*.PDF"))):
            summary_path = cat_dir / (pdf.stem + "_summary.md")
            if summary_path.exists():
                continue

            # Find the JSONL for this PDF
            h = calculate_hash(str(pdf))
            jsonl_path = None
            for subdir in cat_dir.iterdir():
                if subdir.is_dir() and subdir.name.endswith(f"_{h}"):
                    candidates = [f for f in subdir.glob("*.jsonl") if not f.name.endswith("_gold.jsonl")]
                    if candidates:
                        jsonl_path = candidates[0]
                    break

            if jsonl_path:
                tasks.append({
                    "jsonl": jsonl_path,
                    "pdf_name": pdf.name,
                    "output": summary_path,
                })

    total_pdfs = sum(1 for d in folder.iterdir() if d.is_dir() for _ in d.glob("*.pdf"))
    existing = total_pdfs - len(tasks)
    print(f"Total PDFs: {total_pdfs}, summaries exist: {existing}, to generate: {len(tasks)}")

    if not tasks:
        print("All papers already summarized.")
        return

    success = 0
    failed = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_do_summarize, client, t): t for t in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            idx = existing + success + failed + 1
            name = result["pdf_name"][:65]
            if result.get("ok"):
                success += 1
                print(f"  [{idx}/{total_pdfs}] done {name}")
            else:
                failed += 1
                err = result.get("error", "unknown")
                print(f"  [{idx}/{total_pdfs}] FAIL {name} — {err}")

    elapsed = time.time() - start
    print(f"Summarized: {success} new, {failed} failed, {elapsed:.0f}s")


def _do_summarize(client: DeepSeekClient, task: Dict) -> Dict:
    jsonl_path = task["jsonl"]
    pdf_name = task["pdf_name"]
    output_path = task["output"]

    if output_path.exists():
        return {**task, "ok": True, "skipped": True}

    full_content = assemble_paper_content(jsonl_path)
    if not full_content:
        return {**task, "ok": False, "error": "empty content"}

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
        return {**task, "ok": True, "skipped": False}
    except Exception as e:
        return {**task, "ok": False, "error": str(e)}


def main(folder_path: str, workers: int = DEFAULT_WORKERS) -> None:
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: folder not found: {folder_path}")
        sys.exit(1)

    env = load_env(env_path=str(Path(__file__).resolve().parents[2] / ".env.local"), require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )

    print("=== Step 1: Move summaries into category folders ===")
    moved = move_summaries(folder)
    print(f"Moved {moved} summary files\n")

    print(f"=== Step 2: Generate missing summaries (workers={workers}) ===")
    summarize_missing(folder, client, workers)
    print("\nDone!")


if __name__ == "__main__":
    import argparse

    from docmeld.utils.logging import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Move summaries + re-summarize failed papers")
    parser.add_argument("folder", help="Path to categorized folder")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent API calls (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()
    main(args.folder, workers=args.workers)
