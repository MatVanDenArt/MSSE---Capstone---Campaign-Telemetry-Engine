import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

@patch('app.services.analytics.get_ai_recommended_actions')
def test_dashboard_overview(mock_ai):
    # Mock AI to avoid real API calls during API tests
    mock_ai.return_value = []
    
    # We are using CMP_TEST because our conftest.py mock database has data for it
    response = client.get("/api/dashboard/overview?campaign_id=CMP_TEST&timeframe=0")
    
    assert response.status_code == 200
    # Assert it returns HTML containing the overview fragment
    assert "text/html" in response.headers["content-type"]
    assert "mod_channel_roi" in response.text or "chart" in response.text or "overview" in response.text

@patch('app.services.analytics.get_ai_recommended_actions')
def test_dashboard_performance(mock_ai):
    mock_ai.return_value = []
    
    response = client.get("/api/dashboard/performance?campaign_id=CMP_TEST&timeframe=0")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "fatigue" in response.text.lower() or "performance" in response.text.lower()

def test_dashboard_action_center():
    # Test the HTMX lazy loading endpoint for the Action Center
    response = client.get("/api/dashboard/action-center?campaign_id=CMP_TEST&timeframe=0")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
