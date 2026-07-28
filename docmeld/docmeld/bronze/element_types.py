"""Pydantic models for document elements extracted from documents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Union, cast

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


class TitleElement(BaseModel):
    type: Literal["title"]
    level: int = Field(ge=0, le=5)
    content: str = Field(min_length=1)
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class TextElement(BaseModel):
    type: Literal["text"]
    content: str = Field(min_length=1)
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class TableElement(BaseModel):
    type: Literal["table"]
    content: str = Field(min_length=1)
    summary: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    table_data: dict[str, Any] | None = None
    hidden: bool = False


class ImageElement(BaseModel):
    type: Literal["image"]
    image_name: str
    content: str
    image: str
    image_id: str
    bbox: tuple[float, float, float, float]
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class ChartElement(BaseModel):
    type: Literal["chart"]
    chart_type: str
    content: str = Field(min_length=1)
    image: str
    image_name: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class FormulaElement(BaseModel):
    type: Literal["formula"]
    content: str = Field(min_length=1)
    formula_type: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class HeaderElement(BaseModel):
    type: Literal["header"]
    content: str = Field(min_length=1)
    page_scope: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class FooterElement(BaseModel):
    type: Literal["footer"]
    content: str = Field(min_length=1)
    page_scope: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class FootnoteElement(BaseModel):
    type: Literal["footnote"]
    content: str = Field(min_length=1)
    reference_id: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class EndnoteElement(BaseModel):
    type: Literal["endnote"]
    content: str = Field(min_length=1)
    reference_id: str
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class SmartArtElement(BaseModel):
    type: Literal["smartart"]
    smartart_type: str
    content: str = ""
    image: str = ""
    image_name: str = ""
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class NotesElement(BaseModel):
    type: Literal["notes"]
    content: str = Field(min_length=1)
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class GroupElement(BaseModel):
    type: Literal["group"]
    content: str = ""
    child_count: int = Field(ge=0)
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


class CommentElement(BaseModel):
    type: Literal["comment"]
    content: str = Field(min_length=1)
    author: str = ""
    page_no: int = Field(ge=1)
    element_id: str = ""
    parent_id: str = ""
    hidden: bool = False


BronzeElement: TypeAlias = Union[
    TitleElement,
    TextElement,
    TableElement,
    ImageElement,
    ChartElement,
    FormulaElement,
    HeaderElement,
    FooterElement,
    FootnoteElement,
    EndnoteElement,
    SmartArtElement,
    NotesElement,
    GroupElement,
    CommentElement,
]


def parse_element(data: dict[str, Any]) -> BronzeElement:
    """Parse a raw dict into the appropriate element model."""
    element_type = data.get("type")
    _type_map: dict[str, type[BaseModel]] = {
        "title": TitleElement,
        "text": TextElement,
        "table": TableElement,
        "image": ImageElement,
        "chart": ChartElement,
        "formula": FormulaElement,
        "header": HeaderElement,
        "footer": FooterElement,
        "footnote": FootnoteElement,
        "endnote": EndnoteElement,
        "smartart": SmartArtElement,
        "notes": NotesElement,
        "group": GroupElement,
        "comment": CommentElement,
    }
    model_cls = _type_map.get(element_type or "")
    if model_cls is None:
        msg = f"Unknown element type: {element_type}"
        raise ValueError(msg)
    return cast("BronzeElement", model_cls(**data))
