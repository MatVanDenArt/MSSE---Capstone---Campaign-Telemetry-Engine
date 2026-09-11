"""
Layer 4: LLM parser & graceful degradation testing.

Architectural purpose:
Because Large Language Models are non-deterministic, remote generative responses
can occasionally produce truncated strings, markdown code-fence wrappers, or malformed JSON.
If the backend parser attempts a naive `json.loads()` without error handling, an unhandled
`JSONDecodeError` will crash the route handler with an HTTP 500.

This test suite isolates the parser by:
  1. Injecting synthetic malformed JSON responses via unittest.mock.
  2. Asserting that the parser degrades gracefully to a safe empty list instead of crashing.
  3. Verifying that valid JSON responses are enriched with runtime trigger IDs and telemetry metadata.
"""

import json
from unittest.mock import patch, MagicMock
from app.services.analytics import get_ai_recommended_actions

class MockResponse:
    # Minimal mock mimicking the google.genai GenerateContentResponse object.
    def __init__(self, text):
        self.text = text

@patch('app.services.llm_rotator.get_genai_client')
@patch('app.services.analytics.get_kpi_benchmarks')
@patch('app.services.llm_rotator.get_cached_response')
def test_ai_recommended_actions_fallback(mock_cache, mock_benchmarks, mock_get_client):
    
    # Validates graceful degradation when the LLM returns invalid/malformed JSON.
    # Asserts that the function intercepts the JSONDecodeError, logs the anomaly,
    # and returns a safe empty list rather than bubbling up a 500 error to the UI.
    
    # 1. Mock cache miss and baseline KPI comparisons
    mock_cache.return_value = None
    mock_benchmarks.return_value = {
        "live": {"pipeline": 1000, "spend": 100, "cpa": 10, "conversions": 5},
        "comparisons": {"cpa": {"value": 0.5}}
    }
    
    # 2. Configure mock client to return syntactically broken JSON
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.models.generate_content.return_value = MockResponse("I am an AI. Here are some things: [ { oops } ]")
    
    # 3. Execute recommended actions generator
    actions = get_ai_recommended_actions("CMP_TEST", 30)
    
    # 4. Verify that unparseable output falls back cleanly to an empty list
    assert isinstance(actions, list), "Expected list response on parser failure"
    assert len(actions) == 0, "Fallback should return empty list on malformed JSON"

@patch('app.services.llm_rotator.get_genai_client')
@patch('app.services.analytics.get_kpi_benchmarks')
@patch('app.services.llm_rotator.get_cached_response')
def test_ai_recommended_actions_success(mock_cache, mock_benchmarks, mock_get_client):
    # Validates parsing and schema enrichment when the LLM returns valid structured JSON.
    # Asserts that the action payload is parsed and enriched with necessary UI trigger IDs.
    
    # 1. Mock cache miss and KPI benchmarks
    mock_cache.return_value = None
    mock_benchmarks.return_value = {
        "live": {"pipeline": 1000, "spend": 100, "cpa": 10, "conversions": 5},
        "comparisons": {"cpa": {"value": 0.5}}
    }
    
    # 2. Configure mock client to return valid JSON array of recommendations
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    good_json = '''
    [
        {"title": "Analyze ROI", "message": "Call ROI", "action_command": "Call ROI", "icon": "fa-chart"}
    ]
    '''
    mock_client.models.generate_content.return_value = MockResponse(good_json)
    
    # 3. Execute generator
    actions = get_ai_recommended_actions("CMP_TEST", 30)
    
    # 4. Assert successful parsing and dynamic field enrichment
    assert len(actions) == 1, "Expected exactly 1 parsed action"
    assert actions[0]["title"].lower() == "analyze roi", "Incorrect action title parsed"
    assert "id" in actions[0], "Parser must dynamically inject a unique action 'id' for HTMX triggering"
    assert actions[0]["type"] == "ai", "Action metadata type must be flagged as 'ai'"
