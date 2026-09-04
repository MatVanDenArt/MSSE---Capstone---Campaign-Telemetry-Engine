import os
import sys
import json
import time
import re
from textwrap import dedent
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.analytics import (
    get_db_connection,
    calculate_blended_cpa, get_account_penetration, evaluate_trickle_threshold,
    simulate_budget_shift, get_tam_penetration, calculate_share_of_voice,
    get_executive_pipeline_kpis, get_budget_pacing, run_attribution_model,
    compare_asset_baselines, map_buying_committee, get_intent_surge_signals,
    get_asset_impact_matrix, get_user_journey, generate_ab_test_variants,
    draft_outreach_sequence
)
from app.services.llm_rotator import get_genai_client, mark_key_exhausted

# --- CONFIGURATION ---
# Sub-sampled Matrix to stay well within free tier limits
MATRIX_CAMPAIGNS = ["CMP_LIVE_DECARBONIZATION_25_26"]
MATRIX_TIMEFRAMES = [30, 90]
MATRIX_TOOLS = [
    {"name": "get_executive_pipeline_kpis", "func": get_executive_pipeline_kpis, "kwargs": {}},
    {"name": "simulate_budget_shift", "func": simulate_budget_shift, "kwargs": {"channel": "linkedin", "budget": "REMAINING_BUDGET"}},
    {"name": "draft_outreach_sequence", "func": draft_outreach_sequence, "kwargs": {"persona": "CMO", "context_data": "High intent on sustainability"}},
    {"name": "calculate_blended_cpa", "func": calculate_blended_cpa, "kwargs": {}},
    {"name": "get_account_penetration", "func": get_account_penetration, "kwargs": {"account_identifier": "Acme Corp"}},
    {"name": "evaluate_trickle_threshold", "func": evaluate_trickle_threshold, "kwargs": {}},
    {"name": "get_tam_penetration", "func": get_tam_penetration, "kwargs": {}},
    {"name": "calculate_share_of_voice", "func": calculate_share_of_voice, "kwargs": {}},
    {"name": "get_budget_pacing", "func": get_budget_pacing, "kwargs": {"channel": "all"}},
    {"name": "run_attribution_model", "func": run_attribution_model, "kwargs": {"model_type": "w_shaped"}},
    {"name": "compare_asset_baselines", "func": compare_asset_baselines, "kwargs": {"asset_a": "/whitepaper-download", "asset_b": "/contact-sales"}},
    {"name": "map_buying_committee", "func": map_buying_committee, "kwargs": {"account_identifier": "DYNAMIC_ACCOUNT"}},
    {"name": "get_intent_surge_signals", "func": get_intent_surge_signals, "kwargs": {"account_identifier": "DYNAMIC_ACCOUNT"}},
    {"name": "get_asset_impact_matrix", "func": get_asset_impact_matrix, "kwargs": {"asset_type": "Web"}},
    {"name": "get_user_journey", "func": get_user_journey, "kwargs": {"name": "DYNAMIC_USER", "company": "DYNAMIC_ACCOUNT"}},
    {"name": "generate_ab_test_variants", "func": generate_ab_test_variants, "kwargs": {"asset_id": "landing_page_1", "variable": "headline"}}
]


