"""
MCP Tools Package

Modular domain packages exporting all 16 Model Context Protocol analytical functions.
"""

from .financial import (
    calculate_blended_cpa,
    simulate_budget_shift,
    get_executive_pipeline_kpis,
    get_budget_pacing,
    run_attribution_model,
)

from .abm_audience import (
    get_account_penetration,
    get_tam_penetration,
    map_buying_committee,
    get_intent_surge_signals,
    get_user_journey,
)

from .asset_performance import (
    evaluate_trickle_threshold,
    get_asset_impact_matrix,
    compare_asset_baselines,
    calculate_share_of_voice,
)

from .generative import (
    generate_ab_test_variants,
    draft_outreach_sequence,
)

__all__ = [
    # Financial Tools
    "calculate_blended_cpa",
    "simulate_budget_shift",
    "get_executive_pipeline_kpis",
    "get_budget_pacing",
    "run_attribution_model",
    # ABM & Audience Tools
    "get_account_penetration",
    "get_tam_penetration",
    "map_buying_committee",
    "get_intent_surge_signals",
    "get_user_journey",
    # Asset Performance Tools
    "evaluate_trickle_threshold",
    "get_asset_impact_matrix",
    "compare_asset_baselines",
    "calculate_share_of_voice",
    # Generative Tools
    "generate_ab_test_variants",
    "draft_outreach_sequence",
]
