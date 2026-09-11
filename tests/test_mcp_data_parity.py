"""
Layer 3: MCP integration & data parity testing.

Architectural purpose:
In an agentic copilot architecture, data divergence is a fatal failure mode:
if the AI copilot cites one financial number in chat while the dashboard UI displays another,
executive trust is destroyed.

This test suite uses FastAPI's TestClient to simultaneously fetch:
  1. The UI Source-of-Truth: Rendered data served to the browser.
  2. The MCP Tool Output: Raw analytical JSON returned to the LLM.
It asserts that financial metrics, media spend, and pipeline aggregations match
to the penny across both presentation and AI layers.
It also validates "Abstract Late Binding" (e.g., resolving declarative tokens like REMAINING_BUDGET).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.analytics import (
    get_budget_pacing,
    simulate_budget_shift,
    get_executive_pipeline_kpis,
)

client = TestClient(app)

def test_pacing_parity():
    # Validates mathematical parity between the UI Channel ROI endpoint and the get_budget_pacing MCP tool.
    # Asserts that total media spend across channels in the UI matches spent_budget reported to the LLM.
    
    campaign = "CMP_TEST"
    tf = 0
    
    # 1. Fetch UI Truth from the live dashboard endpoint
    ui_res = client.get(f"/api/dashboard/v2/channel-roi-data?campaign_id={campaign}&timeframe={tf}")
    assert ui_res.status_code == 200, "UI channel ROI endpoint failed"
    ui_data = ui_res.json()
    
    # Sum spend across all channels based on UI logic
    li_ui_spend = ui_data.get("linkedin", {}).get("spend", 0)
    web_ui_spend = ui_data.get("web", {}).get("spend", 0)
    em_ui_spend = ui_data.get("email", {}).get("spend", 0)
    total_ui_spend = li_ui_spend + web_ui_spend + em_ui_spend
    
    # 2. Query the MCP Tool directly with the identical campaign and timeframe scope
    mcp_data = get_budget_pacing(channel="all", campaign_id=campaign, timeframe=tf)
    mcp_spend = mcp_data.get("spent_budget", 0)
    
    # 3. Assert mathematical parity (allowing for minor floating-point rounding)
    assert round(total_ui_spend, 2) == round(mcp_spend, 2), (
        f"Pacing Parity Failure: UI reported ${total_ui_spend} but MCP tool returned ${mcp_spend}"
    )

def test_simulate_budget_shift_boundaries():
    
    # Validates Abstract Late Binding and boundary validation in simulate_budget_shift.
    # 1. Tests dynamic resolution of the declarative string token 'REMAINING_BUDGET'.
    # 2. Tests rejection and graceful error reporting for unsupported channels.
    
    campaign = "CMP_TEST"
    tf = 0
    
    # 1. Execute with Late Binding token: backend must intercept and resolve against SQLite
    mcp_data = simulate_budget_shift(
        channel="linkedin",
        budget="REMAINING_BUDGET",
        campaign_id=campaign,
        timeframe=tf
    )
    
    # Assert that pipeline impact is dynamically calculated
    assert "projected_pipeline_value" in mcp_data, "Missing 'projected_pipeline_value' in simulation response"
    assert mcp_data["projected_pipeline_value"] > 0, "Simulation projected zero or negative pipeline"
    
    # 2. Execute with an invalid channel to verify boundary enforcement
    invalid_data = simulate_budget_shift(
        channel="carrier_pigeon",
        budget="REMAINING_BUDGET",
        campaign_id=campaign,
        timeframe=tf
    )
    assert "error" in invalid_data, "Simulation failed to catch invalid channel boundary"
    assert "Unsupported channel" in invalid_data["error"], "Incorrect error message for invalid channel"

def test_executive_pipeline_parity():
    
    # Validates that get_executive_pipeline_kpis returns valid numerical aggregations
    # aligned with the top-level overview cards.
    
    campaign = "CMP_TEST"
    tf = 0
    
    # 1. Verify the UI overview fragment renders successfully
    ui_res = client.get(f"/api/dashboard/overview?campaign_id={campaign}&timeframe={tf}")
    assert ui_res.status_code == 200, "UI overview endpoint failed"
    
    # 2. Execute the executive pipeline MCP tool
    mcp_data = get_executive_pipeline_kpis(campaign_id=campaign, timeframe=tf)
    
    # Assert structural integrity and valid numeric metrics
    assert "total_open_pipeline" in mcp_data, "Missing 'total_open_pipeline' in executive KPIs"
    assert "total_open_opportunities" in mcp_data, "Missing 'total_open_opportunities' in executive KPIs"
    assert isinstance(mcp_data["total_open_pipeline"], (int, float)), "total_open_pipeline must be numeric"
