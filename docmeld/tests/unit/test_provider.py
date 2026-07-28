"""Tests for LLMProvider injection and swappable LLM backends.

Phase D TDD: This file is written FIRST. Tests MUST fail (DocMeldParser
doesn't accept a provider parameter yet) before T043–T044 implement the seam.
"""
from __future__ import annotations

from typing import Any

import pytest

from docmeld.gold.provider import LLMProvider
from docmeld.parser import DocMeldParser


class DummyProvider:
    """Minimal LLMProvider implementation for testing without live API calls."""

    def extract_metadata(self, page_content: str) -> dict[str, Any]:
        return {"description": "dummy desc", "keywords": ["dummy"]}

    def generate(self, prompt: str) -> str:
        return "# Dummy Generated Content"

    def categorize(self, prompt: str) -> str:
        return "Dummy category response"


class TestLLMProviderInjection:
    """Verify LLMProvider can be injected into DocMeldParser."""

    def test_dummy_provider_conforms_to_protocol(self) -> None:
        """DummyProvider structurally matches LLMProvider Protocol."""
        dummy = DummyProvider()
        assert isinstance(dummy, LLMProvider), (
            "DummyProvider should conform to LLMProvider Protocol"
        )

    def test_inject_provider_into_parser(self) -> None:
        """DocMeldParser accepts an optional provider and uses it."""
        dummy = DummyProvider()
        # Use a file path that doesn't exist — we only test the injection seam,
        # not actual document processing.
        parser = DocMeldParser("nonexistent.pdf", provider=dummy)
        assert parser.provider is dummy, (
            "DocMeldParser should store the injected provider"
        )

    def test_default_provider_is_none(self) -> None:
        """When no provider is given, provider is None (DeepSeekClient built lazily)."""
        parser = DocMeldParser("nonexistent.pdf")
        assert parser.provider is None, (
            "DocMeldParser should default provider to None"
        )
