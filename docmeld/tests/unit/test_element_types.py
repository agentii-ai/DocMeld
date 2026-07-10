"""Unit tests for Pydantic element models."""
import pytest
from pydantic import ValidationError


class TestTitleElement:
    def test_valid_title(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        elem = TitleElement(type="title", level=0, content="Executive Summary", page_no=1)
        assert elem.type == "title"
        assert elem.level == 0
        assert elem.content == "Executive Summary"
        assert elem.page_no == 1

    def test_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        elem = TitleElement(type="title", level=0, content="Title", page_no=1)
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_custom_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        elem = TitleElement(
            type="title", level=1, content="Sub", page_no=1,
            element_id="e_002", parent_id="e_001",
        )
        assert elem.element_id == "e_002"
        assert elem.parent_id == "e_001"

    def test_level_range(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        for level in range(6):
            elem = TitleElement(type="title", level=level, content="Title", page_no=1)
            assert elem.level == level

    def test_level_too_high(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        with pytest.raises(ValidationError):
            TitleElement(type="title", level=6, content="Title", page_no=1)

    def test_level_negative(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        with pytest.raises(ValidationError):
            TitleElement(type="title", level=-1, content="Title", page_no=1)

    def test_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        with pytest.raises(ValidationError):
            TitleElement(type="title", level=0, content="", page_no=1)

    def test_page_no_zero_rejected(self) -> None:
        from docmeld.bronze.element_types import TitleElement

        with pytest.raises(ValidationError):
            TitleElement(type="title", level=0, content="Title", page_no=0)


class TestTextElement:
    def test_valid_text(self) -> None:
        from docmeld.bronze.element_types import TextElement

        elem = TextElement(type="text", content="Some paragraph text.", page_no=2)
        assert elem.type == "text"
        assert elem.content == "Some paragraph text."
        assert elem.page_no == 2

    def test_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import TextElement

        elem = TextElement(type="text", content="Hello", page_no=1)
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import TextElement

        with pytest.raises(ValidationError):
            TextElement(type="text", content="", page_no=1)


class TestTableElement:
    def test_valid_table(self) -> None:
        from docmeld.bronze.element_types import TableElement

        elem = TableElement(
            type="table",
            content="| A | B |\n|---|---|\n| 1 | 2 |",
            summary="Items: A, B",
            page_no=3,
        )
        assert elem.type == "table"
        assert elem.summary == "Items: A, B"

    def test_default_table_data_is_none(self) -> None:
        from docmeld.bronze.element_types import TableElement

        elem = TableElement(
            type="table", content="| A |\n|---|\n| 1 |", summary="", page_no=1
        )
        assert elem.table_data is None

    def test_table_data_with_value(self) -> None:
        from docmeld.bronze.element_types import TableElement

        td = {"headers": ["A", "B"], "rows": [["1", "2"]], "num_rows": 1, "num_cols": 2}
        elem = TableElement(
            type="table", content="| A | B |\n|---|---|\n| 1 | 2 |",
            summary="", page_no=1, table_data=td,
        )
        assert elem.table_data == td

    def test_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import TableElement

        elem = TableElement(
            type="table", content="| A |\n|---|\n| 1 |", summary="", page_no=1
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_empty_summary_allowed(self) -> None:
        from docmeld.bronze.element_types import TableElement

        elem = TableElement(
            type="table", content="| A |\n|---|\n| 1 |", summary="", page_no=1
        )
        assert elem.summary == ""

    def test_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import TableElement

        with pytest.raises(ValidationError):
            TableElement(type="table", content="", summary="", page_no=1)


class TestImageElement:
    def test_valid_image(self) -> None:
        from docmeld.bronze.element_types import ImageElement

        elem = ImageElement(
            type="image",
            image_name="page001_image_001.png",
            content="A chart",
            image="aGVsbG8=",
            image_id="page001_image_001",
            bbox=(0.0, 0.0, 100.0, 100.0),
            page_no=1,
        )
        assert elem.type == "image"
        assert elem.image_name == "page001_image_001.png"
        assert elem.bbox == (0.0, 0.0, 100.0, 100.0)

    def test_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import ImageElement

        elem = ImageElement(
            type="image", image_name="img.png", content="", image="aGVsbG8=",
            image_id="img", bbox=(0.0, 0.0, 0.0, 0.0), page_no=1,
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_empty_content_allowed(self) -> None:
        from docmeld.bronze.element_types import ImageElement

        elem = ImageElement(
            type="image",
            image_name="img.png",
            content="",
            image="aGVsbG8=",
            image_id="img",
            bbox=(0.0, 0.0, 0.0, 0.0),
            page_no=1,
        )
        assert elem.content == ""


class TestParseElement:
    def test_parse_title_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "title", "level": 1, "content": "Section", "page_no": 2}
        elem = parse_element(data)
        assert elem.type == "title"

    def test_parse_text_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "text", "content": "Hello", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "text"

    def test_parse_unknown_type_raises(self) -> None:
        from docmeld.bronze.element_types import parse_element

        with pytest.raises(ValueError, match="Unknown element type"):
            parse_element({"type": "unknown", "page_no": 1})


class TestChartElement:
    def test_valid_chart(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        elem = ChartElement(
            type="chart",
            chart_type="bar",
            content="| Q | R |\n|---|---|\n| Q1 | 100 |",
            image="iVBORw0KGgo=",
            image_name="chart_001.png",
            page_no=2,
        )
        assert elem.type == "chart"
        assert elem.chart_type == "bar"
        assert elem.content == "| Q | R |\n|---|---|\n| Q1 | 100 |"
        assert elem.image == "iVBORw0KGgo="

    def test_chart_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        elem = ChartElement(
            type="chart", chart_type="pie", content="| A |\n|---|\n| 1 |",
            image="aGVsbG8=", image_name="chart.png", page_no=1,
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_chart_type_unknown_allowed(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        elem = ChartElement(
            type="chart", chart_type="unknown", content="| A |\n|---|\n| 1 |",
            image="aGVsbG8=", image_name="chart.png", page_no=1,
        )
        assert elem.chart_type == "unknown"

    def test_chart_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        with pytest.raises(ValidationError):
            ChartElement(
                type="chart", chart_type="bar", content="",
                image="aGVsbG8=", image_name="chart.png", page_no=1,
            )

    def test_chart_page_no_zero_rejected(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        with pytest.raises(ValidationError):
            ChartElement(
                type="chart", chart_type="bar", content="| A |\n|---|\n| 1 |",
                image="aGVsbG8=", image_name="chart.png", page_no=0,
            )


class TestFormulaElement:
    def test_valid_formula_mathtype(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        elem = FormulaElement(
            type="formula", content="E = mc^2", formula_type="MathType", page_no=3,
        )
        assert elem.type == "formula"
        assert elem.content == "E = mc^2"
        assert elem.formula_type == "MathType"

    def test_valid_formula_omml(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        elem = FormulaElement(
            type="formula", content="\\frac{a}{b}", formula_type="OMML", page_no=1,
        )
        assert elem.formula_type == "OMML"

    def test_valid_formula_latex(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        elem = FormulaElement(
            type="formula", content="\\sum_{i=1}^{n} x_i", formula_type="LaTeX", page_no=1,
        )
        assert elem.formula_type == "LaTeX"

    def test_formula_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        elem = FormulaElement(
            type="formula", content="x = y", formula_type="LaTeX", page_no=1,
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_formula_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        with pytest.raises(ValidationError):
            FormulaElement(
                type="formula", content="", formula_type="LaTeX", page_no=1,
            )

    def test_formula_page_no_zero_rejected(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        with pytest.raises(ValidationError):
            FormulaElement(
                type="formula", content="x = y", formula_type="LaTeX", page_no=0,
            )


class TestHeaderElement:
    def test_valid_header(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        elem = HeaderElement(
            type="header", content="Chapter 3", page_scope="all", page_no=5,
        )
        assert elem.type == "header"
        assert elem.content == "Chapter 3"
        assert elem.page_scope == "all"

    def test_header_page_scope_even(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        elem = HeaderElement(
            type="header", content="Even header", page_scope="even", page_no=2,
        )
        assert elem.page_scope == "even"

    def test_header_page_scope_odd(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        elem = HeaderElement(
            type="header", content="Odd header", page_scope="odd", page_no=3,
        )
        assert elem.page_scope == "odd"

    def test_header_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        elem = HeaderElement(
            type="header", content="Header", page_scope="all", page_no=1,
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_header_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        with pytest.raises(ValidationError):
            HeaderElement(
                type="header", content="", page_scope="all", page_no=1,
            )


class TestFooterElement:
    def test_valid_footer(self) -> None:
        from docmeld.bronze.element_types import FooterElement

        elem = FooterElement(
            type="footer", content="Page 1", page_scope="all", page_no=1,
        )
        assert elem.type == "footer"
        assert elem.content == "Page 1"

    def test_footer_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import FooterElement

        with pytest.raises(ValidationError):
            FooterElement(
                type="footer", content="", page_scope="all", page_no=1,
            )


class TestFootnoteElement:
    def test_valid_footnote(self) -> None:
        from docmeld.bronze.element_types import FootnoteElement

        elem = FootnoteElement(
            type="footnote", content="Source: Annual Report", reference_id="1", page_no=7,
        )
        assert elem.type == "footnote"
        assert elem.content == "Source: Annual Report"
        assert elem.reference_id == "1"

    def test_footnote_default_element_id_and_parent_id(self) -> None:
        from docmeld.bronze.element_types import FootnoteElement

        elem = FootnoteElement(
            type="footnote", content="Note text", reference_id="*", page_no=1,
        )
        assert elem.element_id == ""
        assert elem.parent_id == ""

    def test_footnote_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import FootnoteElement

        with pytest.raises(ValidationError):
            FootnoteElement(
                type="footnote", content="", reference_id="1", page_no=1,
            )


class TestEndnoteElement:
    def test_valid_endnote(self) -> None:
        from docmeld.bronze.element_types import EndnoteElement

        elem = EndnoteElement(
            type="endnote", content="See Appendix A", reference_id="i", page_no=20,
        )
        assert elem.type == "endnote"
        assert elem.content == "See Appendix A"
        assert elem.reference_id == "i"

    def test_endnote_empty_content_rejected(self) -> None:
        from docmeld.bronze.element_types import EndnoteElement

        with pytest.raises(ValidationError):
            EndnoteElement(
                type="endnote", content="", reference_id="1", page_no=1,
            )


class TestParseElement:
    def test_parse_title_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "title", "level": 1, "content": "Section", "page_no": 2}
        elem = parse_element(data)
        assert elem.type == "title"

    def test_parse_text_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "text", "content": "Hello", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "text"

    def test_parse_chart_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {
            "type": "chart", "chart_type": "bar",
            "content": "| Q | R |\n|---|---|\n| Q1 | 100 |",
            "image": "aGVsbG8=", "image_name": "chart.png", "page_no": 2,
        }
        elem = parse_element(data)
        assert elem.type == "chart"

    def test_parse_formula_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "formula", "content": "E = mc^2", "formula_type": "MathType", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "formula"

    def test_parse_header_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "header", "content": "Header text", "page_scope": "all", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "header"

    def test_parse_footer_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "footer", "content": "Footer text", "page_scope": "all", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "footer"

    def test_parse_footnote_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "footnote", "content": "Note", "reference_id": "1", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "footnote"

    def test_parse_endnote_dict(self) -> None:
        from docmeld.bronze.element_types import parse_element

        data = {"type": "endnote", "content": "Note", "reference_id": "1", "page_no": 1}
        elem = parse_element(data)
        assert elem.type == "endnote"

    def test_parse_unknown_type_raises(self) -> None:
        from docmeld.bronze.element_types import parse_element

        with pytest.raises(ValueError, match="Unknown element type"):
            parse_element({"type": "unknown", "page_no": 1})


class TestSmartArtElement:
    def test_valid_smartart(self) -> None:
        from docmeld.bronze.element_types import SmartArtElement

        elem = SmartArtElement(
            type="smartart", smartart_type="process",
            content="- Plan\n- Build\n- Ship", page_no=3,
        )
        assert elem.type == "smartart"
        assert elem.smartart_type == "process"
        assert elem.hidden is False

    def test_smartart_image_fallback_allows_empty_content(self) -> None:
        from docmeld.bronze.element_types import SmartArtElement

        elem = SmartArtElement(
            type="smartart", smartart_type="cycle", image="base64==", page_no=1
        )
        assert elem.content == ""
        assert elem.image == "base64=="


class TestNotesElement:
    def test_valid_notes(self) -> None:
        from docmeld.bronze.element_types import NotesElement

        elem = NotesElement(type="notes", content="Speaker note here", page_no=2)
        assert elem.type == "notes"
        assert elem.content == "Speaker note here"

    def test_notes_requires_content(self) -> None:
        from docmeld.bronze.element_types import NotesElement

        with pytest.raises(ValidationError):
            NotesElement(type="notes", content="", page_no=1)


class TestGroupElement:
    def test_valid_group(self) -> None:
        from docmeld.bronze.element_types import GroupElement

        elem = GroupElement(
            type="group", content="Group of 3", child_count=3, page_no=4
        )
        assert elem.type == "group"
        assert elem.child_count == 3

    def test_group_child_count_non_negative(self) -> None:
        from docmeld.bronze.element_types import GroupElement

        with pytest.raises(ValidationError):
            GroupElement(type="group", child_count=-1, page_no=1)


class TestCommentElement:
    def test_valid_comment(self) -> None:
        from docmeld.bronze.element_types import CommentElement

        elem = CommentElement(
            type="comment", content="Fix this", author="A. Reviewer", page_no=2
        )
        assert elem.type == "comment"
        assert elem.author == "A. Reviewer"

    def test_comment_author_defaults_empty(self) -> None:
        from docmeld.bronze.element_types import CommentElement

        elem = CommentElement(type="comment", content="No author", page_no=1)
        assert elem.author == ""


class TestHiddenField:
    def test_hidden_defaults_false_all_types(self) -> None:
        from docmeld.bronze.element_types import TextElement, NotesElement

        assert TextElement(type="text", content="x", page_no=1).hidden is False
        assert NotesElement(type="notes", content="x", page_no=1).hidden is False

    def test_hidden_can_be_set(self) -> None:
        from docmeld.bronze.element_types import TextElement

        assert TextElement(type="text", content="x", page_no=1, hidden=True).hidden is True


class TestParseElementNewTypes:
    def test_parse_smartart(self) -> None:
        from docmeld.bronze.element_types import parse_element, SmartArtElement

        elem = parse_element({"type": "smartart", "smartart_type": "list", "content": "a", "page_no": 1})
        assert isinstance(elem, SmartArtElement)

    def test_parse_all_new_types(self) -> None:
        from docmeld.bronze.element_types import parse_element

        for t, extra in [
            ("smartart", {"smartart_type": "process", "content": "x"}),
            ("notes", {"content": "x"}),
            ("group", {"child_count": 2}),
            ("comment", {"content": "x"}),
        ]:
            elem = parse_element({"type": t, "page_no": 1, **extra})
            assert elem.type == t
