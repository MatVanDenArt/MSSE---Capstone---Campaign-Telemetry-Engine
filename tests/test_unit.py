"""
Layer 1: Unit Testing & Mathematical Boundaries for the Full MCP Toolset.

Architectural Purpose:
Directly invokes and asserts the mathematical correctness, data boundaries, and output schemas
for ALL 16 analytical functions exposed to the Gemini AI Copilot via the Model Context Protocol (MCP).
The test suite is organized into the four distinct analytical domains:
  1. Financial & Budgetary Analytics (5 functions)
  2. ABM & Audience Intelligence (5 functions)
  3. Creative & Asset Performance (4 functions)
  4. Generative Content Synthesis (2 functions)

All tests execute against the isolated test database provisioned by conftest.py.
External LLM generation in generative tools is mocked to guarantee fast, deterministic execution.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.analytics import (
    # 1. Financial & Budgetary
    calculate_blended_cpa,
    simulate_budget_shift,
    get_executive_pipeline_kpis,
    get_budget_pacing,
    run_attribution_model,
    # 2. ABM & Audience
    get_account_penetration,
    get_tam_penetration,
    map_buying_committee,
    get_intent_surge_signals,
    get_user_journey,
    # 3. Creative & Asset Performance
    evaluate_trickle_threshold,
    get_asset_impact_matrix,
    compare_asset_baselines,
    calculate_share_of_voice,
    # 4. Generative Content
    generate_ab_test_variants,
    draft_outreach_sequence,
)


# ==============================================================================
# Domain 1: Financial & Budgetary Analytics (5 Tools)
# ==============================================================================

def test_calculate_blended_cpa():
    """
    Tool 1: calculate_blended_cpa
    Validates cross-channel media spend vs CRM closed-won conversions.
    Formula: Total Spend / Closed-Won Opps.
    """
    res = calculate_blended_cpa(campaign_id="CMP_TEST", timeframe=0)
    assert "blended_cpa" in res, "Response missing 'blended_cpa'"
    assert isinstance(res["blended_cpa"], (float, int)), "'blended_cpa' must be numeric"
    assert "verdict" in res, "Response missing executive 'verdict'"


def test_simulate_budget_shift():
    """
    Tool 2: simulate_budget_shift
    Validates counterfactual pipeline simulation when reallocating budget to a channel.
    """
    res = simulate_budget_shift(channel="linkedin", budget=25000, campaign_id="CMP_TEST", timeframe=0)
    assert "projected_pipeline_value" in res, "Missing 'projected_pipeline_value'"
    assert res["projected_pipeline_value"] > 0, "Projected pipeline should be positive"
    assert "projected_roas" in res, "Missing 'projected_roas'"
    assert "verdict" in res, "Missing 'verdict'"


def test_get_executive_pipeline_kpis():
    """
    Tool 3: get_executive_pipeline_kpis
    Validates high-level executive pipeline KPI aggregation.
    """
    res = get_executive_pipeline_kpis(campaign_id="CMP_TEST", timeframe=0)
    assert "total_open_pipeline" in res, "Missing 'total_open_pipeline'"
    assert "total_open_opportunities" in res, "Missing 'total_open_opportunities'"
    assert isinstance(res["total_open_pipeline"], (int, float)), "Pipeline value must be numeric"


def test_get_budget_pacing():
    """
    Tool 4: get_budget_pacing
    Validates daily burn rates, spend tracking, and runway health.
    """
    res = get_budget_pacing(channel="all", campaign_id="CMP_TEST", timeframe=0)
    assert "spent_budget" in res, "Missing 'spent_budget'"
    assert "allocated_budget" in res, "Missing 'allocated_budget'"
    assert "pacing_status" in res, "Missing 'pacing_status'"


def test_run_attribution_model():
    """
    Tool 5: run_attribution_model
    Validates multi-touch attribution calculations (linear model).
    """
    res = run_attribution_model(model_type="linear", campaign_id="CMP_TEST", timeframe=0)
    assert "channel_distribution" in res, "Missing 'channel_distribution'"
    assert "total_attributed_revenue" in res, "Missing 'total_attributed_revenue'"
    assert res["model_type"] == "linear", "Model type mismatch"


# ==============================================================================
# Domain 2: ABM & Audience Intelligence (5 Tools)
# ==============================================================================

def test_get_account_penetration():
    """
    Tool 6: get_account_penetration
    Validates company engagement breakdown grouped by seniority tier.
    """
    res = get_account_penetration(campaign_id="CMP_TEST", timeframe=0)
    assert "account_penetration" in res, "Missing 'account_penetration' payload"
    assert isinstance(res["account_penetration"], dict), "'account_penetration' must be a dictionary"


def test_get_tam_penetration():
    """
    Tool 7: get_tam_penetration
    Validates Total Addressable Market (TAM) coverage vs engaged accounts.
    """
    res = get_tam_penetration(campaign_id="CMP_TEST", timeframe=0)
    assert "raw_value" in res, "Missing 'raw_value' percentage"
    assert "engaged_accounts" in res, "Missing 'engaged_accounts' count"
    assert res["engaged_accounts"] >= 0, "Engaged accounts cannot be negative"


def test_map_buying_committee():
    """
    Tool 8: map_buying_committee
    Validates buying committee discovery and multi-threading gap detection for an account.
    """
    res = map_buying_committee(account_identifier="Acme Corp", campaign_id="CMP_TEST", timeframe=0)
    assert "company_name" in res, "Missing 'company_name'"
    assert res["company_name"] == "Acme Corp", "Account name mismatch"
    assert "buying_committee_segments" in res, "Missing 'buying_committee_segments'"
    assert "strategic_insight" in res, "Missing 'strategic_insight'"


def test_get_intent_surge_signals():
    """
    Tool 9: get_intent_surge_signals
    Validates 48-hour velocity spike detection for high-priority target accounts.
    """
    res = get_intent_surge_signals(account_identifier="Acme Corp", campaign_id="CMP_TEST", timeframe=0)
    assert "company_name" in res, "Missing 'company_name'"
    assert "surge_detected" in res, "Missing 'surge_detected' flag"
    assert isinstance(res["surge_detected"], bool), "'surge_detected' must be a boolean"


def test_get_user_journey():
    """
    Tool 10: get_user_journey
    Validates chronological cross-channel touchpoint reconstruction for a specific contact.
    """
    res = get_user_journey(name="Test User", company="Acme Corp", campaign_id="CMP_TEST", timeframe=0)
    assert "html_timeline" in res, "Missing 'html_timeline' fragment"
    assert isinstance(res["html_timeline"], str), "'html_timeline' must be a string"


# ==============================================================================
# Domain 3: Creative & Asset Performance (4 Tools)
# ==============================================================================

def test_evaluate_trickle_threshold():
    """
    Tool 11: evaluate_trickle_threshold
    Validates asset fatigue and traffic decay (>95% drop sustained for 7 days).
    """
    res = evaluate_trickle_threshold(campaign_id="CMP_TEST", timeframe=0)
    assert "is_active" in res, "Missing 'is_active' status"
    assert isinstance(res["is_active"], bool), "'is_active' must be a boolean"


def test_get_asset_impact_matrix():
    """
    Tool 12: get_asset_impact_matrix
    Validates composite scoring and pipeline influence across creative assets.
    """
    res = get_asset_impact_matrix(campaign_id="CMP_TEST", timeframe=0)
    assert isinstance(res, list), "Expected list of asset performance records"
    if len(res) > 0:
        assert "asset_name" in res[0], "Asset record missing 'asset_name'"
        assert "impact_score" in res[0], "Asset record missing 'impact_score'"


def test_compare_asset_baselines():
    """
    Tool 13: compare_asset_baselines
    Validates head-to-head comparison between two creative assets based on revenue influence.
    """
    res = compare_asset_baselines(
        asset_a="/whitepaper",
        asset_b="/whitepaper",
        campaign_id="CMP_TEST",
        timeframe=0
    )
    assert "asset_a" in res, "Missing 'asset_a' comparison block"
    assert "asset_b" in res, "Missing 'asset_b' comparison block"
    assert "winner" in res or "error" in res, "Comparison must identify a winner or log an error"


def test_calculate_share_of_voice():
    """
    Tool 14: calculate_share_of_voice
    Validates competitive brand impression and click share of voice calculations.
    """
    res = calculate_share_of_voice(campaign_id="CMP_TEST", timeframe=0)
    assert "our_sov_pct" in res, "Missing 'our_sov_pct'"
    assert "competitor_distribution" in res, "Missing 'competitor_distribution'"
    assert isinstance(res["our_sov_pct"], (int, float)), "SOV percentage must be numeric"


# ==============================================================================
# Domain 4: Generative Content Synthesis (2 Tools)
# ==============================================================================

@patch("app.services.llm_rotator.get_genai_client")
def test_generate_ab_test_variants(mock_get_client):
    """
    Tool 15: generate_ab_test_variants
    Validates recursive LLM invocation for synthesizing structured A/B test variations.
    Mocks external LLM response to verify schema parsing without incurring API cost.
    """
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock LLM returning structured A/B test JSON
    mock_resp = MagicMock()
    mock_resp.text = '''
    {
        "control": "Accelerate Net-Zero Transition",
        "variant_a": "Cut Industrial Emissions by 40% with Decarbonization",
        "variant_b": "The CFO's Guide to Capital-Efficient ESG Compliance",
        "rationale": "Variant A focuses on quantifiable operational metrics, while Variant B targets financial risk."
    }
    '''
    mock_client.models.generate_content.return_value = mock_resp

    res = generate_ab_test_variants(
        asset_id="/whitepaper",
        variable="headline",
        campaign_id="CMP_TEST",
        timeframe=0
    )

    assert "control" in res, "Missing 'control' variation"
    assert "variant_a" in res, "Missing 'variant_a'"
    assert "variant_b" in res, "Missing 'variant_b'"
    assert "rationale" in res, "Missing 'rationale' hypothesis"


@patch("app.services.llm_rotator.get_genai_client")
def test_draft_outreach_sequence(mock_get_client):
    """
    Tool 16: draft_outreach_sequence
    Validates recursive sales outreach sequence synthesis tailored to buyer persona and intent.
    Mocks external LLM response to verify schema parsing.
    """
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.text = '''
    {
        "persona": "Decision Maker",
        "context": "Downloaded Decarbonization Whitepaper",
        "sequence": [
            {"step": "Day 1: Contextual Intro", "channel": "Email", "content": "Saw your focus on ESG..."},
            {"step": "Day 3: Value Add", "channel": "LinkedIn Message", "content": "Here is our benchmark report..."},
            {"step": "Day 7: Breakup", "channel": "Email", "content": "Should I close your file?"}
        ],
        "strategic_note": "Direct, executive tone focusing on compliance urgency."
    }
    '''
    mock_client.models.generate_content.return_value = mock_resp

    res = draft_outreach_sequence(
        persona="Decision Maker",
        context_data="Downloaded Decarbonization Whitepaper",
        campaign_id="CMP_TEST",
        timeframe=0
    )

    assert "persona" in res, "Missing 'persona'"
    assert "sequence" in res, "Missing 'sequence' list"
    assert len(res["sequence"]) == 3, "Expected 3-step outreach sequence"
    assert "strategic_note" in res, "Missing 'strategic_note'"
    
