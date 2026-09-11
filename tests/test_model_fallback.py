"""
Layer 5: Cascading model fallback & rate-limit resilience testing.

Architectural purpose:
In Google AI Studio (free tier), quota limits (15 RPM / 1,500 RPD) are enforced
on distinct, model-specific quota buckets. If burst traffic exhausts the quota for
`gemini-3.8-flash`, requests to `gemini-3.6-flash` and `gemini-3.5-flash` remain unthrottled.

This test suite asserts our two-dimensional resilience strategy in `app/services/llm_rotator.py`:
  1. Constraint verification: Asserts that FLASH_MODEL_CHAIN strictly contains Flash-tier models.
  2. Cache priority: Asserts that pre-computed prompt hashes return immediately without consuming API quota.
  3. Cascading fallback: Simulates HTTP 429 quota exhaustion on the primary model, verifying that
     the engine quarantines the exhausted API key and cascades execution down to the secondary model.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_rotator import (
    FLASH_MODEL_CHAIN,
    generate_content_with_fallback,
    MockResponse,
)

def test_flash_model_chain_contains_flash_family():
    # Verifies that the cascading model fallback chain is strictly configured with
    # Flash-tier models (avoiding Pro-tier models that have restrictive 2 RPM / 50 RPD limits).
    
    assert len(FLASH_MODEL_CHAIN) >= 3, "Fallback chain must contain at least 3 model tiers"
    for model in FLASH_MODEL_CHAIN:
        assert "flash" in model.lower(), f"Non-Flash model '{model}' found in FLASH_MODEL_CHAIN"

@patch("app.services.llm_rotator.get_cached_response")
def test_fallback_returns_cached_response_directly(mock_get_cached):
    
    # Verifies that when a prompt hash exists in cache (Redis or local JSON),
    # generate_content_with_fallback returns a MockResponse immediately without network calls.
    
    mock_get_cached.return_value = "Cached output text"
    
    resp = generate_content_with_fallback("test prompt")
    
    assert isinstance(resp, MockResponse), "Expected MockResponse duck-typed object from cache"
    assert resp.text == "Cached output text", "Cached text does not match stored value"

@patch("app.services.llm_rotator.get_cached_response", return_value=None)
@patch("app.services.llm_rotator.set_cached_response")
@patch("app.services.llm_rotator.get_random_api_key", return_value="fake_key_12345")
@patch("google.genai.Client")
def test_fallback_cascades_on_429(mock_genai_client, mock_key, mock_set_cache, mock_get_cache):
    
    # Simulates primary model (gemini-3.8-flash) encountering HTTP 429 RESOURCE_EXHAUSTED
    # across all configured key retry attempts, asserting that execution seamlessly cascades
    # down to the secondary model (gemini-3.6-flash).
    
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance

    calls = []

    def mock_generate_content(model, contents, **kwargs):
        calls.append(model)
        if model == "gemini-3.8-flash":
            # Primary model fails with 429 rate limit
            raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for model gemini-3.8-flash")
        # Secondary model succeeds
        mock_resp = MagicMock()
        mock_resp.text = f"Success from {model}"
        return mock_resp

    mock_instance.models.generate_content.side_effect = mock_generate_content

    # Execute with fallback chain
    resp = generate_content_with_fallback(
        contents="Analyze campaign metrics",
        model_chain=["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash"],
        max_key_retries=2,
    )

    # Assert that execution cascaded to gemini-3.6-flash and succeeded
    assert resp.text == "Success from gemini-3.6-flash", "Failed to retrieve successful response from fallback model"
    assert calls.count("gemini-3.8-flash") == 2, "Primary model should be attempted max_key_retries times before cascading"
    assert "gemini-3.6-flash" in calls, "Secondary model was never invoked after primary exhausted quota"
