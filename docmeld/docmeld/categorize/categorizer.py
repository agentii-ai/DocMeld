"""Categorize papers into topic clusters via DeepSeek API."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from docmeld.categorize.models import PaperMetadata

logger = logging.getLogger("docmeld")

# Max papers per API call for descriptions
DESC_BATCH_SIZE = 30


def categorize_papers(
    papers: List[PaperMetadata], client: Any
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Send aggregated paper content to DeepSeek for topic clustering.

    Two-phase approach:
    1. Single API call with just filenames for consistent category assignments
    2. Batched API calls for per-paper descriptions

    Args:
        papers: List of PaperMetadata from the aggregator.
        client: DeepSeekClient instance with categorize_papers() method.

    Returns:
        Tuple of (categories, paper_descriptions).
    """
    if not papers:
        return [], []

    sorted_papers = sorted(papers, key=lambda p: p.filename)

    # Phase 1: Categorize ALL papers in one call using filenames + short excerpts
    # Response is compact (just category names + filename lists), so it won't truncate
    logger.info(f"Phase 1: Categorizing {len(sorted_papers)} papers via API...")
    cat_prompt = _build_categorization_prompt(sorted_papers)
    cat_response = client.categorize_papers(cat_prompt)
    categories = _parse_categories_only(cat_response)
    logger.info(f"Identified {len(categories)} categories")

    # Phase 2: Get per-paper descriptions in batches
    all_descs: List[Dict[str, Any]] = []
    total_batches = (len(sorted_papers) + DESC_BATCH_SIZE - 1) // DESC_BATCH_SIZE
    for i in range(0, len(sorted_papers), DESC_BATCH_SIZE):
        batch = sorted_papers[i : i + DESC_BATCH_SIZE]
        batch_num = i // DESC_BATCH_SIZE + 1
        logger.info(
            f"Phase 2: Descriptions batch {batch_num}/{total_batches} "
            f"({len(batch)} papers)..."
        )
        desc_prompt = _build_description_prompt(batch)
        desc_response = client.categorize_papers(desc_prompt)
        batch_descs = _parse_descriptions_only(desc_response)
        all_descs.extend(batch_descs)

    logger.info(f"Categorized {len(sorted_papers)} papers into {len(categories)} categories")
    return categories, all_descs


def _build_categorization_prompt(papers: List[PaperMetadata]) -> str:
    """Build a compact prompt for categorization using filenames + short excerpts.

    Keeps output small by only requesting category assignments (no descriptions).
    """
    sorted_papers = sorted(papers, key=lambda p: p.filename)

    paper_sections = []
    for p in sorted_papers:
        content_preview = p.content[:500] if p.content else "(no content)"
        paper_sections.append(f"=== {p.filename} ===\n{content_preview}\n")

    papers_text = "\n".join(paper_sections)

    return (
        "You are a research paper categorization assistant. "
        "Given the following research papers, group them into topic categories "
        "with hierarchical prefixes.\n\n"
        "Rules:\n"
        "- Each paper must be assigned to exactly one category\n"
        "- Determine the number of categories automatically based on content similarity\n"
        "- Category names MUST have a hierarchical prefix in the format 'x_y Category Name'\n"
        "  where x is the cluster number (1, 2, 3...) and y is the subcategory within that cluster\n"
        "- ORDERING IS CRITICAL — categories must progress from general to specific:\n"
        "  * 0_0 Uncategorized — for papers that do not fit any topic cluster\n"
        "  * 1_x — Surveys, reviews, and broad overviews of the field\n"
        "  * 2_x — Foundational concepts, benchmarks, and datasets\n"
        "  * 3_x onwards — Progressively more focused and specialized subtopics\n"
        "- Examples:\n"
        "  * '0_0 Uncategorized'\n"
        "  * '1_1 Surveys and General Reviews'\n"
        "  * '1_2 Foundational Concepts and Benchmarks'\n"
        "  * '2_1 Monocular Depth Estimation'\n"
        "  * '2_2 Stereo and Multi-View Depth'\n"
        "  * '3_1 3D Reconstruction'\n"
        "  * '4_1 Video Generation and Diffusion Models'\n"
        "- Group related subtopics under the same cluster number (same x value)\n"
        "- Include 3-5 representative keywords per category\n"
        "- Aim for 5-15 papers per category. Split large groups, merge tiny ones.\n\n"
        "IMPORTANT: Return ONLY the categories with paper assignments. "
        "Do NOT include paper_descriptions (they will be requested separately).\n\n"
        "Return ONLY valid JSON:\n"
        '{"categories": [{"name": "x_y Category Name", '
        '"papers": ["filename1.jsonl", "filename2.jsonl"], '
        '"keywords": ["kw1", "kw2", "kw3"]}]}\n\n'
        f"Papers ({len(sorted_papers)} total):\n{papers_text}"
    )


