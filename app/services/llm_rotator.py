"""
LLM Resilience, Key Rotation & Model Context Protocol (MCP) Tool Registry

This module provides the foundational AI infrastructure for the Campaign Telemetry Engine:
1. Multi-Key Round-Robin Rotation (`KeyManager`):
   Mitigates Gemini API rate limits (HTTP 429 / RESOURCE_EXHAUSTED) by rotating across a pool
   of comma-delimited API keys in `GEMINI_API_KEYS`. Exhausted keys are automatically placed in
   a 60-second cooldown penalty box before re-entering circulation.

2. Dual-Tier Response & Telemetry Caching:
   Caches LLM responses by SHA-256 prompt hash. Uses Redis as the primary production cache
   (with 24h TTL) and falls back to a local JSON cache file (`.cache/llm_cache.json`) for dev environments.

3. SDK Abstraction & Compatibility:
   Wraps both the modern `google.genai` Client (`NewClientWrapper`) and legacy `google.generativeai`
   GenerativeModel (`LegacyModelWrapper`) with automatic response caching and quota metrics collection.

4. MCP Tool Registry:
   Maintains the canonical JSON Schema declarations (`mcp_tools`) and Python callable dispatch map
   (`tool_functions`) for all 16 analytical functions exposed to the AI Copilot.
"""

import os
import random
import time
import json
import hashlib
import redis


# ==============================================================================
# 1. Multi-Key Round-Robin Rotation & Rate Limit Resilience
# ==============================================================================

class KeyManager:
    """
    Manages a pool of Gemini API keys with round-robin dispatch and temporary cooldowns.
    When an API call receives a 429 quota exhaustion error, the key is sidelined for 60 seconds
    while subsequent requests use alternative keys in the pool.
    """
    def __init__(self):
        self.keys = []
        self.cooldowns = {} # key -> timestamp when it was exhausted
        self.current_index = 0
        self.initialized = False
        self.cooldown_period = 60 # 60 seconds penalty box
        
    def _initialize(self):
        if self.initialized:
            return
        keys_str = os.environ.get("GEMINI_API_KEYS", "")
        if not keys_str:
            keys_str = os.environ.get("GEMINI_API_KEY", "")
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.initialized = True
        
    def get_next_key(self) -> str:
        """Fetch the next available key not currently quarantined by cooldown."""
        self._initialize()
        if not self.keys:
            return ""
            
        now = time.time()
        
        # Try to find a key that is not in cooldown
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            
            # Check cooldown
            if key in self.cooldowns:
                if now - self.cooldowns[key] < self.cooldown_period:
                    continue # Still in cooldown, skip this key
                else:
                    del self.cooldowns[key] # Cooldown expired
            
            return key
            
        # If ALL keys are in cooldown, return the current index as fallback
        return self.keys[self.current_index]
        
    def mark_exhausted(self, key: str):
        """Quarantine an exhausted API key in the penalty box."""
        if key:
            self.cooldowns[key] = time.time()


_key_manager = KeyManager()

def get_random_api_key() -> str:
    """Returns the next available API key using Round-Robin and Cooldowns."""
    return _key_manager.get_next_key()

def mark_key_exhausted(key: str):
    """Places the key in a 60-second penalty box."""
    _key_manager.mark_exhausted(key)

# ==============================================================================
# 2. Dual-Tier Response & Telemetry Caching
# ==============================================================================

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "llm_cache.json")
TELEMETRY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "ai_telemetry.json")

