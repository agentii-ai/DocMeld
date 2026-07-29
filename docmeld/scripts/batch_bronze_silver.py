"""Batch process PDFs through bronze → silver stages (no LLM/gold).

Produces bronze JSON, silver JSONL, and silver markdown files
for all found PDFs in the given directories.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Add docmeld to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docmeld.bronze.processor import BronzeProcessor
from docmeld.silver.processor import SilverProcessor


def find_pdfs(root_dirs: list[str]) -> list[Path]:
    """Recursively find all .pdf files (excluding hidden files)."""
    pdfs = []
    for root_dir in root_dirs:
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in sorted(filenames):
                if fn.lower().endswith(".pdf") and not fn.startswith("."):
                    pdfs.append(Path(dirpath) / fn)
    return pdfs


def jsonl_to_markdown(jsonl_path: Path) -> Path:
    """Convert a silver JSONL file to a single markdown file next to it."""
    md_path = jsonl_path.with_suffix(".md")
    if md_path.exists():
        return md_path

    with open(jsonl_path, encoding="utf-8") as f:
        pages_data = [json.loads(line) for line in f if line.strip()]

    parts = []
    source = pages_data[0]["metadata"]["source"] if pages_data else "unknown"
    parts.append(f"# {source}\n")

    for page_data in pages_data:
        meta = page_data["metadata"]
        parts.append(f"## {meta['page_no']}")
        if meta.get("session_title"):
            parts.append(f"_Context: {meta['session_title']}_")
        parts.append("")
        parts.append(page_data["page_content"])
        parts.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    return md_path


def main():
    root_dirs = sys.argv[1:] if len(sys.argv) > 1 else []
    if not root_dirs:
        print("Usage: python scripts/batch_bronze_silver.py /path/to/pdf/dir1 [/path/to/dir2 ...]")
        sys.exit(1)

    print("Scanning directories...")
    all_pdfs = find_pdfs(root_dirs)
    print(f"Found {len(all_pdfs)} PDFs\n")

    bronze = BronzeProcessor()
    silver_proc = SilverProcessor()

    stats = {"bronze_ok": 0, "bronze_skip": 0, "bronze_fail": 0,
             "silver_ok": 0, "silver_skip": 0, "silver_fail": 0,
             "md_ok": 0, "md_skip": 0}
    failures = []

    t0 = time.time()
    for i, pdf_path in enumerate(all_pdfs, 1):
        name = pdf_path.name
        print(f"[{i}/{len(all_pdfs)}] {name[:80]}", end=" ", flush=True)

        # Bronze
        try:
            bresult = bronze.process_file(str(pdf_path))
            if bresult.skipped:
                stats["bronze_skip"] += 1
                print("bronze=(skip)", end=" ", flush=True)
            else:
                stats["bronze_ok"] += 1
                print(f"bronze=({bresult.page_count}p)", end=" ", flush=True)
        except Exception as e:
            stats["bronze_fail"] += 1
            failures.append((str(pdf_path), f"bronze: {e}"))
            print(f"BRONZE FAIL: {str(e)[:60]}", flush=True)
            continue

        # Silver
        try:
            sresult = silver_proc.process(bresult.output_path)
            if sresult.skipped:
                stats["silver_skip"] += 1
                print("silver=(skip)", end=" ", flush=True)
            else:
                stats["silver_ok"] += 1
                print(f"silver=({sresult.page_count}p)", end=" ", flush=True)
        except Exception as e:
            stats["silver_fail"] += 1
            failures.append((str(pdf_path), f"silver: {e}"))
            print(f"SILVER FAIL: {str(e)[:60]}", flush=True)
            continue

        # Markdown
        try:
            md_path = jsonl_to_markdown(Path(sresult.output_path))
            if md_path.stat().st_mtime > t0:
                stats["md_ok"] += 1
                print("md=(new)", flush=True)
            else:
                stats["md_skip"] += 1
                print("md=(skip)", flush=True)
        except Exception as e:
            print(f"MD FAIL: {str(e)[:60]}", flush=True)

    elapsed = time.time() - t0

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY — {elapsed:.1f}s elapsed")
    print(f"  Bronze: {stats['bronze_ok']} new, {stats['bronze_skip']} skipped, {stats['bronze_fail']} failed")
    print(f"  Silver: {stats['silver_ok']} new, {stats['silver_skip']} skipped, {stats['silver_fail']} failed")
    print(f"  MD:     {stats['md_ok']} new, {stats['md_skip']} skipped")
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for path, err in failures[:30]:
            print(f"    {Path(path).name}: {err}")
        if len(failures) > 30:
            print(f"    ... and {len(failures) - 30} more")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
