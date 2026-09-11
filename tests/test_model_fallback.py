import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_rotator import (
    FLASH_MODEL_CHAIN,
    generate_content_with_fallback,
    MockResponse,
)

def test_flash_model_chain_contains_flash_family():
    """Verify that FLASH_MODEL_CHAIN is strictly configured with Flash-tier models."""
    assert len(FLASH_MODEL_CHAIN) >= 3
    for model in FLASH_MODEL_CHAIN:
        assert "flash" in model.lower(), f"Expected Flash model, got {model}"

@patch("app.services.llm_rotator.get_cached_response")
def test_fallback_returns_cached_response_directly(mock_get_cached):
    """Verify that if cache contains the response, no network API call is made."""
    mock_get_cached.return_value = "Cached output text"
    resp = generate_content_with_fallback("test prompt")
    assert isinstance(resp, MockResponse)
    assert resp.text == "Cached output text"

@patch("app.services.llm_rotator.get_cached_response", return_value=None)
@patch("app.services.llm_rotator.set_cached_response")
@patch("app.services.llm_rotator.get_random_api_key", return_value="fake_key_12345")
@patch("google.genai.Client")
def test_fallback_cascades_on_429(mock_genai_client, mock_key, mock_set_cache, mock_get_cache):
    """
    Simulate primary model (gemini-3.8-flash) failing with 429 quota exhaustion across attempts,
    and secondary model (gemini-3.6-flash) succeeding.
    """
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance

    calls = []

    def mock_generate_content(model, contents, **kwargs):
        calls.append(model)
        if model == "gemini-3.8-flash":
            raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for model gemini-3.8-flash")
        mock_resp = MagicMock()
        mock_resp.text = f"Success from {model}"
        return mock_resp

    mock_instance.models.generate_content.side_effect = mock_generate_content

    resp = generate_content_with_fallback(
        contents="Analyze campaign metrics",
        model_chain=["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash"],
        max_key_retries=2,
    )

    assert resp.text == "Success from gemini-3.6-flash"
    assert calls.count("gemini-3.8-flash") == 2
    assert "gemini-3.6-flash" in calls