def get_telemetry() -> dict:
    """Return lifetime total API calls and cache hit counts from the telemetry store."""
    if os.path.exists(TELEMETRY_FILE):
        try:
            with open(TELEMETRY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_calls": 0, "cache_hits": 0}

def increment_telemetry(is_cache_hit: bool = False):
    """Update and persist API invocation and cache performance metrics."""
    t = get_telemetry()
    if is_cache_hit:
        t["cache_hits"] += 1
    else:
        t["total_calls"] += 1
    try:
        os.makedirs(os.path.dirname(TELEMETRY_FILE), exist_ok=True)
        with open(TELEMETRY_FILE, 'w') as f:
            json.dump(t, f)
    except Exception:
        pass

REDIS_URL = os.getenv("REDIS_URL")
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("Successfully connected to Redis!", flush=True) 
    except Exception as e:
        print(f"Redis connection failed on startup: {e}", flush=True)
        redis_client = None

def get_cached_response(prompt: str) -> str | None:
    """Check Redis (primary) or local JSON cache (fallback) for a pre-computed response."""
    h = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    if redis_client:
        try:
            return redis_client.get(f"llm_cache:{h}")
        except Exception as e:
            print(f"Redis GET error: {e}", flush=True)
    
    # Fallback to local JSON
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                if h in cache:
                    return cache[h]
        except Exception:
            pass
    return None

def set_cached_response(prompt: str, response_text: str):
    """Store generated response in Redis (with 24h TTL) or append to local JSON cache."""
    h = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    if redis_client:
        try:
            redis_client.setex(f"llm_cache:{h}", 86400, response_text) # 24 hr cache
            return
        except Exception as e:
            print(f"Redis SET error: {e}", flush=True)
            
    # Fallback to local JSON
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except Exception:
            pass
    cache[h] = response_text
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass


# ==============================================================================
# 3. SDK Client Wrappers & Transparent Cache Interceptors
# ==============================================================================

class MockResponse:
    """Minimal duck-typed response object emulating SDK GenerateContentResponse."""
    def __init__(self, text):
        self.text = text
        self.function_calls = None
        self.candidates = []

class LegacyModelWrapper:
    """Transparent cache interceptor for the legacy google.generativeai SDK."""
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

# Cascading model fallback chain for Flash tier.
# Tries primary model first, falling back across alternative Flash models on 429/503 quota errors.
FLASH_MODEL_CHAIN: list[str] = [
    os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.8-flash"),
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]


def generate_content_with_fallback(
    contents,
    config=None,
    model_chain: list[str] = None,
    max_key_retries: int = 3,
    **kwargs
):
    """
    Executes generate_content across a cascading fallback chain of Gemini Flash models
    with automatic API key rotation on 429 (Resource Exhausted) or 503 (Overloaded) errors.

    Resilience Strategy:
      1. Tries primary model (default: gemini-3.8-flash) rotating across available API keys.
      2. If all keys hit rate limits for that model, cascades to secondary (gemini-3.6-flash).
      3. If secondary is exhausted, cascades to tertiary (gemini-3.5-flash).
    """
    from google import genai

    if model_chain is None:
        model_chain = FLASH_MODEL_CHAIN

    prompt_str = str(contents)

    # Check cache first before making any network calls
    cached = get_cached_response(prompt_str)
    if cached:
        increment_telemetry(is_cache_hit=True)
        return MockResponse(cached)

    increment_telemetry(is_cache_hit=False)

    call_kwargs = dict(kwargs)
    if config is not None:
        call_kwargs["config"] = config

    last_err = None
    for model_name in model_chain:
        for attempt in range(max_key_retries):
            api_key = get_random_api_key()
            if not api_key:
                raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
            try:
                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    **call_kwargs
                )
                if resp:
                    try:
                        if hasattr(resp, 'text') and resp.text:
                            set_cached_response(prompt_str, resp.text)
                    except Exception:
                        pass
                    return resp
            except Exception as e:
                last_err = e
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                    mark_key_exhausted(api_key)
                    print(f"[RETRY] Model '{model_name}' hit rate limit on key ...{api_key[-4:] if len(api_key)>=4 else ''}. Trying alternative key...", flush=True)
                    continue
                else:
                    # Non-quota error (e.g. invalid argument, bad prompt syntax)
                    raise e

        print(f"[FALLBACK] Model '{model_name}' exhausted quota across keys. Cascading to next Flash model in fallback chain...", flush=True)

    if last_err:
        raise last_err


class NewModelsWrapper:
    """Transparent cache interceptor for the modern google.genai SDK models service."""
    def __init__(self, models):
        self._models = models
        
    def generate_content(self, model, contents, **kwargs):
        # Create a priority cascade starting with the requested model
        chain = [model] + [m for m in FLASH_MODEL_CHAIN if m != model]
        return generate_content_with_fallback(contents=contents, model_chain=chain, **kwargs)


class NewClientWrapper:
    """Wraps google.genai.Client, injecting rotating credentials and response caching."""
    def __init__(self, client, api_key=None):
        self._client = client
        self.api_key = api_key
        self.models = NewModelsWrapper(client.models)


def get_genai_client():
    """Returns a wrapped client for the new SDK (google-genai) using a managed key."""
    from google import genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    client = genai.Client(api_key=api_key)
    return NewClientWrapper(client, api_key)


def get_legacy_generative_model(model_name="gemini-3.6-flash"):

    """Returns a wrapped model for the old SDK (google.generativeai) using a random key."""
    import google.generativeai as genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    
    # Configure the global genai module with the randomly selected key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    return LegacyModelWrapper(model)


# ==============================================================================
# 4. Model Context Protocol (MCP) Tool Declarations & Dispatch Registry
# ==============================================================================

# Canonical analytical tools exported to the LLM agent via Gemini Function Declarations.
# Each schema precisely specifies argument types and business descriptions so the model
# can plan multi-turn reasoning steps autonomously.
from app.services.analytics import (
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
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_account_penetration",
        "description": "Returns AGGREGATE company-level engagement data grouped by company name and user seniority across all contacts. Use this to understand which companies are engaged with a campaign at a macro level. Do NOT use this tool to look up an individual person — for individual person queries (e.g. 'What is X interested in?', 'What has Y done?'), use get_user_journey instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": []
        }
    },
    {
        "name": "evaluate_trickle_threshold",
        "description": "Evaluates if the campaign is currently active or past based on the Trickle Threshold Algorithm (95% drop sustained for 7 days).",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
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
                    "type": "string",
                    "description": "The new proposed budget amount in dollars (e.g., '100000'), or the exact string 'REMAINING_BUDGET' to dynamically simulate shifting the exact remaining unspent budget across all channels."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "channel",
                "budget"
            ]
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
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "campaign_id"
            ]
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
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "campaign_id"
            ]
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
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
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "asset_a",
                "asset_b"
            ]
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "account_identifier"
            ]
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "account_identifier"
            ]
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
            "required": [
                "campaign_id"
            ]
        }
    },
    {
        "name": "get_user_journey",
        "description": "Returns the chronological, cross-channel touchpoints (interactions) of a specific named lead. Use this as the FIRST tool whenever a user asks about a specific person — e.g. 'What topics is [Name] interested in?', 'What has [Name] done?', 'Investigate [Name]'. Requires the person's full name and company. If the company is not provided by the user, you may infer it from context or ask the user before calling this tool.",
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "name",
                "company"
            ]
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "asset_id",
                "variable"
            ]
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
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to scope the metrics."
                },
                "timeframe": {
                    "type": "integer",
                    "description": "Optional timeframe in days."
                }
            },
            "required": [
                "persona",
                "context_data"
            ]
        }
    }
]

# Tool Registry (Strategy Pattern):
# Maps tool names received from Gemini FunctionCall responses directly to their
# corresponding executable Python service implementations in analytics.py.
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

