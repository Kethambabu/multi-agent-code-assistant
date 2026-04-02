"""
Low-level Hugging Face Inference API HTTP client.

Handles raw HTTP communication with the HF API.
No retry logic — that belongs in the higher-level HuggingFaceLLM wrapper.

Dependency: config (HuggingFaceConfig).
"""
import requests
from typing import Dict, Any

from src.config import HuggingFaceConfig


def call_hf_api(
    prompt: str,
    config: HuggingFaceConfig,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> str:
    """
    Call Hugging Face Inference API with a prompt.

    Args:
        prompt: Input prompt for the model.
        config: HuggingFaceConfig with API credentials and settings.
        max_tokens: Maximum length of generated text.
        temperature: Controls randomness (0.0–1.0).

    Returns:
        Generated text from the model.

    Raises:
        ValueError: If configuration is invalid or response format unexpected.
        requests.exceptions.RequestException: If API call fails.
    """
    url = config.api_url
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }

    # Format explicitly for OpenAI-compatible chat completions API
    # deployed on router.huggingface.co/v1/chat/completions
    payload: Dict[str, Any] = {
        "model": config.model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("Invalid API key. Check HUGGINGFACE_API_KEY.") from e
        elif response.status_code == 429:
            raise requests.exceptions.RequestException(
                "Rate limited by Hugging Face API."
            ) from e
        raise
    except requests.exceptions.Timeout:
        raise requests.exceptions.RequestException(
            f"Request timeout after {config.timeout} seconds."
        )

    # Parse response
    result = response.json()

    # Parse OpenAI compatible format
    if "choices" in result and len(result["choices"]) > 0:
        message = result["choices"][0].get("message", {})
        if "content" in message:
            return message["content"]

    raise ValueError(f"Unexpected API response format: {result}")
