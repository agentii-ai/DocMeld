"""Batch summarize business school case studies into Chinese learning notes.

Uses DeepSeek-chat (V3) with a 3-round prompt refinement approach:
  Round 1 → Initial comprehensive summary
  Round 2 → Add teaching narrative, examples, frameworks
  Round 3 → Final polish for clarity and pedagogy

Output: {pdf_name}_bschool_note.md next to each silver output directory.

Usage:
    cd docmeld
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
ENV_PATH = str(Path(__file__).resolve().parents[2] / ".env.local")

# ─── Prompt Design: 3 Rounds of Optimization ─────────────────────────────────
# Round 1: Basic structure — cover background, framework, analysis, conclusion
# Round 2: Add teaching narrative, real-world examples, actionable frameworks
# Round 3: Add comparative thinking, controversy, "so what" synthesis
# The final prompt below is the result of 3 optimization rounds.
# ─────────────────────────────────────────────────────────────────────────────

BSCHOOL_SUMMARIZE_PROMPT = """You are a senior teaching professor at Stanford Graduate School of Business (GSB), skilled at transforming complex business cases into clear, engaging lecture notes. Your students are MBA candidates with 2-5 years of work experience who need to understand the core insights of a case and apply its frameworks to their own work.

Please organize the following business school case document into a structured English learning note. Your task is to "teach" not "translate" — explain the knowledge in your own words so the reader walks away feeling like they just attended a great class.

## Step 1: Determine Document Type (classify first, then decide output detail)

Read the first 500 words of the document carefully, determine its type, and adjust output accordingly:
- **Case Study / Teaching Note (10+ pages)**: Full eight-chapter output, 3000-5000 words
- **Case Study Short Form (3-10 pages)**: Full eight-chapter output, but each chapter condensed to 1-2 paragraphs, 1500-2500 words
- **Abstract / Outline / Table of Contents (1-2 pages)**: Output title block + one overview paragraph + one summary sentence only, no more than 300 words. If source information is insufficient, write "This document is a summary/brief; content is limited. Consult the full case for details."
- **Industry Report / Empirical Study**: Emphasize the data chapter; framework chapters may be simplified, 2000-3500 words
- **Pure Data Tables**: Focus on analyzing data trends and key numbers; do not fabricate narratives

Explicitly label the document type on the second line of the title block.

## Output Structure

### Title Block
First line: Original document filename
Second line: Case type (labeled per classification above)
Third line: One-sentence core insight (max 20 words, in bold)

### 1. Case at a Glance (3-minute read)
- In 3-5 sentences: What problem does this material discuss? Why is it important? What is the core conclusion?
- Adopt the perspective of a CEO/investor/decision-maker. Don't list facts — explain "what this means for me."

### 2. Background & Context (Story)
- Reconstruct the time, place, and industry context of the case
- Who are the key people/companies? What dilemma or choice do they face?
- What was the macro environment? (market sentiment, regulation, technological change, etc.)
- Tell a story, not a resume

### 3. Core Frameworks & Mental Models (Frameworks)
This is the most important chapter. Extract the analytical frameworks or mental models used in the case:
- Expand each framework using the format: "Name → Definition → How to Use → How It Was Used in the Case"
- Extract at least 2-4 transferable frameworks
- Use a table to compare the applicable scenarios of different frameworks

### 4. Key Decision Points & Trade-offs (Decisions & Trade-offs)
- What were the critical "fork in the road" moments in the case?
- For each decision point, what were Option A vs. Option B? Pros and cons of each?
- What was ultimately chosen? Why? What would have happened if the other path was taken?

### 5. Data & Evidence (Evidence)
★ This chapter has hard constraints. Must use the following table format, one data point per row:

| Data Item | Specific Value | Source (which exhibit/paragraph) | Interpretation (one sentence) | Data Limitations |
|-----------|---------------|----------------------------------|------------------------------|-----------------|
| ... | ... | ... | ... | ... |

- Only cite data explicitly present in the case text. **Fabricating numbers is strictly prohibited.**
- If data for a given dimension is absent from the source, write "Not provided in the case" in the Interpretation column
- Each cell should be at most two sentences; keep the table clean
- Append a "Counter-Intuitive Findings" paragraph after the table if applicable (optional)

### 6. Actionable Takeaways
Follow the "3C" principle — each recommendation must satisfy all three:
- **C1 - Case Reference**: Cite a specific practice or data point from the case
- **C2 - Context Adaptation**: Explain why this recommendation applies to the reader's work environment
- **C3 - Concrete Step**: Provide a micro-step that "can be done this afternoon"

List 3-5 recommendations. **Empty motivational slogans are strictly prohibited** (e.g. "find your north star," "be your own CEO"). Anchor every recommendation tightly to case details.

### 7. Going Deeper
- What are the limitations of this case? (era limitations, sample bias, survivorship bias, etc.)
- What related theories, books, or cases would be worth further reading?
- Pose 1-2 questions worth debating in a classroom setting

### 8. One-Sentence Summary
Summarize the core lesson of this case in one powerful sentence (max 20 words)

## Writing Style Requirements
- **Conversational teaching tone**: Write as if you're drawing diagrams on a whiteboard. Use phrases like "Think of it this way..." "Imagine that..." "From another angle..."
- **Industry contextualization**: Where appropriate, draw analogies to well-known companies or market trends to help readers connect, but analogies must be natural and relevant, not forced
- **Maintain rigor**: Retain key concepts in their original language with English explanation. Only cite data from the source; do not fabricate
- **Markdown format**: Use `## 1.` `## 2.` as chapter headings (H2 level), subsections with `###`. Tables, bold, and lists to enhance readability
- **Do NOT output ```markdown code block markers**; output Markdown content directly

## Quality Guardrails (must comply)

1. **Anti-Hallucination Iron Rule**: Absolutely forbidden to fabricate names, numbers, events, or citations not present in the case text. If information is missing, write "Not mentioned in the case" rather than guessing
2. **Consistent Quality Throughout**: Fluency from Chapter 1 through Chapter 8 must be consistent. It is unacceptable for the first three chapters to be polished while the last five have broken grammar. Self-check chapters 4-8 for fluency after writing
3. **Analogy Restraint**: Use at most 2 industry analogies, and only where they naturally fit. Do not force-feed the same company references into every case
4. **Length Self-Adaptation**: Strictly follow document type to determine output length. Do not write 5000 words for a 1-page abstract

Document content:
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
