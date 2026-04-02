"""
Hugging Face LLM provider with retry logic and error handling.

This is the main class that agents interact with. It wraps the low-level
client and adds retry, validation, and exponential backoff.

Dependency: config, llm.client, llm.provider (exceptions).
"""
import time
import requests

from src.config import HuggingFaceConfig
from src.llm.client import call_hf_api
from src.llm.provider import LLMError, LLMRetryError


class HuggingFaceLLM:
    """
    Hugging Face LLM provider with retry logic and error handling.

    Provides a clean abstraction for LLM communication with:
    - Automatic retry on transient failures
    - Exponential backoff
    - Input/output validation

    Example::

        llm = HuggingFaceLLM(config)
        result = llm.generate("def hello():")
    """

    def __init__(self, config: HuggingFaceConfig) -> None:
        """
        Initialize Hugging Face LLM provider.

        Args:
            config: Immutable HuggingFaceConfig with API credentials.
        """
        self._config = config
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        self.exponential_backoff = config.exponential_backoff

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt with automatic retries.

        Args:
            prompt: Input prompt for the model.
            **kwargs: Additional arguments passed to the API
                (max_tokens, temperature).

        Returns:
            Generated text from the model or an error message as a string.
        """
        if not prompt or not prompt.strip():
            return "Error: Prompt cannot be empty."

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                result = call_hf_api(prompt, self._config, **kwargs)

                if not result or not str(result).strip():
                    return "Error: Received empty response from model."

                # Clean up response if it echoes the prompt (common with some code models)
                clean_result = str(result).strip()
                if clean_result.startswith(prompt.strip()):
                    clean_result = clean_result[len(prompt.strip()):].strip()
                return clean_result

            except ValueError as e:
                return f"Error: Invalid configuration or response ({e})."

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)

            except requests.exceptions.HTTPError as e:
                status_code = getattr(e.response, "status_code", None)
                if status_code in (429, 503):
                    last_exception = e
                    if attempt < self.max_retries:
                        self._wait_before_retry(attempt)
                    continue
                error_msg = getattr(e.response, "text", str(e))
                return f"API Error ({status_code}): {error_msg}"

            except Exception as e:
                return f"Error: Unexpected LLM failure ({e})."

        return f"Error: Failed after {self.max_retries + 1} attempts. Last error: {last_exception}"

    def _wait_before_retry(self, attempt: int) -> None:
        """Wait before retrying, with optional exponential backoff."""
        if self.exponential_backoff:
            delay = self.retry_delay * (2 ** attempt)
        else:
            delay = self.retry_delay
        time.sleep(delay)

    def __repr__(self) -> str:
        return (
            f"HuggingFaceLLM(model={self._config.model}, "
            f"max_retries={self.max_retries})"
        )
