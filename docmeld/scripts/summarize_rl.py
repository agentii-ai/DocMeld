"""Batch summarize research papers into structured Chinese Markdown notes.

Walks a folder of already-processed papers (each PDF has a sibling
``<name>_<hash>/`` output dir containing silver ``.jsonl``), assembles the page
content, and writes ``<pdf_stem>_summary.md`` next to each PDF via DeepSeek-chat.

Usage:
    cd /Users/frank/A/DocMeld/docmeld
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

SUMMARIZE_PROMPT = """你是一位资深AI研究员，擅长解读前沿论文并输出结构化中文总结。你对数据工程有极强的敏感度，会格外关注论文中所有与数据相关的细节。

请解读以下论文内容，输出格式清晰的中文总结Markdown文章。

要求：
1. 第一行：论文原始文件名
2. 第二行：研究机构
3. 第三行：论文中文标题 + 一段话概括（100-200字，涵盖核心贡献、方法、结果）
4. 正文按以下结构组织（根据论文实际内容灵活调整）：
   - 一、研究背景与现存问题
   - 二、模型/方法核心贡献（列出3-5个要点）
   - 三、核心技术体系（分小节详细展开，每个技术点说清楚原理和作用）
   - 四、数据体系（★ 重点章节，务必详尽）
   - 五、实验验证（实验设置、核心结果、消融实验）
   - 六、应用场景
   - 七、局限性与未来工作
   - 八、整体结论（一段话总结）

格式要求：
- 使用中文，技术术语保留英文原文并用括号标注
- 用Markdown格式，标题用中文数字（一、二、三...），小节用（一）（二）...
- 关键数字、指标、模型名称要准确引用
- 不要输出```markdown代码块标记，直接输出Markdown内容

论文内容：
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
