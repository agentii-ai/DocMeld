"""Batch summarize business school case studies into Chinese learning notes.

Uses DeepSeek-chat (V3) with a 3-round prompt refinement approach:
  Round 1 → Initial comprehensive summary
  Round 2 → Add teaching narrative, examples, frameworks
  Round 3 → Final polish for clarity and pedagogy

Output: {pdf_name}_bschool_note.md next to each silver output directory.

Usage:
    cd /Users/frank/A/DocMeld/docmeld
    source venv/bin/activate
    python scripts/summarize_bschool.py "/path/to/case-study-folder" --workers 5
"""
from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from docmeld.gold.deepseek_client import DeepSeekClient, call_with_retry
from docmeld.utils.env_loader import load_env

logger = logging.getLogger("docmeld")

DEFAULT_WORKERS = 5
DEEPSEEK_MODEL = "deepseek-v4-flash"  # DeepSeek V4 Flash
ENV_PATH = "/Users/frank/A/DocMeld/.env.local"

# ─── Prompt Design: 3 Rounds of Optimization ─────────────────────────────────
# Round 1: Basic structure — cover background, framework, analysis, conclusion
# Round 2: Add teaching narrative, real-world examples, actionable frameworks
# Round 3: Add comparative thinking, controversy, "so what" synthesis
# The final prompt below is the result of 3 optimization rounds.
# ─────────────────────────────────────────────────────────────────────────────

BSCHOOL_SUMMARIZE_PROMPT = """你是一位斯坦福商学院（Stanford GSB）的资深教学教授，擅长将复杂的商业案例转化为通俗易懂、生动有趣的课堂讲解笔记。你的学生是有2-5年工作经验的中国MBA学员，他们需要理解案例的核心洞察，并能将框架应用到自己的工作中。

请将以下商学院案例文档整理成一份中文学习笔记。你的任务是"讲解"而非"翻译"——用你自己的话把知识讲清楚，让读者读完后能像上完一堂课一样掌握核心内容。

## 第一步：判断文档类型（先分类，再决定输出详略）

仔细阅读文档前500字，判断类型，并据此调整输出：
- **案例研究/教学笔记（10页以上）**：完整输出八章，3000-5000字
- **案例研究短版（3-10页）**：完整输出八章，但每章精简为1-2段，1500-2500字  
- **摘要/大纲/目录（1-2页）**：只输出标题区 + 一段速览 + 一句总结，不超过300字。如果原文信息不足，写"本文档为摘要/简章，内容有限，建议查阅完整版案例"
- **行业报告/实证研究**：强调数据章节，框架章节可简化，2000-3500字
- **纯数据表格**：重点分析数据趋势和关键数字，不编造故事

在标题区第二行明确标注以上类型。

## 输出结构要求

### 标题区
第一行：文档原始文件名
第二行：案例类型（按上述分类标注）
第三行：一句话核心洞察（30字以内，用粗体标注）

### 一、案例速览（3分钟读完）
- 用3-5句话讲清楚：这份材料在讨论什么问题？为什么重要？核心结论是什么？
- 站在CEO/投资者/决策者视角，不要罗列事实，要讲"这对我意味着什么"

### 二、背景与情境还原（Story）
- 还原案例发生的时间、地点、行业背景
- 核心人物/公司是谁？他们面临什么困境或选择？
- 当时的宏观环境如何？（市场情绪、监管、技术变革等）
- 要讲故事，不要列简历

### 三、核心框架与思维模型（Frameworks）
这是最重要的章节。提炼出案例中使用的分析框架或思维模型：
- 每个框架用"名称 → 定义 → 如何使用 → 案例中怎么用的"的格式展开
- 至少提炼2-4个可迁移的框架
- 用表格对比不同框架的适用场景

### 四、关键决策点与权衡（Decisions & Trade-offs）
- 案例中有哪些关键的"分叉路口"？
- 每个决策点的选项A vs 选项B是什么？各自的利弊？
- 最终选择了什么？为什么？如果选另一条路会怎样？

### 五、数据与证据（Evidence）
★ 这是硬约束章节。必须使用以下表格格式，每行一个数据点：

| 数据项 | 具体数值 | 原文出处（哪个exhibit/段落） | 含义解读（一句话） | 数据局限性 |
|--------|---------|---------------------------|-------------------|-----------|
| ... | ... | ... | ... | ... |

- 只引用案例原文中明确出现的数据，**严禁编造任何数字**
- 如果某个维度的数据原文没有，在"含义解读"列写"案例未提供"
- 每个单元格不超过两句话，保持表格整洁
- 表格后附一段"反直觉发现"（如有），不要求必须写

### 六、实战启示（Actionable Takeaways）
遵循"3C"原则——每条建议必须同时满足：
- **C1 - 案例引用**（Case）：引用案例中的具体做法或数据
- **C2 - 语境适配**（Context）：说明这条建议为何适用于当前读者的工作环境
- **C3 - 可执行步骤**（Concrete）：给出"今天下午就能做的第一步"微步骤

列出3-5条建议。**严禁空洞的励志口号**（如"找到北极星""做自己的CEO"），必须紧扣案例细节。

### 七、延伸思考（Going Deeper）
- 这个案例有什么局限性？（时代局限、样本偏差、幸存者偏差等）
- 有哪些相关的理论、书籍、案例可以进一步阅读？
- 提出1-2个值得在课堂上辩论的问题

### 八、一句话总结
用一句有力的中文总结这个案例的核心教训（20字以内）

## 写作风格要求
- **口语化讲解**：像老师在黑板上画图讲解一样，多用"你可以这样理解...""想象一下...""换个角度想..."
- **中国语境化**：适当引用中国市场/企业的类比，帮助中国读者建立联系。但类比必须自然贴切，不可生搬硬套
- **保持严谨**：关键概念保留英文原文并括号标注。数据只引用原文，不编造
- **Markdown格式**：全篇统一使用 `## 一、` `## 二、` 作为章节标题（即二级标题），小节用 `###`。表格、加粗、列表增强可读性
- **不要输出```markdown代码块标记**，直接输出Markdown内容

## 质量红线（必须遵守）

1. **反幻觉铁律**：绝对禁止编造案例原文中没有的人名、数字、事件、引用。如果某个信息缺失，写"案例未提及"而不是猜测填补
2. **全篇语言一致性**：第一节到第八节的语言流畅度必须一致。不允许前三节通畅、后五节语法破碎的情况。写完请自我检查第四节至第八节是否通顺
3. **案例类比克制**：中国市场类比最多使用2处，且只在自然贴切的场景使用。不要把"拼多多""蚂蚁森林""海底捞"塞进每一个案例
4. **篇幅自适应**：严格按照文档类型决定输出长度，不要对1页摘要写5000字

文档内容：
"""


