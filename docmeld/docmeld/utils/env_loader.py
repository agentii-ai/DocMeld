"""Environment variable loader with .env.local support."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Recognized API key environment variables (checked in order).
_KNOWN_API_KEYS = (
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLM_API_KEY",
)

# Recognized endpoint / base URL environment variables.
_KNOWN_ENDPOINTS = (
    "DEEPSEEK_API_ENDPOINT",
    "LLM_API_ENDPOINT",
)


def load_env(
    env_path: str | None = None,
    require_api_key: bool = False,
) -> dict[str, str]:
    """Load environment variables from .env.local file.

    Args:
        env_path: Path to .env file. Defaults to .env.local in the current
            working directory.
        require_api_key: If True, raises ValueError when none of the
            recognized API key variables are present.

    Returns:
        Dict of loaded environment variables keyed by name.
    """
    if env_path is None:
        env_path = str(Path.cwd() / ".env.local")

    if Path(env_path).exists():
        load_dotenv(env_path, override=True)

    result: dict[str, str] = {}

    for key in _KNOWN_API_KEYS:
        value = os.environ.get(key, "")
        if value:
            result[key] = value

    for key in _KNOWN_ENDPOINTS:
        value = os.environ.get(key, "")
        if value:
            result[key] = value

    if require_api_key and not any(k in result for k in _KNOWN_API_KEYS):
        msg = (
            "No API key found. Set one of "
            + ", ".join(_KNOWN_API_KEYS)
            + " in .env.local or as an environment variable."
        )
        raise ValueError(msg)

    return result
