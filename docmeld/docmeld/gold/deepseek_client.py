"""DeepSeek API client for gold stage metadata extraction."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, TypeVar

from docmeld.utils.text import strip_code_fences

logger = logging.getLogger("docmeld")

T = TypeVar("T")


def call_with_retry(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Call a function with exponential backoff retry.

    Args:
        func: Callable to execute.
        max_retries: Maximum number of attempts.
        base_delay: Base delay in seconds (doubles each retry).

    Returns:
        Result of the function call.

    Raises:
        The last exception if all retries fail.
    """
    last_exception: Exception | None = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait = base_delay * (2**attempt)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
    raise last_exception  # type: ignore[misc]


class DeepSeekClient:
    """Wrapper for DeepSeek chat API with structured output."""

    DEFAULT_MODEL = "deepseek-chat"

    def __init__(
        self,
        api_key: str,
        endpoint: str | None = None,
        temperature: float = 1.0,
        model: str = DEFAULT_MODEL,
    ) -> None:
        if not api_key:
            msg = "DEEPSEEK_API_KEY is required. Set it in .env.local or pass directly."
            raise ValueError(msg)
        self.api_key = api_key
        self.endpoint = endpoint
        self.temperature = temperature
        self.model = model

    def extract_metadata(self, page_content: str) -> dict[str, Any]:
        """Extract description and keywords from page content.

        Args:
            page_content: Markdown-formatted page content.

        Returns:
            Dict with 'description' (str) and 'keywords' (list[str]).
        """
        return call_with_retry(
            lambda: self._call_api(page_content),
            max_retries=3,
            base_delay=1.0,
        )

    def _call_api(self, page_content: str) -> dict[str, Any]:
        """Make the actual API call to DeepSeek."""
        from langchain_deepseek import ChatDeepSeek

        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "api_key": self.api_key,
        }
        if self.endpoint:
            kwargs["base_url"] = self.endpoint

        llm = ChatDeepSeek(**kwargs)

        prompt = (
            "Analyze the following document page content. "
            "Return a JSON object with exactly two fields:\n"
            '- "description": a single-line summary of the page content\n'
            '- "keywords": a list of 3-10 relevant keywords\n\n'
            "Return ONLY valid JSON, no other text.\n\n"
            f"Page content:\n{page_content}"
        )

        response = llm.invoke(prompt)
        text = str(response.content).strip()

        # Strip markdown code fences if present
        text = strip_code_fences(text)

        result = json.loads(text)

        return {
            "description": result.get("description", ""),
            "keywords": result.get("keywords", []),
        }

    def categorize(self, prompt: str) -> str:
        """Send a categorization prompt and return the raw response text.

        Args:
            prompt: The full categorization prompt with paper metadata.

        Returns:
            Raw response text from the API.
        """
        return call_with_retry(
            lambda: self._call_text_api(prompt),
            max_retries=3,
            base_delay=1.0,
        )

    def generate(self, prompt: str) -> str:
        """Send a free-form generation prompt and return the raw response text.

        Used for PRD, workflow, and skills generation.

        Args:
            prompt: The full generation prompt with document content.

        Returns:
            Raw response text (markdown/JSON) from the API.
        """
        return call_with_retry(
            lambda: self._call_text_api(prompt),
            max_retries=3,
            base_delay=1.0,
        )

    def _call_text_api(self, prompt: str) -> str:
        """Make the actual free-form text API call."""
        from langchain_deepseek import ChatDeepSeek

        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "api_key": self.api_key,
            "max_tokens": 8192,
        }
        if self.endpoint:
            kwargs["base_url"] = self.endpoint

        llm = ChatDeepSeek(**kwargs)
        response = llm.invoke(prompt)
        return str(response.content).strip()

    # Deprecated aliases (pre-0.4.0 names). Prefer generate()/categorize().
    def categorize_papers(self, prompt: str) -> str:
        """Deprecated alias for :meth:`categorize`."""
        return self.categorize(prompt)

    def generate_prd(self, prompt: str) -> str:
        """Deprecated alias for :meth:`generate`."""
        return self.generate(prompt)
