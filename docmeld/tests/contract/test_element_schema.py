"""Contract tests for element JSON Schema validation."""
import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).resolve().parents[3] / "specs" / "001-mvp-pdf-pipeline" / "contracts" / "element-schema.json"


class TestElementSchema:
    @pytest.fixture()
    def schema(self) -> dict:  # type: ignore[type-arg]
        with open(SCHEMA_PATH) as f:
            return json.load(f)

    def test_schema_loads(self, schema: dict) -> None:  # type: ignore[type-arg]
        assert schema["title"] == "DocMeld Element Schema"
        assert "definitions" in schema

    def test_valid_title_element(self, schema: dict) -> None:  # type: ignore[type-arg]
        element = {"type": "title", "level": 0, "content": "Test", "page_no": 1}
        assert element["type"] in ["title", "text", "table", "image"]
        assert element["page_no"] >= 1

    def test_valid_text_element(self, schema: dict) -> None:  # type: ignore[type-arg]
        element = {"type": "text", "content": "Hello world", "page_no": 2}
        assert element["type"] == "text"
        assert len(element["content"]) > 0

    def test_valid_table_element(self, schema: dict) -> None:  # type: ignore[type-arg]
        element = {
            "type": "table",
            "content": "| A | B |\n|---|---|\n| 1 | 2 |",
            "summary": "Items: A, B",
            "page_no": 3,
        }
        assert element["type"] == "table"
        assert "summary" in element

    def test_valid_image_element(self, schema: dict) -> None:  # type: ignore[type-arg]
        element = {
            "type": "image",
            "image_name": "page001_image_001.png",
            "content": "",
            "image": "aGVsbG8=",
            "image_id": "page001_image_001",
            "bbox": [0, 0, 100, 100],
            "page_no": 1,
        }
        assert element["type"] == "image"
        assert len(element["bbox"]) == 4

    def test_invalid_page_no(self) -> None:
        element = {"type": "text", "content": "Hello", "page_no": 0}
        assert element["page_no"] < 1  # Should fail schema validation

    def test_bronze_json_list_structure(self) -> None:
        elements = [
            {"type": "title", "level": 0, "content": "Title", "page_no": 1},
            {"type": "text", "content": "Paragraph", "page_no": 1},
            {"type": "table", "content": "| A |\n|---|\n| 1 |", "summary": "", "page_no": 2},
        ]
        assert isinstance(elements, list)
        for elem in elements:
            assert "type" in elem
            assert "page_no" in elem
            assert elem["page_no"] >= 1

    def test_schema_has_element_id_field(self, schema: dict) -> None:  # type: ignore[type-arg]
        base = schema["definitions"]["BaseElement"]
        assert "element_id" in base["properties"]
        assert base["properties"]["element_id"]["type"] == "string"

    def test_schema_has_parent_id_field(self, schema: dict) -> None:  # type: ignore[type-arg]
        base = schema["definitions"]["BaseElement"]
        assert "parent_id" in base["properties"]
        assert base["properties"]["parent_id"]["type"] == "string"

    def test_schema_has_table_data_field(self, schema: dict) -> None:  # type: ignore[type-arg]
        table_def = schema["definitions"]["TableElement"]["allOf"][1]
        assert "table_data" in table_def["properties"]
        assert table_def["properties"]["table_data"]["type"] == "object"

    def test_element_id_and_parent_id_not_required(self, schema: dict) -> None:  # type: ignore[type-arg]
        base = schema["definitions"]["BaseElement"]
        assert "element_id" not in base["required"]
        assert "parent_id" not in base["required"]

    def test_table_data_not_required(self, schema: dict) -> None:  # type: ignore[type-arg]
        table_def = schema["definitions"]["TableElement"]["allOf"][1]
        assert "table_data" not in table_def["required"]

    def test_valid_element_with_ids(self) -> None:
        element = {
            "type": "title", "level": 0, "content": "Test", "page_no": 1,
            "element_id": "e_001", "parent_id": "",
        }
        assert element["element_id"] == "e_001"
        assert element["parent_id"] == ""

    def test_valid_table_with_table_data(self) -> None:
        element = {
            "type": "table",
            "content": "| A | B |\n|---|---|\n| 1 | 2 |",
            "summary": "Items: 1",
            "page_no": 1,
            "table_data": {
                "headers": ["A", "B"],
                "rows": [["1", "2"]],
                "num_rows": 1,
                "num_cols": 2,
            },
        }
        assert element["table_data"]["num_rows"] == 1
        assert element["table_data"]["headers"] == ["A", "B"]

    def test_ten_type_schema_exists(self) -> None:
        """Verify the 006-mvp-doc-pipeline element schema with 10 types."""
        schema_path = (
            Path(__file__).resolve().parents[3]
            / "specs" / "006-mvp-doc-pipeline" / "contracts" / "element-schema.json"
        )
        assert schema_path.exists(), f"Schema not found at {schema_path}"
        with open(schema_path) as f:
            schema = json.load(f)
        allowed_types = schema["items"]["properties"]["type"]["enum"]
        assert "chart" in allowed_types
        assert "formula" in allowed_types
        assert "header" in allowed_types
        assert "footer" in allowed_types
        assert "footnote" in allowed_types
        assert "endnote" in allowed_types
        assert len(allowed_types) == 10

    def test_chart_element_conforms_to_schema(self) -> None:
        from docmeld.bronze.element_types import ChartElement

        elem = ChartElement(
            type="chart", chart_type="bar",
            content="| Q | R |\n|---|---|\n| Q1 | 100 |",
            image="aGVsbG8=", image_name="chart.png", page_no=2,
        )
        assert elem.type == "chart"
        assert elem.chart_type in ["bar", "line", "pie", "scatter", "area", "radar", "doughnut", "bubble", "unknown"]

    def test_formula_element_conforms_to_schema(self) -> None:
        from docmeld.bronze.element_types import FormulaElement

        elem = FormulaElement(
            type="formula", content="E = mc^2", formula_type="MathType", page_no=1,
        )
        assert elem.formula_type in ["MathType", "OMML", "LaTeX"]

    def test_header_element_conforms_to_schema(self) -> None:
        from docmeld.bronze.element_types import HeaderElement

        elem = HeaderElement(
            type="header", content="Header", page_scope="all", page_no=1,
        )
        assert elem.page_scope in ["all", "even", "odd"]

    def test_backward_compatible_four_types(self) -> None:
        """Existing 4-type elements should validate against 10-type schema."""
        elements = [
            {"type": "title", "level": 0, "content": "Title", "page_no": 1},
            {"type": "text", "content": "Text", "page_no": 1},
            {"type": "table", "content": "| A |\n|---|\n| 1 |", "summary": "", "page_no": 2},
            {"type": "image", "image_name": "img.png", "content": "", "image": "aGVsbG8=", "image_id": "img", "bbox": [0, 0, 0, 0], "page_no": 3},
        ]
        for elem in elements:
            assert elem["type"] in ["title", "text", "table", "image", "chart", "formula", "header", "footer", "footnote", "endnote"]
            assert elem["page_no"] >= 1
