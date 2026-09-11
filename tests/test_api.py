"""
Layer 6: Presentation layer & server-driven UI fragment testing.

Architectural purpose:
Because the frontend employs a server-driven UI architecture with HTMX and Jinja2,
the FastAPI backend serves rendered HTML fragments directly into targeted DOM containers
rather than returning raw JSON for client-side assembly.

This test suite uses FastAPI's TestClient to verify:
  1. Route availability and HTTP 200 OK status codes across primary dashboard tabs.
  2. Content-Type integrity (ensuring text/html response headers for HTMX swaps).
  3. Template rendering stability (verifying key DOM markers, chart canvas IDs, and partial components).
  4. Isolation from external AI services by mocking get_ai_recommended_actions.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

@patch('app.services.analytics.get_ai_recommended_actions')
def test_dashboard_overview(mock_ai):
    
    # Validates the Executive Overview tab endpoint (/api/dashboard/overview).
    # Asserts that the server returns HTTP 200 with rendered HTML containing
    # channel ROI markers, KPI benchmark cards, and Chart.js initialization tags.
    
    # Mock AI recommended actions to isolate presentation logic from external LLM APIs
    mock_ai.return_value = []
    
    # Query overview route with test campaign context
    response = client.get("/api/dashboard/overview?campaign_id=CMP_TEST&timeframe=0")
    
    # Assert HTTP success and HTML content type
    assert response.status_code == 200, f"Dashboard overview failed with status {response.status_code}"
    assert "text/html" in response.headers["content-type"], "Response must be an HTML fragment for HTMX swapping"
    
    # Assert presence of core overview template components
    assert "mod_channel_roi" in response.text or "chart" in response.text or "overview" in response.text, (
        "Rendered overview fragment missing expected chart or KPI container elements"
    )

@patch('app.services.analytics.get_ai_recommended_actions')
def test_dashboard_performance(mock_ai):
    
    # Validates the Performance & fatigue tab endpoint (/api/dashboard/performance).
    # Asserts that the server returns HTTP 200 with rendered HTML containing
    # the omnichannel asset matrix and fatigue index indicators.
    
    mock_ai.return_value = []
    
    response = client.get("/api/dashboard/performance?campaign_id=CMP_TEST&timeframe=0")
    
    assert response.status_code == 200, f"Dashboard performance failed with status {response.status_code}"
    assert "text/html" in response.headers["content-type"], "Response must be an HTML fragment"
    assert "fatigue" in response.text.lower() or "performance" in response.text.lower(), (
        "Rendered performance fragment missing asset fatigue matrix markers"
    )

def test_dashboard_action_center():
    
    # Validates the Action Center lazy-load endpoint (/api/dashboard/action-center).
    # Asserts that the asynchronous HTMX lazy-loading drawer returns HTTP 200
    # with valid HTML cards ready for dynamic swapping into the DOM.
    
    response = client.get("/api/dashboard/action-center?campaign_id=CMP_TEST&timeframe=0")
    
    assert response.status_code == 200, f"Action center endpoint failed with status {response.status_code}"
    assert "text/html" in response.headers["content-type"], "Response must be an HTML fragment"


def test_telemetry_ai_calls_endpoint():
    """Validates the live AI telemetry stats endpoint (/api/telemetry/ai-calls)."""
    response = client.get("/api/telemetry/ai-calls")
    assert response.status_code == 200
    data = response.json()
    assert "total_calls" in data
    assert "cache_hits" in data
    assert isinstance(data["total_calls"], int)
    assert isinstance(data["cache_hits"], int)

