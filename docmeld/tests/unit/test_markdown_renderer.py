"""Unit tests for markdown renderer (10 element types)."""
from __future__ import annotations


class TestRenderPage:
    def test_title_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [{"type": "title", "level": 0, "content": "Main", "page_no": 1}]
        tracker = TitleTracker()
        counters = new_counters()
        content, counters = render_page(elements, tracker, counters)
        assert "# Main" in content

    def test_title_level_mapping(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [
            {"type": "title", "level": 0, "content": "H1", "page_no": 1},
            {"type": "title", "level": 1, "content": "H2", "page_no": 1},
            {"type": "title", "level": 2, "content": "H3", "page_no": 1},
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, _ = render_page(elements, tracker, counters)
        assert "# H1" in content
        assert "## H2" in content
        assert "### H3" in content

    def test_text_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [{"type": "text", "content": "Hello world.", "page_no": 1}]
        tracker = TitleTracker()
        counters = new_counters()
        content, _ = render_page(elements, tracker, counters)
        assert "Hello world." in content

    def test_table_markers_with_global_numbering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        table_content = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        elements = [
            {"type": "table", "content": table_content, "summary": "Items: A", "page_no": 1}
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, counters = render_page(elements, tracker, counters)
        assert "[[Table1]]" in content
        assert "[/Table1]" in content
        assert counters["table"] == 1

    def test_global_numbering_across_pages(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        table = "| X |\n|---|\n| 1 |\n| 2 |"
        elements1 = [{"type": "table", "content": table, "summary": "", "page_no": 1}]
        elements2 = [{"type": "table", "content": table, "summary": "", "page_no": 2}]

        tracker = TitleTracker()
        counters = new_counters()
        _, counters = render_page(elements1, tracker, counters)
        assert counters["table"] == 1

        content2, counters2 = render_page(elements2, tracker, counters)
        assert "[[Table2]]" in content2
        assert counters2["table"] == 2

    def test_small_table_no_number(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        small_table = "| A |\n|---|\n| 1 |"
        elements = [
            {"type": "table", "content": small_table, "summary": "", "page_no": 1}
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, counters = render_page(elements, tracker, counters)
        assert "[[Table]]" in content
        assert counters["table"] == 0

    def test_chart_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        chart_content = "| Q | R |\n|---|---|\n| Q1 | 100 |"
        elements = [
            {"type": "chart", "chart_type": "bar", "content": chart_content,
             "image": "aGVsbG8=", "image_name": "c.png", "page_no": 2}
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, counters = render_page(elements, tracker, counters)
        assert "[[Chart1" in content
        assert "[/Chart1]" in content
        assert counters["chart"] == 1

    def test_formula_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [
            {"type": "formula", "content": "E = mc^2", "formula_type": "MathType", "page_no": 1}
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, counters = render_page(elements, tracker, counters)
        assert "[[Formula1" in content
        assert "[/Formula1]" in content
        assert "E = mc^2" in content
        assert counters["formula"] == 1

    def test_header_footer_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [
            {"type": "header", "content": "Chapter 1", "page_scope": "all", "page_no": 1},
            {"type": "footer", "content": "Page 1", "page_scope": "all", "page_no": 1},
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, _ = render_page(elements, tracker, counters)
        assert "[Header" in content
        assert "[Footer" in content
        assert "Chapter 1" in content

    def test_footnote_rendering(self) -> None:
        from docmeld.silver.markdown_renderer import new_counters, render_page
        from docmeld.silver.title_tracker import TitleTracker

        elements = [
            {"type": "footnote", "content": "Source text", "reference_id": "1", "page_no": 1}
        ]
        tracker = TitleTracker()
        counters = new_counters()
        content, _ = render_page(elements, tracker, counters)
        assert "[^1]" in content
        assert "Source text" in content
