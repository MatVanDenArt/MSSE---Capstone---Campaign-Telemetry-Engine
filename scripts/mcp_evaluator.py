import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.services.analytics import simulate_budget_shift, get_budget_pacing

def main():
    print("Starting MCP Data Parity Validation Harness...")
    client = TestClient(app)
    
    test_cases = [
        {"campaign_id": "CMP_LIVE_DECARBONIZATION_25_26", "timeframe": 90, "budget_shift": 50000}
    ]
    
    report_lines = []
    report_lines.append("# MCP Data Parity & Quality Evaluation Report\n")
    
    for case in test_cases:
        campaign_id = case["campaign_id"]
        tf = case["timeframe"]
        budget = case["budget_shift"]
        
        report_lines.append(f"## Test Case: Campaign `{campaign_id}`, Timeframe `{tf} days`\n")
        
        # 1. UI Truth: Channel ROI Data
        print(f"Fetching UI Source of Truth for {campaign_id} ({tf}d)...")
        ui_res = client.get(f"/api/dashboard/v2/channel-roi-data?campaign_id={campaign_id}&timeframe={tf}")
        if ui_res.status_code == 200:
            ui_data = ui_res.json()
            li_ui_pipe = ui_data.get("linkedin", {}).get("pipeline", 0)
            li_ui_spend = ui_data.get("linkedin", {}).get("spend", 0)
            li_ui_roi = ui_data.get("linkedin", {}).get("roi_multiplier", 0)
        else:
            li_ui_pipe, li_ui_spend, li_ui_roi = 0, 0, 0
            
        report_lines.append("### 1. Data Parity Check: Channel ROI (LinkedIn)\n")
        report_lines.append("| Metric | Frontend UI (Source of Truth) | MCP Tool Output (`simulate_budget_shift`) | Match |")
        report_lines.append("|---|---|---|---|")
        
        # 2. MCP Execution: simulate_budget_shift
        print(f"Executing MCP Tool simulate_budget_shift...")
        mcp_data = simulate_budget_shift(channel="linkedin", budget=budget, campaign_id=campaign_id, timeframe=tf)
        mcp_roi = mcp_data.get("historical_roi_multiplier", 0)
        
        # Compare
        match_roi = "✅ PASS" if round(li_ui_roi, 1) == round(mcp_roi, 1) else "❌ FAIL"
        report_lines.append(f"| ROI Multiplier | {li_ui_roi:,.1f}x | {mcp_roi:,.1f}x | {match_roi} |")
        
        # Check reasons for failure if fail
        if "FAIL" in match_roi:
            report_lines.append("\n> [!WARNING]\n> **Data Divergence Detected!** The `simulate_budget_shift` MCP tool is calculating a completely different ROI multiplier than the frontend UI. The UI calculates channel-specific attribution (`user_id IN linkedin_events`), while the MCP tool calculates global campaign pipeline / global spend.\n")
            
        # UI Truth: Budget Pacing
        print(f"Fetching UI Source of Truth for Pacing...")
        ui_pacing = client.get(f"/api/dashboard/v2/channel-roi-data?campaign_id={campaign_id}&timeframe={tf}") # We reuse spend
        
        mcp_pacing = get_budget_pacing(channel="linkedin", campaign_id=campaign_id, timeframe=tf)
        mcp_spend = mcp_pacing.get("spent_budget", 0)
        
        match_spend = "✅ PASS" if round(li_ui_spend, 2) == round(mcp_spend, 2) else "❌ FAIL"
        
        report_lines.append("### 2. Data Parity Check: Budget Pacing (LinkedIn)\n")
        report_lines.append("| Metric | Frontend UI (Source of Truth) | MCP Tool Output (`get_budget_pacing`) | Match |")
        report_lines.append("|---|---|---|---|")
        report_lines.append(f"| Spent Budget | ${li_ui_spend:,.2f} | ${mcp_spend:,.2f} | {match_spend} |")
        
        if "FAIL" in match_spend:
             report_lines.append("\n> [!WARNING]\n> **Data Divergence Detected!** Pacing spend does not match.\n")
    
    # Save Report
    artifact_path = r"C:\Users\mpser\.gemini\antigravity\brain\6e76ceec-cb33-4973-b609-6fdf8bc28e0e\mcp_evaluation_report.md"
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Report saved to {artifact_path}")

if __name__ == "__main__":
    main()