def get_dynamic_test_data(campaign_id: str) -> dict:
    '''Dynamically queries the database for a valid user and account in this campaign context.'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get a valid company name
        cursor.execute('''
            SELECT DISTINCT c.company_name 
            FROM crm_users c 
            JOIN ga4_events g ON c.user_id = g.user_id
            WHERE g.utm_campaign = ? LIMIT 1
        ''', (campaign_id,))
        company_row = cursor.fetchone()
        company = company_row[0] if company_row else "Acme Corp"
        
        # Get a valid user name
        cursor.execute('''
            SELECT DISTINCT c.first_name || ' ' || c.last_name 
            FROM crm_users c 
            JOIN ga4_events g ON c.user_id = g.user_id
            WHERE g.utm_campaign = ? LIMIT 1
        ''', (campaign_id,))
        user_row = cursor.fetchone()
        user = user_row[0] if user_row else "Test User"
        
        return {"account_identifier": company, "company": company, "name": user}
    except Exception as e:
        print("Warning: Dynamic fetch failed, falling back to dummy data.", e)
        return {"account_identifier": "Acme Corp", "company": "Acme Corp", "name": "Test User"}

def heuristic_sparsity_score(data) -> int:
    """Zero-cost Python evaluation for data sparsity. 1-5 scale."""
    if not data or "error" in data:
        return 1
    
    score = 5
    empty_vals = 0
    total_vals = 0
    
    if isinstance(data, dict):
        for k, v in data.items():
            total_vals += 1
            if v in [0, 0.0, "", None, [], {}]:
                empty_vals += 1
                
    if total_vals > 0:
        sparsity_ratio = empty_vals / total_vals
        if sparsity_ratio > 0.8: score = 2
        elif sparsity_ratio > 0.5: score = 3
        elif sparsity_ratio > 0.2: score = 4
        
    return score

def llm_judge_score(tool_name: str, raw_output: dict):
    """Uses LLM-as-a-Judge to score relevance and actionability with rate limit protection."""
    prompt = dedent(f"""
        You are an expert Data Analytics Evaluator. 
        I am going to provide you the JSON output of a Marketing AI tool named `{tool_name}`.
        
        Evaluate the payload on two metrics from 1-5:
        1. Actionability (5 = An executive could easily make a financial decision based on this)
        2. Contextual Relevance (5 = This strictly answers the intent of the tool with no noise)
        
        Provide the output as valid JSON: {{"actionability": <int>, "relevance": <int>, "reasoning": "<string>"}}
        
        TOOL OUTPUT:
        {json.dumps(raw_output, indent=2)}
    """)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_genai_client()
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            text = response.text
            
            # Extract JSON
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"actionability": 1, "relevance": 1, "reasoning": "Failed to parse JSON"}
            
        except Exception as e:
            if "429" in str(e) or "Resource exhausted" in str(e):
                print(f"    [Rate Limit Hit] Sleeping for 20 seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(20) # Exponential backoff safeguard
            else:
                return {"actionability": 1, "relevance": 1, "reasoning": f"Exception: {str(e)}"}
                
    return {"actionability": 1, "relevance": 1, "reasoning": "Rate limit exhausted completely."}

def main():
    print("Starting AI Evals Matrix Testing (Sprint 2)...")
    
    results = []
    
    for tool in MATRIX_TOOLS:
        for camp in MATRIX_CAMPAIGNS:
            for tf in MATRIX_TIMEFRAMES:
                print(f"Evaluating {tool['name']} for {camp} ({tf} days)...")
                
                # 1. Execute Tool locally (Zero Cost)
                kwargs = tool["kwargs"].copy()
                kwargs["campaign_id"] = camp
                kwargs["timeframe"] = tf
                
                # Inject dynamic mock data if requested
                dyn_data = get_dynamic_test_data(camp)
                for k, v in kwargs.items():
                    if v == "DYNAMIC_ACCOUNT":
                        kwargs[k] = dyn_data.get("company", "Acme Corp")
                    elif v == "DYNAMIC_USER":
                        kwargs[k] = dyn_data.get("name", "Test User")
                
                start_time = time.time()
                try:
                    data = tool["func"](**kwargs)
                    exec_time = time.time() - start_time
                except Exception as e:
                    data = {"error": str(e)}
                    exec_time = 0
                    
                # 2. Heuristic Scoring (Zero Cost)
                sparsity = heuristic_sparsity_score(data)
                
                # 3. LLM Judge Scoring (Network Cost)
                llm_scores = llm_judge_score(tool["name"], data)
                
                results.append({
                    "tool": tool["name"],
                    "campaign": camp,
                    "timeframe": tf,
                    "sparsity": sparsity,
                    "actionability": llm_scores.get("actionability", 1),
                    "relevance": llm_scores.get("relevance", 1),
                    "reasoning": llm_scores.get("reasoning", ""),
                    "exec_ms": round(exec_time * 1000, 2)
                })
                
                time.sleep(1) # Base throttle to prevent hammering the rotator
                
    # Generate Report
    report = ["# AI Evals & Scoring Report\n"]
    report.append("> Generated by Matrix Evaluation Harness\n")
    
    report.append("| Tool | Timeframe | Sparsity | Actionability | Relevance | Exec Time | Notes |")
    report.append("|---|---|---|---|---|---|---|")
    
    for r in results:
        notes = r['reasoning'].replace('\n', ' ')
        
        report.append(f"| `{r['tool']}` | {r['timeframe']}d | {r['sparsity']}/5 | {r['actionability']}/5 | {r['relevance']}/5 | {r['exec_ms']}ms | {notes} |")
        
    artifact_path = os.path.join(os.path.dirname(__file__), '..', 'ai_evals_report.md')
    with open(artifact_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Matrix Evaluation Complete! Report saved to {artifact_path}")

if __name__ == "__main__":
    main()
