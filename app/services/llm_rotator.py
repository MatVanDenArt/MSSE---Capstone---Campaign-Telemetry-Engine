import os
import random

def get_random_api_key() -> str:
    """Returns a random API key from the GEMINI_API_KEYS environment variable."""
    keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_str:
        # Fallback to single key env var, which might also contain commas
        keys_str = os.environ.get("GEMINI_API_KEY", "")
    
    # Split by comma and remove empty strings/whitespace
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        return ""
        
    return random.choice(keys)

import json
import hashlib

CACHE_FILE = "C:\\Users\\mpser\\Downloads\\Quantic\\Capstone\\llm_cache.json"
TELEMETRY_FILE = "C:\\Users\\mpser\\Downloads\\Quantic\\Capstone\\ai_telemetry.json"

def get_telemetry():
    if os.path.exists(TELEMETRY_FILE):
        try:
            with open(TELEMETRY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"total_calls": 0, "cache_hits": 0}

def increment_telemetry(is_cache_hit=False):
    t = get_telemetry()
    if is_cache_hit:
        t["cache_hits"] += 1
    else:
        t["total_calls"] += 1
    with open(TELEMETRY_FILE, 'w') as f:
        json.dump(t, f)

def get_cached_response(prompt: str):
    h = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                if h in cache:
                    return cache[h]
        except:
            pass
    return None

def set_cached_response(prompt: str, response_text: str):
    h = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except:
            pass
    cache[h] = response_text
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

class MockResponse:
    def __init__(self, text):
        self.text = text

class LegacyModelWrapper:
    def __init__(self, model):
        self._model = model
    
    def generate_content(self, contents, **kwargs):
        prompt = str(contents)
        cached = get_cached_response(prompt)
        if cached:
            increment_telemetry(is_cache_hit=True)
            return MockResponse(cached)
            
        increment_telemetry(is_cache_hit=False)
        resp = self._model.generate_content(contents, **kwargs)
        set_cached_response(prompt, resp.text)
        return resp

class NewModelsWrapper:
    def __init__(self, models):
        self._models = models
        
    def generate_content(self, model, contents, **kwargs):
        prompt = str(contents)
        cached = get_cached_response(prompt)
        if cached:
            increment_telemetry(is_cache_hit=True)
            return MockResponse(cached)
            
        increment_telemetry(is_cache_hit=False)
        resp = self._models.generate_content(model=model, contents=contents, **kwargs)
        set_cached_response(prompt, resp.text)
        return resp

class NewClientWrapper:
    def __init__(self, client):
        self._client = client
        self.models = NewModelsWrapper(client.models)

def get_genai_client():
    """Returns a wrapped client for the new SDK (google-genai) using a random key."""
    from google import genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    client = genai.Client(api_key=api_key)
    return NewClientWrapper(client)

def get_legacy_generative_model(model_name="gemini-3.5-flash"):
    """Returns a wrapped model for the old SDK (google.generativeai) using a random key."""
    import google.generativeai as genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    
    # Configure the global genai module with the randomly selected key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    return LegacyModelWrapper(model)

from app.services.analytics_v2 import (
    calculate_blended_cpa,
    get_account_penetration,
    evaluate_trickle_threshold,
    simulate_budget_shift,
    get_tam_penetration,
    calculate_share_of_voice,
    get_executive_pipeline_kpis,
    get_budget_pacing,
    run_attribution_model,
    compare_asset_baselines,
    map_buying_committee,
    get_intent_surge_signals,
    get_asset_impact_matrix,
    get_user_journey,
    generate_ab_test_variants,
    draft_outreach_sequence
)

