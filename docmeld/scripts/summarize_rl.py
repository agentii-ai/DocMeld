"""Batch summarize research papers into structured Chinese Markdown notes.

Walks a folder of already-processed papers (each PDF has a sibling
``<name>_<hash>/`` output dir containing silver ``.jsonl``), assembles the page
content, and writes ``<pdf_stem>_summary.md`` next to each PDF via DeepSeek-chat.

Usage:
    cd docmeld
    source venv/bin/activate
    python scripts/summarize_rl.py "/path/to/papers" --workers 5
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from langchain_deepseek import ChatDeepSeek

from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.utils.env_loader import load_env

MAX_CONTENT_CHARS = 200000
DEFAULT_WORKERS = 5

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
   - 5. Experimental Validation (experimental setup, key results, ablation studies)
   - 6. Application Scenarios
   - 7. Limitations & Future Work
   - 8. Overall Conclusion (one-paragraph summary)

Formatting requirements:
- Use English; retain technical terms in their original language with English explanation
- Use Markdown format; headings use Arabic numerals (1, 2, 3...), subsections use (a), (b)...
- Key numbers, metrics, and model names must be accurately cited
- Do NOT output ```markdown code block markers; output Markdown content directly

Paper content:
"""

def assemble_content(jsonl_path: Path) -> str:
    pages = []
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


def call_api(client: DeepSeekClient, prompt: str) -> str:
    kwargs: dict = {"model": "deepseek-chat", "temperature": 1.2, "api_key": client.api_key}
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


def summarize_one(client: DeepSeekClient, pdf_path: Path, jsonl_path: Path) -> tuple:
    output_path = pdf_path.parent / (pdf_path.stem + "_summary.md")
    if output_path.exists():
        return pdf_path.name, True, "skipped"

    content = assemble_content(jsonl_path)
    if not content:
        return pdf_path.name, False, "empty content"

    prompt = SUMMARIZE_PROMPT + content[:MAX_CONTENT_CHARS]
    try:
        response = call_with_retry(lambda: call_api(client, prompt), max_retries=3, base_delay=2.0)
        if not response.startswith(pdf_path.name):
            response = f"{pdf_path.name}\n\n{response}"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response)
            if not response.endswith("\n"):
                f.write("\n")
        return pdf_path.name, True, str(output_path)
    except Exception as e:
        return pdf_path.name, False, str(e)


def build_tasks(base: Path) -> list[tuple[Path, Path]]:
    from docmeld.bronze.filename_sanitizer import calculate_hash
    tasks = []
    for jsonl in sorted(base.rglob("*.jsonl")):
        if "_gold" in jsonl.name:
            continue
        subdir = jsonl.parent
        hash6 = subdir.name.rsplit("_", 1)[-1]
        parent = subdir.parent
        matched = None
        for pdf in parent.glob("*.pdf"):
            if calculate_hash(str(pdf)) == hash6:
                matched = pdf
                break
        if matched:
            tasks.append((matched, jsonl))
        else:
            print(f"  [warn] no PDF matched for {jsonl.name}", flush=True)
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="Path to the folder of processed papers")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers (default: {DEFAULT_WORKERS})",
    )
    args = parser.parse_args()

    base = Path(args.folder)
    if not base.is_dir():
        parser.error(f"folder not found: {base}")

    env = load_env(require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )

    tasks = build_tasks(base)
    print(f"Summarizing {len(tasks)} papers with {args.workers} workers...", flush=True)
    start = time.time()
    success = failed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(summarize_one, client, pdf, jsonl): pdf for pdf, jsonl in tasks}
        for future in as_completed(futures):
            name, ok, info = future.result()
            if ok:
                success += 1
                status = "skipped" if info == "skipped" else "✓"
                print(f"{status} {Path(name).name[:75]}", flush=True)
            else:
                failed += 1
                print(f"✗ {Path(name).name[:75]} — {info}", flush=True)

    elapsed = time.time() - start
    print(f"\nDone: {success} ok, {failed} failed, {elapsed:.0f}s", flush=True)


if __name__ == "__main__":
    main()
