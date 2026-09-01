import json
from unittest.mock import patch, MagicMock
from app.services.analytics import get_ai_recommended_actions

class MockResponse:
    def __init__(self, text):
        self.text = text

@patch('app.services.llm_rotator.get_genai_client')
@patch('app.services.analytics.get_kpi_benchmarks')
@patch('app.services.llm_rotator.get_cached_response')
def test_ai_recommended_actions_fallback(mock_cache, mock_benchmarks, mock_get_client):
    # Setup mocks
    mock_cache.return_value = None
    mock_benchmarks.return_value = {
        "live": {"pipeline": 1000, "spend": 100, "cpa": 10, "conversions": 5},
        "comparisons": {"cpa": {"value": 0.5}}
    }
    
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Simulate the LLM returning complete garbage / malformed JSON
    mock_client.models.generate_content.return_value = MockResponse("I am an AI. Here are some things: [ { oops } ]")
    
    actions = get_ai_recommended_actions("CMP_TEST", 30)
    
    # Assert it falls back gracefully to an empty list instead of crashing with JSONDecodeError
    assert isinstance(actions, list)
    assert len(actions) == 0

@patch('app.services.llm_rotator.get_genai_client')
@patch('app.services.analytics.get_kpi_benchmarks')
@patch('app.services.llm_rotator.get_cached_response')
def test_ai_recommended_actions_success(mock_cache, mock_benchmarks, mock_get_client):
    # Setup mocks
    mock_cache.return_value = None
    mock_benchmarks.return_value = {
        "live": {"pipeline": 1000, "spend": 100, "cpa": 10, "conversions": 5},
        "comparisons": {"cpa": {"value": 0.5}}
    }
    
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    good_json = '''
    [
        {"title": "Analyze ROI", "message": "Call ROI", "action_command": "Call ROI", "icon": "fa-chart"}
    ]
    '''
    mock_client.models.generate_content.return_value = MockResponse(good_json)
    
    actions = get_ai_recommended_actions("CMP_TEST", 30)
    
    # Assert it parsed successfully
    assert len(actions) == 1
    assert actions[0]["title"].lower() == "analyze roi"
    # Ensure it appended the necessary trigger fields
    assert "id" in actions[0]
    assert actions[0]["type"] == "ai"
