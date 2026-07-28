"""Shared pytest fixtures for DocMeld tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config, items):
    """Auto-tag tests by directory so ``pytest -m unit`` etc. work.

    Maps tests/unit/ → unit, tests/integration/ → integration,
    tests/contract/ → contract. No per-test decorators needed.
    """
    for item in items:
        fspath = str(item.fspath)
        if "/unit/" in fspath:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in fspath:
            item.add_marker(pytest.mark.integration)
        elif "/contract/" in fspath:
            item.add_marker(pytest.mark.contract)


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture()
def sample_simple_pdf() -> Path:
    return FIXTURES_DIR / "sample_simple.pdf"


@pytest.fixture()
def sample_complex_pdf() -> Path:
    return FIXTURES_DIR / "sample_complex.pdf"


@pytest.fixture()
def tmp_env(tmp_path: Path) -> Path:
    """Create a temporary .env.local file with test API key."""
    env_file = tmp_path / ".env.local"
    env_file.write_text("DEEPSEEK_API_KEY=test_key_for_testing\n")
    return env_file