def assemble_page_content(md_path: Path) -> str:
    """Read silver markdown file as full document text."""
    with open(md_path, encoding="utf-8") as f:
        return f.read()


def _call_api(client: DeepSeekClient, prompt: str) -> str:
    """Make the API call for summarization."""
    from langchain_deepseek import ChatDeepSeek

    kwargs: Dict = {
        "model": DEEPSEEK_MODEL,
        "temperature": 1.2,
        "api_key": client.api_key,
    }
    if client.endpoint:
        kwargs["base_url"] = client.endpoint

    llm = ChatDeepSeek(**kwargs)
    response = llm.invoke(prompt)
    text = str(response.content).strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return text


def summarize_one(client: DeepSeekClient, task: Dict) -> Dict:
    """Summarize a single case study. Returns task dict with 'ok' field."""
    md_path = task["md_path"]
    pdf_name = task["pdf_name"]
    output_path = Path(task["output"])

    if output_path.exists():
        return {**task, "ok": True, "skipped": True}

    full_content = assemble_page_content(Path(md_path))
    if not full_content:
        return {**task, "ok": False, "error": "empty content"}

    prompt = BSCHOOL_SUMMARIZE_PROMPT + full_content

    try:
        response = call_with_retry(
            lambda: _call_api(client, prompt),
            max_retries=3,
            base_delay=2.0,
        )

        # Always prepend the PDF filename
        if not response.startswith(pdf_name):
            response = f"{pdf_name}\n\n{response}"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response)
            if not response.endswith("\n"):
                f.write("\n")

        return {**task, "ok": True, "skipped": False}

    except Exception as e:
        return {**task, "ok": False, "error": str(e)}


def collect_cases(folder: Path) -> List[Dict]:
    """Scan folder for silver markdown files needing summarization.

    Silver stage produces .md files next to .jsonl in each hash-named subdir.
    """
    cases = []
    for subdir in sorted(folder.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name.startswith("."):
            continue

        md_files = list(subdir.glob("*.md"))
        if not md_files:
            continue

        md_path = md_files[0]

        # Derive PDF name from the md stem (format: {name}_{hash6})
        stem = md_path.stem
        pdf_name = stem + ".pdf"  # fallback

        # Try to find actual PDF next to the subdir
        parent = subdir.parent
        for pdf in parent.glob("*.pdf"):
            from docmeld.bronze.filename_sanitizer import calculate_hash
            hash6 = stem.rsplit("_", 1)[-1] if "_" in stem else ""
            if len(hash6) == 6 and calculate_hash(str(pdf)) == hash6:
                pdf_name = pdf.name
                break

        output_path = parent / f"{Path(pdf_name).stem}_bschool_note.md"

        cases.append({
            "md_path": str(md_path),
            "pdf_name": pdf_name,
            "output": str(output_path),
        })

    return cases


def batch_summarize(folder_path: str, workers: int = DEFAULT_WORKERS) -> None:
    """Summarize all b-school cases with concurrent API calls."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: folder not found: {folder_path}")
        sys.exit(1)

    env = load_env(str(Path(ENV_PATH)), require_api_key=True)
    client = DeepSeekClient(
        api_key=env["DEEPSEEK_API_KEY"],
        endpoint=env.get("DEEPSEEK_API_ENDPOINT"),
    )

    cases = collect_cases(folder)
    total = len(cases)
    pending = [c for c in cases if not Path(c["output"]).exists()]
    done = total - len(pending)

    print(f"Found {total} cases, {done} already done, {len(pending)} remaining")
    print(f"Model: {DEEPSEEK_MODEL}, Workers: {workers}")
    print("Prompt: 3-round optimized Chinese b-school teaching style")
    print()

    if not pending:
        print("All cases already summarized.")
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
            name = result["pdf_name"][:70]

            if result.get("ok"):
                if result.get("skipped"):
                    print(f"[{idx}/{total}] ⏭ {name} (cached)")
                else:
                    success += 1
                    print(f"[{idx}/{total}] ✓ {name}")
            else:
                failed += 1
                err = result.get("error", "unknown")
                print(f"[{idx}/{total}] ✗ {name} — {err[:80]}")

    elapsed = time.time() - start
    print(f"\nDone: {success} new, {failed} failed, {done} cached, {elapsed:.0f}s")


if __name__ == "__main__":
    import argparse

    from docmeld.utils.logging import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Batch summarize business school cases via DeepSeek"
    )
    parser.add_argument("folder", help="Path to folder with silver outputs")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Concurrent API calls (default: {DEFAULT_WORKERS})"
    )
    args = parser.parse_args()

    batch_summarize(args.folder, workers=args.workers)
