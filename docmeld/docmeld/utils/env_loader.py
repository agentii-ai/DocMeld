"""Environment variable loader with .env.local support."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env(
    env_path: str | None = None,
    require_api_key: bool = False,
) -> dict[str, str]:
    """Load environment variables from .env.local file.

    Args:
        env_path: Path to .env file. Defaults to .env.local in repo root.
        require_api_key: If True, raises ValueError when DEEPSEEK_API_KEY is missing.

    Returns:
        Dict of loaded environment variables relevant to DocMeld.
    """
    if env_path is None:
        env_path = str(Path.cwd() / ".env.local")

    if Path(env_path).exists():
        load_dotenv(env_path, override=True)

    result: dict[str, str] = {}

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key:
        result["DEEPSEEK_API_KEY"] = api_key

    endpoint = os.environ.get("DEEPSEEK_API_ENDPOINT", "")
    if endpoint:
        result["DEEPSEEK_API_ENDPOINT"] = endpoint

    if require_api_key and "DEEPSEEK_API_KEY" not in result:
        msg = "DEEPSEEK_API_KEY not found. Set it in .env.local or as an environment variable."
        raise ValueError(msg)

    return result