mcp_tools = [
    {
        "name": "calculate_blended_cpa",
        "description": "Calculates the blended Cost Per Acquisition (CPA) by dividing total LinkedIn spend by total CRM Closed Won opportunities.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_account_penetration",
        "description": "Retrieves the account penetration grouped by company name and user seniority level.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "evaluate_trickle_threshold",
        "description": "Evaluates if the campaign is currently active or past based on the Trickle Threshold Algorithm (95% drop sustained for 7 days).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "simulate_budget_shift",
        "description": "Simulates the projected pipeline value if the budget for a specific channel is shifted.",
        "parameters": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "The marketing channel to simulate (e.g., 'linkedin')."
                },
                "budget": {
                    "type": "number",
                    "description": "The new proposed budget amount in dollars."
                }
            },
            "required": ["channel", "budget"]
        }
    },
    {
        "name": "get_tam_penetration",
        "description": "Mock calculation for Target Account Penetration scoped to a campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The ID of the campaign."
                }
            },
            "required": ["campaign_id"]
        }
    },
    {
        "name": "calculate_share_of_voice",
        "description": "Mock calculation for Topic Share of Voice (SOV) against competitors.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The ID of the campaign."
                }
            },
            "required": ["campaign_id"]
        }
    },
    {
        "name": "get_executive_pipeline_kpis",
        "description": "Query CRM for top-level ROI and Pipeline KPIs.",
        "parameters": {
            "type": "object",
            "properties": {
                "timeframe": {
                    "type": "integer",
                    "description": "Number of days to look back. 0 means all time."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_budget_pacing",
        "description": "Query spend data vs. pipeline creation.",
        "parameters": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel to check pacing for, default is all."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID to filter by."
                }
            },
            "required": []
        }
    },
    {
        "name": "run_attribution_model",
        "description": "Distribute pipeline credit across touches (e.g., linear model).",
        "parameters": {
            "type": "object",
            "properties": {
                "model_type": {
                    "type": "string",
                    "description": "The attribution model to use (e.g., 'linear', 'first_touch')."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Timeframe in days."
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_asset_baselines",
        "description": "Compare performance between two specific assets.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_a": {
                    "type": "string",
                    "description": "Name or URL of the first asset."
                },
                "asset_b": {
                    "type": "string",
                    "description": "Name or URL of the second asset."
                }
            },
            "required": ["asset_a", "asset_b"]
        }
    },
    {
        "name": "map_buying_committee",
        "description": "Map the buying committee and engagement levels for a specific account.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_identifier": {
                    "type": "string",
                    "description": "The name of the company or account (e.g., 'Shell', 'BP')."
                }
            },
            "required": ["account_identifier"]
        }
    },
    {
        "name": "get_intent_surge_signals",
        "description": "Identify intent surge signals across an account in the last 48 hours.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_identifier": {
                    "type": "string",
                    "description": "The name of the company or account."
                }
            },
            "required": ["account_identifier"]
        }
    },
    {
        "name": "get_asset_impact_matrix",
        "description": "Get the impact matrix for all assets in a campaign, including fatigue and engagement scores.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The campaign ID to fetch the matrix for."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Timeframe in days, default is 0."
                }
            },
            "required": ["campaign_id"]
        }
    }
,
    {
        "name": "get_user_journey",
        "description": "Returns the chronological, cross-channel touchpoints (interactions) of a specific lead.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The full name of the user, e.g., 'Kathleen Harris'"
                },
                "company": {
                    "type": "string",
                    "description": "The company the user works for, e.g., 'Petrobras'"
                }
            },
            "required": ["name", "company"]
        }
    },
    {
        "name": "generate_ab_test_variants",
        "description": "Generate A/B test variations for a specific asset and variable.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "The name or ID of the asset."
                },
                "variable": {
                    "type": "string",
                    "description": "The variable to test, e.g., 'Subject Line', 'Hero Copy'."
                }
            },
            "required": ["asset_id", "variable"]
        }
    },
    {
        "name": "draft_outreach_sequence",
        "description": "Draft a multi-step outreach sequence tailored to a persona based on interaction context.",
        "parameters": {
            "type": "object",
            "properties": {
                "persona": {
                    "type": "string",
                    "description": "The target persona (e.g., 'C-Suite Executive')."
                },
                "context_data": {
                    "type": "string",
                    "description": "The context or reason for outreach (e.g., 'High intent on Digital Twin Insights')."
                }
            },
            "required": ["persona", "context_data"]
        }
    }
]

tool_functions = {
    "calculate_blended_cpa": calculate_blended_cpa,
    "get_account_penetration": get_account_penetration,
    "evaluate_trickle_threshold": evaluate_trickle_threshold,
    "simulate_budget_shift": simulate_budget_shift,
    "get_tam_penetration": get_tam_penetration,
    "calculate_share_of_voice": calculate_share_of_voice,
    "get_executive_pipeline_kpis": get_executive_pipeline_kpis,
    "get_budget_pacing": get_budget_pacing,
    "run_attribution_model": run_attribution_model,
    "compare_asset_baselines": compare_asset_baselines,
    "map_buying_committee": map_buying_committee,
    "get_intent_surge_signals": get_intent_surge_signals,
    "get_asset_impact_matrix": get_asset_impact_matrix,
    "get_user_journey": get_user_journey,
    "generate_ab_test_variants": generate_ab_test_variants,
    "draft_outreach_sequence": draft_outreach_sequence
}
