"""Process PDFs in loop_prompts folder: bronze -> silver -> summary.

Generates .json, .jsonl, and _summary.md for each PDF.
Skips gold layer per-page metadata enrichment (no description/keywords in JSONL).

Usage:
    cd /Users/frank/A/DocMeld/docmeld && source venv/bin/activate
    python run_loop_prompts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the docmeld package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from docmeld.summarize import SUMMARIZE_PROMPT, _call_summarize_api, assemble_paper_content

from docmeld.bronze.filename_sanitizer import get_output_name
from docmeld.bronze.processor import BronzeProcessor
from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.silver.processor import SilverProcessor
from docmeld.utils.env_loader import load_env
from docmeld.utils.logging import setup_logging

TARGET_FOLDER = Path("/Users/frank/D/SynthRoute/refs/loop_prompts")
ENV_PATH = "/Users/frank/A/DocMeld/.env.local"


def generate_summary(client: DeepSeekClient, jsonl_path: Path, pdf_name: str,
                     output_path: Path) -> dict:
    """Generate a _summary.md for one paper via DeepSeek."""
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


def main():
    setup_logging()

    folder = TARGET_FOLDER
    pdf_files = sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF"))

    if not pdf_files:
        print("No PDFs found.")
        return

    print(f"Found {len(pdf_files)} PDF(s) in {folder}")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")

    # Load API key for summarization
    env = load_env(env_path=ENV_PATH, require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )
    print(f"API key loaded: {'DEEPSEEK_API_KEY' in env}")

    bronze = BronzeProcessor()
    silver = SilverProcessor()

    # ── Step 1: Bronze → Silver ──────────────────────────────────────────
    print("\n=== Step 1: Bronze → Silver ===")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf.name}")

        try:
            bronze_result = bronze.process_file(str(pdf))
            if bronze_result.skipped:
                print("  Bronze: SKIPPED (already exists)")
            else:
                print(f"  Bronze: {bronze_result.element_count} elements, "
                      f"{bronze_result.page_count} pages")
            print(f"  Output dir: {bronze_result.output_dir}")
        except Exception as e:
            print(f"  Bronze FAILED: {e}")
            continue

        try:
            silver_result = silver.process(bronze_result.output_path)
            if silver_result.skipped:
                print("  Silver: SKIPPED (already exists)")
            else:
                print(f"  Silver: {silver_result.page_count} pages")
            print(f"  JSONL: {silver_result.output_path}")
        except Exception as e:
            print(f"  Silver FAILED: {e}")
            continue

    # ── Step 2: Generate _summary.md ─────────────────────────────────────
    print("\n=== Step 2: Generate _summary.md ===")
    for i, pdf in enumerate(pdf_files, 1):
        output_name = get_output_name(str(pdf))
        output_dir = pdf.parent / output_name
        jsonl_path = output_dir / f"{output_name}.jsonl"
        summary_path = pdf.parent / (pdf.stem + "_summary.md")

        if not jsonl_path.exists():
            print(f"\n[{i}/{len(pdf_files)}] {pdf.name} — SKIP (no JSONL found)")
            continue

        print(f"\n[{i}/{len(pdf_files)}] {pdf.name}")
        print(f"  JSONL: {jsonl_path}")
        print(f"  Summary: {summary_path}")

        result = generate_summary(client, jsonl_path, pdf.name, summary_path)
        if result.get("ok"):
            if result.get("skipped"):
                print("  Summary: SKIPPED (already exists)")
            else:
                print(f"  Summary: DONE ({summary_path.stat().st_size} bytes)")
        else:
            print(f"  Summary FAILED: {result.get('error', 'unknown')}")

    # ── Summary report ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    for pdf in pdf_files:
        output_name = get_output_name(str(pdf))
        output_dir = pdf.parent / output_name
        json_path = output_dir / f"{output_name}.json"
        jsonl_path = output_dir / f"{output_name}.jsonl"
        summary_path = pdf.parent / (pdf.stem + "_summary.md")

        print(f"\n{pdf.name}:")
        print(f"  JSON:    {json_path} {'✓' if json_path.exists() else '✗'}")
        print(f"  JSONL:   {jsonl_path} {'✓' if jsonl_path.exists() else '✗'}")
        print(f"  Summary: {summary_path} {'✓' if summary_path.exists() else '✗'}")


if __name__ == "__main__":
    main()
