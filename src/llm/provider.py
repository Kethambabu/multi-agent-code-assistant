"""
LLM Provider interface and exceptions.

Defines the protocol (duck-typing interface) that all LLM providers must satisfy.
This enables swapping providers without changing agent code.

Dependency: None (pure interface).
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    Protocol for LLM providers.

    Any object with a ``generate(prompt: str, **kwargs) -> str`` method
    satisfies this protocol, enabling duck-typing and easy mocking in tests.
    """

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        ...


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMRetryError(LLMError):
    """Raised when maximum retries are exceeded."""
    pass
