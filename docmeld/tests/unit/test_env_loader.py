"""Unit tests for environment loader."""
import os
import pytest
from pathlib import Path


class TestLoadEnv:
    def test_loads_api_key_from_env_file(self, tmp_path: Path) -> None:
        from docmeld.utils.env_loader import load_env

        env_file = tmp_path / ".env.local"
        env_file.write_text("DEEPSEEK_API_KEY=test_key_123\n")

        result = load_env(env_path=str(env_file))
        assert result["DEEPSEEK_API_KEY"] == "test_key_123"

    def test_missing_api_key_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from docmeld.utils.env_loader import load_env

        # Clear all known API keys from the environment
        for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY"):
            monkeypatch.delenv(key, raising=False)

        env_file = tmp_path / ".env.local"
        env_file.write_text("OTHER_VAR=value\n")

        with pytest.raises(ValueError, match="No API key found"):
            load_env(env_path=str(env_file), require_api_key=True)

    def test_optional_endpoint(self, tmp_path: Path) -> None:
        from docmeld.utils.env_loader import load_env

        env_file = tmp_path / ".env.local"
        env_file.write_text(
            "DEEPSEEK_API_KEY=key123\nDEEPSEEK_API_ENDPOINT=https://custom.api.com\n"
        )

        result = load_env(env_path=str(env_file))
        assert result["DEEPSEEK_API_KEY"] == "key123"
        assert result["DEEPSEEK_API_ENDPOINT"] == "https://custom.api.com"

    def test_missing_env_file_no_error_when_not_required(self, tmp_path: Path) -> None:
        from docmeld.utils.env_loader import load_env

        result = load_env(env_path=str(tmp_path / "nonexistent"), require_api_key=False)
        assert isinstance(result, dict)

    def test_recognizes_openai_key(self, tmp_path: Path) -> None:
        from docmeld.utils.env_loader import load_env

        env_file = tmp_path / ".env.local"
        env_file.write_text("OPENAI_API_KEY=sk-openai-test\n")

        result = load_env(env_path=str(env_file))
        assert result["OPENAI_API_KEY"] == "sk-openai-test"

    def test_require_any_known_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from docmeld.utils.env_loader import load_env

        # Clear all known keys
        for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY"):
            monkeypatch.delenv(key, raising=False)

        env_file = tmp_path / ".env.local"
        env_file.write_text("OPENAI_API_KEY=sk-test\n")

        result = load_env(env_path=str(env_file), require_api_key=True)
        assert "OPENAI_API_KEY" in result
