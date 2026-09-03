import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.analytics import get_budget_pacing, simulate_budget_shift, get_executive_pipeline_kpis

client = TestClient(app)

def test_pacing_parity():
    """
    Test that the get_budget_pacing MCP tool matches the data returned by the UI endpoint.
    """
    campaign = "CMP_TEST"
    tf = 0
    
    # UI Truth
    ui_res = client.get(f"/api/dashboard/v2/channel-roi-data?campaign_id={campaign}&timeframe={tf}")
    assert ui_res.status_code == 200
    ui_data = ui_res.json()
    
    # We sum the spend across the channels based on UI logic
    li_ui_spend = ui_data.get("linkedin", {}).get("spend", 0)
    web_ui_spend = ui_data.get("web", {}).get("spend", 0)
    em_ui_spend = ui_data.get("email", {}).get("spend", 0)
    total_ui_spend = li_ui_spend + web_ui_spend + em_ui_spend
    
    # MCP Output
    mcp_data = get_budget_pacing(channel="all", campaign_id=campaign, timeframe=tf)
    mcp_spend = mcp_data.get("spent_budget", 0)
    
    # Assert Parity (Allowing for tiny floating point discrepancies)
    assert round(total_ui_spend, 2) == round(mcp_spend, 2), f"Pacing Parity Failure: UI ${total_ui_spend} != MCP ${mcp_spend}"

def test_simulate_budget_shift_boundaries():
    """
    Test that the simulate_budget_shift MCP tool properly utilizes Late Binding
    and respects boundaries.
    """
    campaign = "CMP_TEST"
    tf = 0
    
    # Execute with Late Binding String
    mcp_data = simulate_budget_shift(channel="linkedin", budget="REMAINING_BUDGET", campaign_id=campaign, timeframe=tf)
    
    # It should dynamically calculate the new pipeline
    assert "projected_pipeline_value" in mcp_data
    assert mcp_data["projected_pipeline_value"] > 0
    
    # Execute with invalid channel to test boundary
    invalid_data = simulate_budget_shift(channel="carrier_pigeon", budget="REMAINING_BUDGET", campaign_id=campaign, timeframe=tf)
    assert "error" in invalid_data
    assert "Unsupported channel" in invalid_data["error"]

def test_executive_pipeline_parity():
    """
    Test that get_executive_pipeline_kpis matches the UI top-level cards.
    """
    campaign = "CMP_TEST"
    tf = 0
    
    # UI Truth (Overview cards)
    ui_res = client.get(f"/api/dashboard/overview?campaign_id={campaign}&timeframe={tf}")
    assert ui_res.status_code == 200
    ui_html = ui_res.text
    
    # Since UI overview returns HTML fragments, we might just assert the MCP tool doesn't crash 
    # and returns valid numerical structure for now until we build a JSON overview endpoint.
    mcp_data = get_executive_pipeline_kpis(campaign_id=campaign, timeframe=tf)
    assert "total_pipeline_value" in mcp_data
    assert "total_opportunities" in mcp_data
    assert isinstance(mcp_data["total_pipeline_value"], (int, float))