def _build_description_prompt(papers: List[PaperMetadata]) -> str:
    """Build a prompt for getting per-paper descriptions only."""
    sorted_papers = sorted(papers, key=lambda p: p.filename)

    paper_sections = []
    for p in sorted_papers:
        content_preview = p.content[:1000] if p.content else "(no content)"
        paper_sections.append(f"=== {p.filename} ===\n{content_preview}\n")

    papers_text = "\n".join(paper_sections)

    return (
        "For each research paper below, provide a one-line description and 3-5 keywords.\n\n"
        "Return ONLY valid JSON with this structure:\n"
        '{"paper_descriptions": [{"filename": "filename1.jsonl", '
        '"description": "one-line summary", "keywords": ["kw1", "kw2"]}]}\n\n'
        f"Papers:\n{papers_text}"
    )


def _parse_categories_only(response_text: str) -> List[Dict[str, Any]]:
    """Parse the API response for category assignments only.

    Attempts to repair truncated JSON if the response was cut off.
    """
    text = _strip_code_fences(response_text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("JSON truncated, attempting repair...")
        data = _repair_truncated_json(text)
        if data is None:
            raise ValueError("Failed to parse or repair categorization response")

    if "categories" not in data:
        raise ValueError("Missing 'categories' key in categorization response")

    return data["categories"]


def _parse_descriptions_only(response_text: str) -> List[Dict[str, Any]]:
    """Parse the API response for paper descriptions only."""
    text = _strip_code_fences(response_text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse description response: {e}") from e

    return data.get("paper_descriptions", [])


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from API response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _repair_truncated_json(text: str) -> Dict[str, Any] | None:
    """Attempt to repair truncated JSON from a cut-off API response.

    Strategy: find the last complete category object and close the JSON structure.
    """
    # Find the last complete category entry by looking for the last "},"
    # or "}" that closes a category object within the categories array
    last_complete = text.rfind("],")
    if last_complete == -1:
        last_complete = text.rfind("]}")
    if last_complete == -1:
        # Try to find last complete object ending with }
        last_complete = text.rfind("}")

    if last_complete == -1:
        return None

    # Try progressively shorter substrings to find valid JSON
    for end_pos in [last_complete + 1, last_complete + 2]:
        truncated = text[:end_pos]
        # Count open brackets to determine what closers we need
        open_brackets = truncated.count("[") - truncated.count("]")
        open_braces = truncated.count("{") - truncated.count("}")
        suffix = "]" * open_brackets + "}" * open_braces
        try:
            data = json.loads(truncated + suffix)
            if "categories" in data:
                logger.info(f"Repaired truncated JSON ({len(data['categories'])} categories recovered)")
                return data
        except json.JSONDecodeError:
            continue

    return None


def _merge_categories(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge categories with the same name from different batches."""
    merged: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        name = cat.get("name", "Uncategorized")
        if name in merged:
            merged[name]["papers"].extend(cat.get("papers", []))
            existing_kws = set(k.lower() for k in merged[name]["keywords"])
            for kw in cat.get("keywords", []):
                if kw.lower() not in existing_kws:
                    merged[name]["keywords"].append(kw)
                    existing_kws.add(kw.lower())
        else:
            merged[name] = {
                "name": name,
                "papers": list(cat.get("papers", [])),
                "keywords": list(cat.get("keywords", [])),
            }
    return list(merged.values())


# Keep backward-compatible parse function for tests
def _parse_categorization_response(
    response_text: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse the API response into category assignments and paper descriptions."""
    text = _strip_code_fences(response_text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse categorization response: {e}") from e

    if "categories" not in data:
        raise ValueError("Missing 'categories' key in categorization response")

    categories = data["categories"]
    paper_descs = data.get("paper_descriptions", [])
    return categories, paper_descs
