"""Batch summarize papers using silver JSONL content via DeepSeek-chat.

Supports concurrent API calls for faster processing.

Usage:
    cd docmeld
    source venv/bin/activate
    python scripts/summarize.py "/path/to/folder" --workers 10
"""
from __future__ import annotations

import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.utils.env_loader import load_env

logger = logging.getLogger("docmeld")

MAX_CONTENT_CHARS = 200000
DEFAULT_WORKERS = 10

SUMMARIZE_PROMPT = """You are a senior AI researcher skilled at interpreting cutting-edge papers and producing structured English summaries. You have a strong sensitivity to data engineering and will pay close attention to all data-related details in the paper.

Please read the following paper content and output a clearly formatted English summary in Markdown.

Requirements:
1. First line: original paper filename
2. Second line: research institution
3. Third line: English paper title + one-paragraph summary (100-200 words, covering core contribution, method, results)
4. Body organized as follows (adjust flexibly based on actual paper content):
   - 1. Research Background & Existing Problems
   - 2. Core Contributions of Model/Method (list 3-5 key points)
   - 3. Technical System Architecture (expand in subsections; explain the principle and role of each technical component)
   - 4. Data System (★ Key Chapter — be as exhaustive as possible)
     This is one of the most important chapters. Extract as much of the following dimensions from the paper as possible:
     (a) Training Datasets: list all dataset names, sources, scale (samples/duration/size), data type (text/image/audio/video/multimodal), public or private
     (b) Data Collection & Cleaning: how raw data was obtained (crawling/crowdsourcing/synthesis/existing datasets), cleaning and filtering rules (quality filtering, deduplication, length filtering, resolution filtering, etc.), data volume comparison before and after cleaning
     (c) Data Annotation & Labeling: manual vs. automatic annotation, annotation tools/models (e.g. GPT-4, CLIP, Whisper, etc.), annotation content (captions/labels/bounding boxes/segmentation masks, etc.), annotation quality control measures
     (d) Data Pipeline & Preprocessing: complete data processing pipeline flow, feature extraction methods (VAE encoding/mel-spectrogram/tokenization, etc.), data augmentation strategies, sampling strategies (curriculum learning/progressive difficulty/ratio mixing, etc.)
     (e) Data Scale & Ratios: training data volume at each stage, mixing ratios of different data sources, differences between pre-training vs. fine-tuning data
     (f) Evaluation Data: composition of test/validation sets, benchmark names and scales
     If a dimension is not mentioned in the paper, explicitly note "Not mentioned in the paper" — do not skip.
   - 5. Experimental Validation (experimental setup, key results, ablation studies)
   - 6. Application Scenarios
   - 7. Limitations & Future Work
   - 8. Overall Conclusion (one-paragraph summary)

Formatting requirements:
- Use English; retain technical terms in their original language with English explanation
- Use Markdown format; headings use Arabic numerals (1, 2, 3...), subsections use (a), (b)...
- Key numbers, metrics, and model names must be accurately cited
- Data-related numbers must be precise: sample counts, dataset sizes, training duration, batch size, etc. must be cited verbatim from the original text
- Do NOT output ```markdown code block markers; output Markdown content directly

Paper content:
"""


def assemble_paper_content(jsonl_path: Path) -> str:
    """Read silver JSONL and concatenate page_content into full markdown."""
    pages: List[str] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            page = json.loads(line)
            content = page.get("page_content", "")
            if content:
                pages.append(content)
    return "\n\n---\n\n".join(pages)


def _call_summarize_api(client: DeepSeekClient, prompt: str) -> str:
    """Make the API call for summarization."""
    from langchain_deepseek import ChatDeepSeek

    kwargs: Dict = {
        "model": "deepseek-chat",
        "temperature": 1.2,
        "api_key": client.api_key,
    }
    if client.endpoint:
        kwargs["base_url"] = client.endpoint

    llm = ChatDeepSeek(**kwargs)
    response = llm.invoke(prompt)
    text = str(response.content).strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return text


def summarize_one(client: DeepSeekClient, task: Dict) -> Dict:
    """Summarize a single paper. Returns task dict with 'ok' field."""
    jsonl_path = task["jsonl"]
    pdf_name = task["pdf_name"]
    output_path = task["output"]

    if output_path.exists():
        return {**task, "ok": True, "skipped": True}

    full_content = assemble_paper_content(jsonl_path)
    if not full_content:
        return {**task, "ok": False, "error": "empty content"}

    truncated = full_content[:MAX_CONTENT_CHARS]
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


def collect_papers(folder: Path) -> List[Dict]:
    """Scan folder for papers needing summarization."""
    papers = []
    for cat_dir in sorted(folder.iterdir()):
        if not cat_dir.is_dir():
            continue
        # Skip non-category dirs (files, hidden dirs)
        if cat_dir.name.startswith(".") or cat_dir.name.startswith("_"):
            continue

        for subdir in sorted(cat_dir.iterdir()):
            if not subdir.is_dir():
                continue
            jsonl_files = [
                f for f in subdir.glob("*.jsonl")
                if not f.name.endswith("_gold.jsonl")
            ]
            if not jsonl_files:
                continue
            jsonl_path = jsonl_files[0]

            # Match PDF by hash suffix
            hash6 = subdir.name.rsplit("_", 1)[-1] if "_" in subdir.name else ""
            pdfs = list(cat_dir.glob("*.pdf")) + list(cat_dir.glob("*.PDF"))
            matched_pdf = None
            for pdf in pdfs:
                from docmeld.bronze.filename_sanitizer import calculate_hash
                if calculate_hash(str(pdf)) == hash6:
                    matched_pdf = pdf
                    break

            pdf_name = matched_pdf.name if matched_pdf else f"{subdir.name}.pdf"
            md_name = Path(pdf_name).stem + "_summary.md"
            output_path = cat_dir / md_name

            papers.append({
                "jsonl": jsonl_path,
                "pdf_name": pdf_name,
                "output": output_path,
                "category": cat_dir.name,
            })

    return papers


def batch_summarize(folder_path: str, workers: int = DEFAULT_WORKERS) -> None:
    """Summarize all papers with concurrent API calls."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: folder not found: {folder_path}")
        sys.exit(1)

    env = load_env(require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )

    papers = collect_papers(folder)
    total = len(papers)
    pending = [p for p in papers if not p["output"].exists()]
    done = total - len(pending)

    print(f"Found {total} papers, {done} already done, {len(pending)} remaining")
    print(f"Workers: {workers}")

    if not pending:
        print("All papers already summarized.")
        return

    success = 0
    failed = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(summarize_one, client, task): task
            for task in pending
        }

        for future in as_completed(futures):
            result = future.result()
            idx = done + success + failed + 1
            name = result["pdf_name"][:65]

            if result.get("ok"):
                success += 1
                print(f"[{idx}/{total}] ✓ {name}")
            else:
                failed += 1
                err = result.get("error", "unknown")
                print(f"[{idx}/{total}] ✗ {name} — {err}")

    elapsed = time.time() - start
    print(f"\nDone: {success} summarized, {failed} failed, {elapsed:.0f}s")
    print(f"Avg: {elapsed / max(success + failed, 1):.1f}s per paper")


if __name__ == "__main__":
    import argparse

    from docmeld.utils.logging import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Batch summarize papers via DeepSeek")
    parser.add_argument("folder", help="Path to categorized folder")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent API calls (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()

    batch_summarize(args.folder, workers=args.workers)
