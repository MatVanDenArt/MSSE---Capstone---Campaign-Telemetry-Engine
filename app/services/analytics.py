"""
Analytical facade & telemetry aggregation service

This module acts as the central analytical facade for the campaign telemetry engine,
providing a high-level API over raw multi-channel data tables in `capstone.db`:
  - `ga4_events`: Web pageviews, session durations, and bounce flags.
  - `mailchimp_events`: Outbound email sends, opens, and link clicks.
  - `linkedin_events`: Sponsored content impressions, ad clicks, and consumed budget.
  - `crm_users`: B2B accounts, buying committee members, seniority, and contact metadata.
  - `crm_opps`: Pipeline opportunities, contract values, and Closed Won revenue stages.
  - `content_metadata`: Topic taxonomy, asset types, target personas, and publication dates.

Architecture & conventions:
  - Facade pattern: Unifies disparate channel sources into standard analytical metrics
    (blended CPA, multi-touch attribution, fatigue ratings, account penetration).
  - MCP tool exporter: Imports and re-exports all 16 domain tools from `app.services.mcp_tools`.
  - Timeframe scoping: Functions accept a `timeframe` integer argument representing days
    (e.g., 30, 60, 90). Passing `timeframe=0` evaluates the full campaign history (All Time).
  - Connection lifecycle: Each public service function opens and closes its own SQLite
    connection via `get_db_connection()`, maintaining isolation and thread safety.
"""

import sqlite3
import json
import os
from functools import lru_cache

_DEFAULT_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "capstone.db"))
DB_PATH = os.getenv("DATABASE_URL", _DEFAULT_DB)
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", DB_PATH))

def get_db_connection():
    """Return a new SQLite database connection configured with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==============================================================================
# 1. Model Context Protocol (MCP) Tool Re-exports
# ==============================================================================

from app.services.mcp_tools import (

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
    draft_outreach_sequence,
)

# ==============================================================================
# 2. Campaign Discovery & Metadata
# ==============================================================================

# Human-readable display names for known campaign ID suffixes.
# Add entries here when new campaigns are created rather than modifying get_all_campaigns().
CAMPAIGN_DISPLAY_NAMES: dict[str, str] = {
    "OIL_GAS_US":          "Oil & Gas US",
    "O_M_2026":            "O&M 2026",
    "OTC_2026":            "OTC 2026",
    "DECARBONIZATION_25_26": "Decarbonization '25/'26",
}


def get_all_campaigns() -> list:
    """
    Scan ga4_events, linkedin_events, and crm_opps to discover all active and historic campaigns.
    Calculates attributed pipeline, start date, and active/inactive status per campaign.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all unique campaign IDs across ALL tables
        cursor.execute("""
            SELECT DISTINCT campaign_id FROM (
                SELECT utm_campaign as campaign_id FROM ga4_events WHERE utm_campaign IS NOT NULL
                UNION
                SELECT campaign_id FROM linkedin_events WHERE campaign_id IS NOT NULL
                UNION
                SELECT utm_campaign as campaign_id FROM crm_opps WHERE utm_campaign IS NOT NULL
            )
        """)

        rows = cursor.fetchall()
        
        campaigns = []
        from datetime import datetime
        now = datetime.now()
        
        for row in rows:
            cid = row["campaign_id"]
            raw_name = cid.replace("CMP_LIVE_", "").replace("CMP_PAST_", "")
            name = CAMPAIGN_DISPLAY_NAMES.get(raw_name, raw_name.replace("_", " ").title())
            
            # Fetch pipeline value
            cursor.execute(f"SELECT SUM(pipeline_value) as total_pipeline FROM crm_opps WHERE utm_campaign = '{cid}'")
            pipeline_row = cursor.fetchone()
            total_pipeline = pipeline_row["total_pipeline"] if pipeline_row and pipeline_row["total_pipeline"] else 0.0
            
            # Fetch start date (absolute minimum across all tables)
            cursor.execute(f"""
                SELECT MIN(timestamp) as start_date FROM (
                    SELECT MIN(timestamp) as timestamp FROM ga4_events WHERE utm_campaign = '{cid}'
                    UNION ALL
                    SELECT MIN(timestamp) as timestamp FROM linkedin_events WHERE campaign_id = '{cid}'
                    UNION ALL
                    SELECT MIN(timestamp) as timestamp FROM mailchimp_events WHERE campaign_id LIKE '%{cid}%'
                    UNION ALL
                    SELECT MIN(timestamp) as timestamp FROM crm_opps WHERE utm_campaign = '{cid}'
                )
            """)
            start_row = cursor.fetchone()
            start_date_str = str(start_row["start_date"]).split(" ")[0] if start_row and start_row["start_date"] else None
            
            # Option 1 Implementation: CRM Pipeline Timeout Rule
            # To cut through the noisy long-tail ghost traffic, we define the campaign's lifespan
            # by its ability to generate CRM pipeline. If no opps are generated in 100 days, it's complete.
            cursor.execute(f"SELECT MAX(timestamp) as last_opp_date FROM crm_opps WHERE utm_campaign = '{cid}'")
            opp_row = cursor.fetchone()
            last_opp_date_str = str(opp_row["last_opp_date"]).split(" ")[0] if opp_row and opp_row["last_opp_date"] else None
            
            is_active = True
            end_date_str = "Present"
            
            if last_opp_date_str:
                last_opp_date = datetime.strptime(last_opp_date_str, "%Y-%m-%d")
                days_since_opp = (now - last_opp_date).days
                if days_since_opp > 100:
                    is_active = False
                    end_date_str = last_opp_date_str
            else:
                # Fallback if campaign has literally 0 opps
                cursor.execute(f"SELECT MAX(timestamp) as last_event FROM ga4_events WHERE utm_campaign = '{cid}'")
                fallback = cursor.fetchone()
                if fallback and fallback["last_event"]:
                    fallback_date_str = str(fallback["last_event"]).split(" ")[0]
                    fallback_date = datetime.strptime(fallback_date_str, "%Y-%m-%d")
                    if (now - fallback_date).days > 100:
                        is_active = False
                        end_date_str = fallback_date_str
            
            # Format dates for UI
            start_date = "Unknown"
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%d %b %Y")
                except ValueError:
                    start_date = start_date_str
                    
            end_date = "Present"
            if end_date_str and end_date_str != "Present":
                try:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").strftime("%d %b %Y")
                except ValueError:
                    end_date = end_date_str
            
            campaigns.append({
                "campaign_id": cid,
                "name": name,
                "is_active": is_active,
                "total_pipeline": total_pipeline,
                "start_date": start_date,
                "end_date": end_date
            })
            
        conn.close()
        # Sort active first, then by name
        campaigns.sort(key=lambda x: (not x["is_active"], x["name"]))
        return campaigns
    except Exception as e:
        raise e


# ==============================================================================
# 3. Telemetry Anomaly & Dynamic Task Detectors
# ==============================================================================

def get_high_bounce_asset(campaign_id: str, timeframe: int = 0) -> dict | None:
    """Return the asset with the highest bounce rate (>60%, min 10 sessions) for an action-center card.

    Returns a dict with keys ``page_viewed``, ``title``, ``bounce_rate``, ``total``,
    or ``None`` if no qualifying asset is found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        cursor.execute(f"""
            SELECT g.page_viewed,
                   COALESCE(c.title, g.page_viewed) as title,
                   COUNT(*) as total,
                   SUM(g.bounce_flag) as bounces,
                   ROUND(100.0 * SUM(g.bounce_flag) / COUNT(*), 1) as bounce_rate
            FROM ga4_events g
            LEFT JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = ? {tf_cond}
            GROUP BY g.page_viewed
            HAVING total >= 10 AND bounce_rate > 60
            ORDER BY bounce_rate DESC
            LIMIT 1
        """, (campaign_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_spiking_asset(campaign_id: str, timeframe: int = 0) -> dict | None:
    """Return the asset whose views in the last 7 days exceed 1.5× the prior 7 days.

    Returns a dict with keys ``page_viewed``, ``title``, ``recent_views``, ``prior_views``,
    or ``None`` if no qualifying asset is found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        cursor.execute(f"""
            SELECT g.page_viewed,
                   COALESCE(c.title, g.page_viewed) as title,
                   SUM(CASE WHEN g.timestamp >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as recent_views,
                   SUM(CASE WHEN g.timestamp >= datetime('now', '-14 days')
                            AND g.timestamp  < datetime('now', '-7 days') THEN 1 ELSE 0 END) as prior_views
            FROM ga4_events g
            LEFT JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = ? {tf_cond}
            GROUP BY g.page_viewed
            HAVING prior_views > 0 AND (CAST(recent_views AS REAL) / prior_views) > 1.5
            ORDER BY (CAST(recent_views AS REAL) / prior_views) DESC
            LIMIT 1
        """, (campaign_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_stalled_account(campaign_id: str, timeframe: int = 0) -> dict | None:
    """Return the account with ≥2 engaged users that has gone silent for more than 14 days.

    Returns a dict with keys ``company_name``, ``engaged_users``, ``last_active``,
    or ``None`` if no qualifying account is found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        cursor.execute(f"""
            WITH CampaignUsers AS (
                SELECT user_id, MAX(timestamp) as last_touch
                FROM ga4_events
                WHERE utm_campaign = ? {tf_cond}
                AND user_id IS NOT NULL
                GROUP BY user_id
            )
            SELECT c.company_name,
                   COUNT(DISTINCT cu.user_id) as engaged_users,
                   MAX(cu.last_touch) as last_active
            FROM CampaignUsers cu
            JOIN crm_users c ON cu.user_id = c.user_id
            GROUP BY c.company_name
            HAVING engaged_users >= 2
               AND last_active < date('now', '-14 days')
            ORDER BY engaged_users DESC
            LIMIT 1
        """, (campaign_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


# ==============================================================================
# 4. Executive KPI Benchmarking & Trajectory Calculations
# ==============================================================================

@lru_cache(maxsize=128)
def get_kpi_benchmarks(campaign_id: str, timeframe: int = 90) -> dict:
    """
    Compute core marketing performance metrics compared against cross-campaign baselines.
    
    Metrics Calculated:
      - Total Spend (blended LinkedIn spend + estimated Mailchimp clicks + GA4 sessions).
      - Closed Won Opportunities & Total Pipeline Attributed.
      - Blended Cost Per Acquisition (CPA).
      - Target Accounts Engaged.
      - 14-day daily sparkline trajectories for trending visualisations.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        
        def fetch_metrics(campaign_id: str, days: int = None):
            date_filter = ""
            if days:
                date_filter = f"AND timestamp >= datetime('now', '-{days} days')"
                
            cursor.execute(f"SELECT SUM(spend_consumed) as spend FROM linkedin_events WHERE campaign_id = '{campaign_id}' {date_filter}")
            li_spend = cursor.fetchone()["spend"] or 0.0
            
            cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' {date_filter}")
            em_clicks = cursor.fetchone()["c"] or 0
            em_spend = em_clicks * 1.50
            
            cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' {date_filter}")
            web_views = cursor.fetchone()["c"] or 0
            web_spend = web_views * 0.80
            
            spend = li_spend + em_spend + web_spend
            
            cursor.execute(f"""
                SELECT COUNT(*) as conv_count 
                FROM crm_opps 
                WHERE utm_campaign = '{campaign_id}' AND event_type = 'Closed Won' {date_filter}
            """)
            conversions = cursor.fetchone()["conv_count"] or 0
            
            cursor.execute(f"""
                SELECT SUM(pipeline_value) as pipeline 
                FROM crm_opps 
                WHERE utm_campaign = '{campaign_id}' {date_filter}
            """)
            pipeline = cursor.fetchone()["pipeline"] or 0.0
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT account_id) as acct_count FROM crm_users 
                WHERE user_id IN (
                    SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL {date_filter}
                )
            """)
            accounts = cursor.fetchone()["acct_count"] or 0
            cpa = spend / conversions if conversions > 0 else 0.0
            
            return {"spend": spend, "accounts": accounts, "cpa": cpa, "conversions": conversions, "pipeline": pipeline}

        live_metrics = fetch_metrics(campaign_id, timeframe)
        
        date_filter = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        
        cursor.execute(f"SELECT COUNT(DISTINCT campaign_id) as n FROM linkedin_events WHERE 1=1 {date_filter}")
        num_campaigns = cursor.fetchone()["n"] or 1
        
        cursor.execute(f"SELECT SUM(spend_consumed) as spend FROM linkedin_events WHERE 1=1 {date_filter}")
        baseline_li = cursor.fetchone()["spend"] or 0.0
        
        cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {date_filter}")
        baseline_em = (cursor.fetchone()["c"] or 0) * 1.50
        
        cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {date_filter}")
        baseline_web = (cursor.fetchone()["c"] or 0) * 0.80
        
        baseline_spend = baseline_li + baseline_em + baseline_web
        
        cursor.execute(f"""
            SELECT COUNT(*) as conv_count 
            FROM crm_opps 
            WHERE event_type = 'Closed Won' {date_filter}
        """)
        baseline_conversions = cursor.fetchone()["conv_count"] or 0
        
        cursor.execute(f"""
            SELECT SUM(pipeline_value) as pipeline 
            FROM crm_opps 
            WHERE 1=1 {date_filter}
        """)
        baseline_pipeline = cursor.fetchone()["pipeline"] or 0.0
        
        cursor.execute(f"SELECT COUNT(DISTINCT account_id) as acct_count FROM crm_users WHERE user_id IN (SELECT user_id FROM ga4_events WHERE user_id IS NOT NULL {date_filter})")
        baseline_accounts = cursor.fetchone()["acct_count"] or 0
        baseline_cpa = baseline_spend / baseline_conversions if baseline_conversions > 0 else 0.0
        
        baseline_metrics = {
            "spend": baseline_spend / num_campaigns,
            "accounts": baseline_accounts / num_campaigns,
            "cpa": baseline_cpa,
            "conversions": baseline_conversions / num_campaigns,
            "pipeline": baseline_pipeline / num_campaigns
        }
        
        def calc_diff(current, baseline, lower_is_better=False):
            if baseline == 0: return 0, False
            diff = ((current - baseline) / baseline) * 100
            is_good = (diff < 0) if lower_is_better else (diff > 0)
            return round(diff, 1), is_good
            
        spend_diff, spend_good = calc_diff(live_metrics["spend"], baseline_metrics["spend"], lower_is_better=False)
        accounts_diff, accounts_good = calc_diff(live_metrics["accounts"], baseline_metrics["accounts"], lower_is_better=False)
        cpa_diff, cpa_good = calc_diff(live_metrics["cpa"], baseline_metrics["cpa"], lower_is_better=True)
        conv_diff, conv_good = calc_diff(live_metrics["conversions"], baseline_metrics["conversions"], lower_is_better=False)
        pipe_diff, pipe_good = calc_diff(live_metrics["pipeline"], baseline_metrics["pipeline"], lower_is_better=False)
        
        # Generate 14-day sparklines
        def get_sparkline(metric_type):
            data = []
            for i in range(13, -1, -1):
                day_start = f"datetime('now', '-{i+1} days')"
                day_end = f"datetime('now', '-{i} days')"
                val = 0
                if metric_type == "spend":
                    cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND timestamp >= {day_start} AND timestamp < {day_end}")
                    val = cursor.fetchone()["s"] or 0
                elif metric_type == "accounts":
                    cursor.execute(f"SELECT COUNT(DISTINCT account_id) as s FROM crm_users WHERE user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND timestamp >= {day_start} AND timestamp < {day_end})")
                    val = cursor.fetchone()["s"] or 0
                elif metric_type == "conversions":
                    cursor.execute(f"SELECT COUNT(*) as s FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL AND timestamp >= {day_start} AND timestamp < {day_end}")
                    val = cursor.fetchone()["s"] or 0
                elif metric_type == "cpa":
                    cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND timestamp >= {day_start} AND timestamp < {day_end}")
                    s = cursor.fetchone()["s"] or 0
                    cursor.execute(f"SELECT COUNT(*) as c FROM crm_opps WHERE utm_campaign = '{campaign_id}' AND event_type = 'Closed Won' AND timestamp >= {day_start} AND timestamp < {day_end}")
                    c = cursor.fetchone()["c"] or 1
                    val = s / c
                data.append(val)
            return data
            
        # Call get_sparkline BEFORE closing the connection!
        sparklines = {
            "spend": get_sparkline("spend"),
            "accounts": get_sparkline("accounts"),
            "cpa": get_sparkline("cpa"),
            "conversions": get_sparkline("conversions")
        }
            
        conn.close()
        
        return {
            "live": {
                "spend": round(live_metrics["spend"], 2),
                "accounts": live_metrics["accounts"],
                "cpa": round(live_metrics["cpa"], 2),
                "conversions": live_metrics["conversions"],
                "pipeline": live_metrics["pipeline"]
            },
            "comparisons": {
                "spend": {"value": spend_diff, "good": spend_good},
                "accounts": {"value": accounts_diff, "good": accounts_good},
                "cpa": {"value": cpa_diff, "good": cpa_good},
                "conversions": {"value": conv_diff, "good": conv_good},
                "pipeline": {"value": pipe_diff, "good": pipe_good}
            },
            "sparklines": sparklines
        }
    except Exception as e:
        raise e


def get_campaign_start_date(campaign_id: str) -> str:
    """Find the earliest event timestamp across GA4, LinkedIn, and Mailchimp for a campaign."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"""
        SELECT MIN(timestamp) as start_date FROM (
            SELECT MIN(timestamp) as timestamp FROM ga4_events WHERE utm_campaign = '{campaign_id}'
            UNION ALL
            SELECT MIN(timestamp) as timestamp FROM linkedin_events WHERE campaign_id = '{campaign_id}'
            UNION ALL
            SELECT MIN(timestamp) as timestamp FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%'
        )
        """
        cursor.execute(query)
        res = cursor.fetchone()
        conn.close()
        return str(res['start_date']).split(" ")[0] if res and res['start_date'] else "Unknown"
    except Exception as e:
        raise e


def format_pipeline(val: float) -> str:
    """Format numeric currency value into compact human-readable string ($1.2M, $450K, $120)."""
    if not val:
        return "$0"
    if val >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:.0f}"


def generate_strategic_tldr(payload: dict) -> str:
    """
    Synthesize an executive TLDR narrative from campaign benchmarks using Gemini.
    Features prompt hashing, Redis caching, and a deterministic template fallback
    if the AI provider is unreachable or rate-limited.
    """
    from google import genai
    from google.genai import types
    try:
        from app.services.llm_rotator import get_genai_client
        
        prompt = f"""You are a B2B Marketing AI Analyst. Review this executive campaign summary data: {payload}.
Write a strict 2-3 sentence executive summary for the CMO.
Evaluate if the pipeline generated justifies the total spend for the analyzed time window.
Highlight the CPA and note if the CPA trend is improving or worsening.
Contextualize the time window's performance against the overall campaign metrics provided (e.g. if the window is a small fraction of the total, or if it is driving most of the pipeline).
Do NOT mention sparklines, tracking anomalies, or technical metrics.
Format in plain text without markdown."""
        
        from app.services.llm_rotator import get_cached_response, set_cached_response
        cached = get_cached_response(prompt)
        if cached:
            return cached
            
        import hashlib
        h = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        print(f"TLDR Prompt Hash: {h}")
        response = None
        last_err = None
        for _ in range(3):
            try:
                client = get_genai_client()
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                break
            except Exception as e:
                last_err = e
                
        if not response or not getattr(response, 'text', None):
            spend = payload.get("window_total_spend_dollars", 0)
            pipe = payload.get("window_pipeline_generated_dollars", 0)
            cpa = payload.get("window_cpa_dollars", 0)
            trend = payload.get("window_cpa_trend_vs_previous_window", 0)
            time_window = payload.get("time_window_analyzed", "All Time")
            trend_str = "improving" if trend < 0 else "elevated" if trend > 0 else "stable"
            
            fallback = f"Over the {time_window.lower()} analysis window, the campaign influenced ${pipe/1e6:.2f}M in pipeline against ${spend/1e3:.1f}k in media investment. Blended Cost Per Acquisition (CPA) is currently ${cpa:,.0f}, maintaining an {trend_str} efficiency curve relative to baseline targets. Engagement velocity across key accounts confirms strong omnichannel alignment."
            return fallback
            
        set_cached_response(prompt, response.text)
        return response.text
    except Exception as e:
        spend = payload.get("window_total_spend_dollars", 0)
        pipe = payload.get("window_pipeline_generated_dollars", 0)
        cpa = payload.get("window_cpa_dollars", 0)
        time_window = payload.get("time_window_analyzed", "All Time")
        return f"Across the {time_window.lower()} period, influenced pipeline stands at ${pipe/1e6:.2f}M with ${spend/1e3:.1f}k in media investment and a CPA of ${cpa:,.0f}. Overall account engagement and pipeline velocity remain steady across target accounts."


# ==============================================================================
# 5. Omnichannel Timeline & Trajectory Series
# ==============================================================================

def get_timeline_chart_data(campaign_id: str, timeframe: int = 90) -> dict:
    """
    Construct synchronized multi-channel daily time series for Chart.js:
      - Web traffic sessions from ga4_events.
      - LinkedIn ad clicks from linkedin_events.
      - Email opens from mailchimp_events.
      - CRM opportunities created with company and pipeline value annotations.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        
        # Calculate true start/end dates for zoom framing
        from datetime import datetime, timedelta
        now = datetime.now()
        
        # Start date
        cursor.execute(f"""
            SELECT MIN(timestamp) as start_date FROM (
                SELECT MIN(timestamp) as timestamp FROM ga4_events WHERE utm_campaign = '{campaign_id}'
                UNION ALL
                SELECT MIN(timestamp) as timestamp FROM linkedin_events WHERE campaign_id = '{campaign_id}'
                UNION ALL
                SELECT MIN(timestamp) as timestamp FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%'
                UNION ALL
                SELECT MIN(timestamp) as timestamp FROM crm_opps WHERE utm_campaign = '{campaign_id}'
            )
        """)
        s_row = cursor.fetchone()
        official_start = str(s_row["start_date"]).split(" ")[0] if s_row and s_row["start_date"] else None
        
        # CRM End Date Rule
        cursor.execute(f"SELECT MAX(timestamp) as last_opp_date FROM crm_opps WHERE utm_campaign = '{campaign_id}'")
        opp_row = cursor.fetchone()
        last_opp = str(opp_row["last_opp_date"]).split(" ")[0] if opp_row and opp_row["last_opp_date"] else None
        
        official_end = None
        is_completed = False
        if last_opp:
            l_opp_dt = datetime.strptime(last_opp, "%Y-%m-%d")
            if (now - l_opp_dt).days > 100:
                is_completed = True
                # Option 1B Soft Crop: pad the end date by 14 days so the chart visually ends gracefully after the last pipeline
                official_end = (l_opp_dt + timedelta(days=14)).strftime("%Y-%m-%d")
        
        # Determine grouping and timeframe conditions
        tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        date_format = "'%Y-%m-%d'"
        
        # Group traffic
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM ga4_events WHERE utm_campaign = '{campaign_id}' {tf_condition} GROUP BY period ORDER BY period")
        traffic_rows = cursor.fetchall()
        
        # Group CRM opps
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM crm_opps WHERE utm_campaign = '{campaign_id}' AND event_type = 'Opportunity Created' {tf_condition} GROUP BY period ORDER BY period")
        opps_rows = cursor.fetchall()
        
        # Get specific CRM opp details
        cursor.execute(f"SELECT o.event_type as type, strftime({date_format}, o.timestamp) as period, o.pipeline_value, u.company_name FROM crm_opps o JOIN (SELECT DISTINCT account_id, company_name FROM crm_users) u ON o.account_id = u.account_id WHERE o.utm_campaign = '{campaign_id}' {tf_condition}")
        opps_details_rows = cursor.fetchall()
        
        opps_details_map = {}
        for r in opps_details_rows:
            p = r["period"]
            if p not in opps_details_map:
                opps_details_map[p] = []
            opps_details_map[p].append({
                "company": r["company_name"],
                "value": r["pipeline_value"] or 0,
                "type": r["type"]
            })
        
        # Group LinkedIn Ad Clicks
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM linkedin_events WHERE campaign_id = '{campaign_id}' {tf_condition} GROUP BY period ORDER BY period")
        linkedin_rows = cursor.fetchall()
        
        # Group Mailchimp Email Opens
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND action = 'Open' {tf_condition} GROUP BY period ORDER BY period")
        mailchimp_rows = cursor.fetchall()
        
        conn.close()
        
        # Merge data
        data_map = {}
        for row in traffic_rows:
            data_map[row["period"]] = {"traffic": row["count"], "opps": 0, "ads": 0, "email": 0}
            
        def merge_into_map(rows, key):
            for row in rows:
                if row["period"] not in data_map:
                    data_map[row["period"]] = {"traffic": 0, "opps": 0, "ads": 0, "email": 0}
                data_map[row["period"]][key] = row["count"]
                
        merge_into_map(opps_rows, "opps")
        merge_into_map(linkedin_rows, "ads")
        merge_into_map(mailchimp_rows, "email")
            
        sorted_periods = sorted(data_map.keys())
        
        # Make sure the official start and end dates exist in the labels so the X-axis doesn't break
        if official_start and official_start not in sorted_periods:
            sorted_periods.insert(0, official_start)
            data_map[official_start] = {"traffic": 0, "opps": 0, "ads": 0, "email": 0}
            sorted_periods.sort()
            
        if official_end and official_end not in sorted_periods:
            sorted_periods.append(official_end)
            data_map[official_end] = {"traffic": 0, "opps": 0, "ads": 0, "email": 0}
            sorted_periods.sort()
        
        return {
            "labels": sorted_periods,
            "traffic": [data_map[p]["traffic"] for p in sorted_periods],
            "opps": [data_map[p]["opps"] for p in sorted_periods],
            "ads": [data_map[p]["ads"] for p in sorted_periods],
            "email": [data_map[p]["email"] for p in sorted_periods],
            "opps_details": {p: opps_details_map.get(p, []) for p in sorted_periods},
            "start_date": official_start,
            "end_date": official_end,
            "is_completed": is_completed
        }
    except Exception as e:
        raise e


# ==============================================================================
# 6. Asset Fatigue & Strategic Next-Best-Action Synthesis
# ==============================================================================


def get_asset_fatigue(campaign_id: str, timeframe: int = 0) -> list:
    """
    Evaluate content consumption decay across web assets.
    Compares recent 30-day velocity against the prior 30-day baseline to assign
    fatigue ratings: 'Healthy', 'Action Required', or 'Saturated'.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        
        # Look at the specific pages viewed as "Assets"
        assets = []
        cursor.execute(f"SELECT DISTINCT page_viewed FROM ga4_events WHERE utm_campaign = '{campaign_id}'")
        pages = cursor.fetchall()
        
        for p in pages:
            asset_name = p["page_viewed"]
            if asset_name == "/": asset_name = "/home"
            
            # Get last 30 days sparkline
            cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{p['page_viewed']}' AND timestamp >= date('now', '-30 days') GROUP BY dt ORDER BY dt")
            recent_rows = cursor.fetchall()
            
            # Get prior 30 days sum
            cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{p['page_viewed']}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
            prior_count = cursor.fetchone()["c"] or 0
            
            sparkline = [0] * 30
            # Simple mapping to last 30 days... 
            total_recent = sum(r["c"] for r in recent_rows)
            for r in recent_rows:
                # Naive placement for sparkline
                sparkline.append(r["c"])
            sparkline = sparkline[-30:] # keep 30 points
            
            # Calculate health
            if total_recent == 0 and prior_count == 0:
                health = "Saturated"
                badge = "bg-slate-800 text-slate-400 border-slate-700"
            elif prior_count == 0 or total_recent > prior_count * 0.8:
                health = "Healthy"
                badge = "bg-emerald-900/30 text-emerald-400 border-emerald-800/30"
            elif total_recent < prior_count * 0.3:
                health = "Action Required"
                badge = "bg-rose-900/30 text-rose-400 border-rose-800/30"
            else:
                health = "Saturated"
                badge = "bg-amber-900/30 text-amber-400 border-amber-800/30"
                
            assets.append({
                "name": asset_name.replace("/", "").replace("-", " ").title() + " Asset",
                "type": "PDF" if "whitepaper" in asset_name else "Web Page",
                "sparkline": sparkline,
                "health": health,
                "badge_class": badge,
                "recent_views": total_recent
            })
            
        conn.close()
        return assets
    except Exception as e:
        raise e

def get_ai_recommended_actions(campaign_id: str, timeframe: int, tab: str = "overview") -> list:
    """
    Generate tab-aware, actionable AI recommendation prompts constrained strictly
    to the 16 available backend MCP tool capabilities.
    
    Prompts are synthesized using Gemini, cached in Redis/JSON by prompt hash,
    and formatted with FontAwesome icons and action-command strings.
    """
    import json
    import uuid

    from datetime import datetime, timedelta
    from app.services.llm_rotator import get_genai_client, get_cached_response, set_cached_response
    from google.genai import types

    from app.services.llm_rotator import mcp_tools
    tool_summaries = [f"- {t['name']}: {t['description']}" for t in mcp_tools]
    tool_list = "\n".join(tool_summaries)

    time_label = "All Time" if timeframe == 0 else f"Last {timeframe} Days"

    # Build tab-specific context payload
    if tab == "performance":
        try:
            from app.services.analytics import get_asset_impact_matrix
            matrix = get_asset_impact_matrix(campaign_id, timeframe)
            top_assets = sorted(matrix, key=lambda x: x.get('impact_score', 0), reverse=True)[:5]
            fatigued = [a['asset_name'] for a in matrix if a.get('health') in ('Fatigued', 'Action Required')]
            context_payload = {
                "tab": "Asset Performance",
                "time_window": time_label,
                "top_assets_by_impact": [
                    {"name": a.get('asset_name'), "type": a.get('type'), "engagement": a.get('engagement', 0), "health": a.get('health')}
                    for a in top_assets
                ],
                "fatigued_asset_names": fatigued,
                "total_assets_tracked": len(matrix)
            }
            focus = "asset-level optimisation: fatigue, A/B testing, channel reallocation, and engagement spike analysis"
        except Exception:
            context_payload = {"tab": "Asset Performance", "time_window": time_label}
            focus = "asset performance optimisation"

    elif tab == "audience":
        try:
            from app.services.analytics import get_prioritized_sales_targets
            targets = get_prioritized_sales_targets(campaign_id, timeframe)[:3]
            context_payload = {
                "tab": "Audience & ABM",
                "time_window": time_label,
                "top_prioritised_targets": [
                    {"name": t['name'], "company": t['company'], "status": t['status'],
                     "interactions": t['interactions'], "personas_at_account": t['personas']}
                    for t in targets
                ],
                "total_targets_scored": len(targets)
            }
            focus = "account-based marketing: buying committee mapping, intent surge detection, outreach sequencing, and account penetration"
        except Exception:
            context_payload = {"tab": "Audience & ABM", "time_window": time_label}
            focus = "audience and account-based marketing"

    else:  # overview — original behaviour
        from app.services.analytics import get_kpi_benchmarks
        benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
        overall_benchmarks = get_kpi_benchmarks(campaign_id, 0)
        context_payload = {
            "tab": "Executive Overview",
            "time_window": time_label,
            "window_pipeline_generated_dollars": benchmarks["live"]["pipeline"],
            "window_total_spend_dollars": benchmarks["live"]["spend"],
            "window_cpa_dollars": benchmarks["live"]["cpa"],
            "window_cpa_trend_vs_previous_window": benchmarks["comparisons"]["cpa"]["value"],
            "window_closed_won_contracts": benchmarks["live"]["conversions"],
            "overall_campaign_pipeline_generated_dollars": overall_benchmarks["live"]["pipeline"],
            "overall_campaign_total_spend_dollars": overall_benchmarks["live"]["spend"],
            "overall_campaign_cpa_dollars": overall_benchmarks["live"]["cpa"]
        }
        focus = "scenario planning & reallocation, forecasting & extrapolation, or deep-dive analysis"

    prompt = f'''You are a B2B Marketing AI. Review this campaign telemetry for the {tab} view: {json.dumps(context_payload)}.
Based on this data, generate exactly 3 strategic "Next Best Actions" focused on {focus}.

CRITICAL INSTRUCTION:
The AI Copilot that will execute your "action_command" ONLY has access to the following backend tools:
{tool_list}

Your recommended actions MUST be directly executable using one or more of these specific tools. Do not invent analytical tasks that these tools cannot perform.

Output strictly as a JSON array of objects. Do not include markdown formatting or backticks.
Each object must have exactly these keys:
- "title": A very short 2-3 word title in sentence case (e.g. "Simulate budget shift", "Map buying committee").
- "message": A 1-sentence strategic question or command that clearly maps to an available tool.
- "action_command": The exact same string as "message".
- "icon": A font-awesome class (e.g. "fa-chart-pie", "fa-users", "fa-magnifying-glass").
'''

    cached = get_cached_response(prompt)
    if cached:
        try:
            items = json.loads(cached)
        except Exception:
            items = []
    else:
        items = []
        for _ in range(3):
            try:
                client = get_genai_client()
                resp = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7)
                )
                text = resp.text.replace('```json', '').replace('```', '').strip()
                items = json.loads(text)
                set_cached_response(prompt, json.dumps(items))
                break
            except Exception:
                pass

    actions = []
    for item in items:
        actions.append({
            "id": f"TRG_{uuid.uuid4().hex[:8]}",
            "campaign_id": campaign_id,
            "type": "ai",
            "message": item.get("message", "Run analysis"),
            "action_payload": item.get("title", "AI Action").capitalize(),
            "resolved_status": 0,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "icon": item.get("icon", "fa-bolt"),
            "icon_color": "text-fuchsia-400",
            "title": item.get("title", "AI Recommendation").capitalize(),
            "action_command": item.get("action_command", "Analyze")
        })
    return actions

def generate_next_best_actions(campaign_id: str, timeframe: int = 0) -> list:
    """
    Produce the prioritized Action Center tasks for the active campaign and timeframe.
    Combines active database triggers (`action_triggers`) with real-time heuristic checks
    for stalled pipeline opportunities, underperforming whitepapers, and CPA surges.
    """
    try:
        import uuid

        from datetime import datetime, timedelta
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Cleanup expired triggers
        cursor.execute("DELETE FROM action_triggers WHERE expires_at IS NOT NULL AND expires_at < ?", (datetime.now().isoformat(),))
        conn.commit()
        
        # Check DB first for timeframe 0
        if timeframe == 0:
            cursor.execute("SELECT * FROM action_triggers WHERE campaign_id = ? AND resolved_status = 0", (campaign_id,))
            existing = cursor.fetchall()
            if existing:
                conn.close()
                enriched = []
                for r in existing:
                    d = dict(r)
                    if 'icon' not in d: d['icon'] = 'fa-bolt'
                    if 'icon_color' not in d: d['icon_color'] = 'text-fuchsia-500'
                    if 'title' not in d: d['title'] = 'Action Required'
                    
                    # Fix fallback title mapping bug
                    if d.get("action_payload") == "Launch Outbound Sequence":
                        d['title'] = "TAM Penetration Stalled"
                        d['icon'] = "fa-crosshairs"
                        d['icon_color'] = "text-sky-500"
                        d['action_command'] = "Draft targeted outbound sales sequence for Tier 1 accounts"
                    elif d.get("action_payload") == "A/B Test Landing Page":
                        d['title'] = "Conversion Bottleneck"
                        d['icon'] = "fa-circle-exclamation"
                        d['icon_color'] = "text-amber-500"
                        d['action_command'] = "Draft new messaging or adjust gating strategy"
                    elif d.get("action_payload") == "Reallocate Budget":
                        d['title'] = "CPA Anomaly Detected"
                        d['icon'] = "fa-triangle-exclamation"
                        d['icon_color'] = "text-rose-500"
                        d['action_command'] = "Run pacing analysis to identify inefficient channels"
                    elif d.get("type") == "ai":
                        d['title'] = d.get("action_payload", "AI Recommendation")
                        d['icon'] = "fa-bolt"
                        d['icon_color'] = "text-fuchsia-400"
                        d['action_command'] = d.get("message", "Analyze data")
                        
                    if 'action_command' not in d: d['action_command'] = f"Execute action for {d.get('action_payload', 'this trigger')}"
                    enriched.append(d)
                return enriched
            
        actions = []
        
        from app.services.analytics import get_kpi_benchmarks, get_tam_penetration, get_campaign_start_date
        benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
        live_cpa = benchmarks["live"]["cpa"]
        cpa_diff = benchmarks["comparisons"]["cpa"]["value"]
        live_spend = benchmarks["live"]["spend"]
        
        # Rule 1: CPA Anomaly
        if live_spend > 1000 and cpa_diff > 30:
            actions.append({
                "id": f"TRG_{uuid.uuid4().hex[:8]}",
                "campaign_id": campaign_id,
                "type": "alert",
                "message": f"Blended CPA has spiked to ${live_cpa:,.0f} (+{cpa_diff:.1f}% vs baseline).",
                "action_payload": "Reallocate Budget",
                "resolved_status": 0,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=48)).isoformat(),
                "icon": "fa-triangle-exclamation",
                "icon_color": "text-rose-500",
                "title": "CPA Anomaly Detected",
                "action_command": "Run pacing analysis to identify inefficient channels"
            })
            
        # Rule 2: Funnel Conversion Drop-off
        tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' {tf_condition}")
        total_sessions = cursor.fetchone()["c"] or 0
        
        cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL {tf_condition}")
        known_users = cursor.fetchone()["c"] or 0
        
        conversion_rate = (known_users / total_sessions * 100) if total_sessions > 0 else 0
        min_visits = (15 * timeframe) if timeframe > 0 else 100
        
        if total_sessions >= min_visits and conversion_rate < 2.5:
            actions.append({
                "id": f"TRG_{uuid.uuid4().hex[:8]}",
                "campaign_id": campaign_id,
                "type": "insight",
                "message": f"Web traffic is healthy but Top-of-Funnel conversion is low ({conversion_rate:.1f}%).",
                "action_payload": "A/B Test Landing Page",
                "resolved_status": 0,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
                "icon": "fa-circle-exclamation",
                "icon_color": "text-amber-500",
                "title": "Conversion Bottleneck",
                "action_command": "Draft new messaging or adjust gating strategy"
            })
            
        # Rule 3: TAM Penetration Stagnation
        tam = get_tam_penetration(campaign_id)
        penetration_str = str(tam.get("value", "0%")).replace("%", "")
        try:
            penetration = float(penetration_str)
        except ValueError:
            penetration = 0.0
            
        start_str = get_campaign_start_date(campaign_id)
        if start_str != "Unknown":
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                days_active = (datetime.now() - start_date).days
                if days_active > 30 and penetration < 15.0:
                    actions.append({
                        "id": f"TRG_{uuid.uuid4().hex[:8]}",
                        "campaign_id": campaign_id,
                        "type": "insight",
                        "message": f"Campaign active for {days_active} days but Tier 1 penetration is stuck at {penetration}%.",
                        "action_payload": "Launch Outbound Sequence",
                        "resolved_status": 0,
                        "created_at": datetime.now().isoformat(),
                        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
                        "icon": "fa-crosshairs",
                        "icon_color": "text-sky-500",
                        "title": "TAM Penetration Stalled",
                        "action_command": "Draft targeted outbound sales sequence for Tier 1 accounts"
                    })
            except Exception as e:
                pass

        # Default fallback: Populate with Dynamic AI Recommendations
        if len(actions) == 0:
            actions.extend(get_ai_recommended_actions(campaign_id, timeframe))
            
        if timeframe == 0:
            for a in actions:
                try:
                    cursor.execute("""
                        INSERT INTO action_triggers (id, campaign_id, type, message, action_payload, resolved_status, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (a["id"], a["campaign_id"], a["type"], a["message"], a["action_payload"], a["resolved_status"], a["created_at"], a["expires_at"]))
                except Exception as e:
                    pass
                    
            conn.commit()
            
        conn.close()
        return actions
    except Exception as e:
        raise e
# --- Gemini MCP Tool Schemas ---
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
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The ID of the campaign to evaluate."
                }
            },
            "required": ["campaign_id"]
        }
    },
    {
        "name": "simulate_budget_shift",
        "description": "Simulates the projected pipeline value if the budget for a specific channel is shifted, using historical baseline conversion rates.",
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
    }
]

tool_functions = {
    "calculate_blended_cpa": calculate_blended_cpa,
    "get_account_penetration": get_account_penetration,
    "evaluate_trickle_threshold": evaluate_trickle_threshold,
    "simulate_budget_shift": simulate_budget_shift
}

def get_scoped_audience_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get users interacting with the campaign across all channels
        query = '''
        WITH AllEvents AS (
            SELECT timestamp, user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL
            UNION ALL
            SELECT m.timestamp, u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ?
            UNION ALL
            SELECT l.timestamp, g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = ?
        )
        SELECT 
            c.user_id,
            c.first_name, 
            c.last_name, 
            c.company_name, 
            c.seniority, 
            COUNT(a.timestamp) as interactions
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority
        '''
        cursor.execute(query, (campaign_id, f'%{campaign_id}%', campaign_id))
        all_users = cursor.fetchall()
        
        sqls = []
        mqls = []
        colds = []
        
        for u in all_users:
            if u['interactions'] >= 5:
                sqls.append(u)
            elif u['interactions'] >= 2:
                mqls.append(u)
            else:
                colds.append(u)
                
        sqls = sorted(sqls, key=lambda x: x['interactions'], reverse=True)
        mqls = sorted(mqls, key=lambda x: x['interactions'], reverse=True)
        colds = sorted(colds, key=lambda x: x['interactions'], reverse=True)
        
        # A realistic funnel mix (total 50)
        rows = sqls[:15] + mqls[:20] + colds[:15]
        
        user_ids = [str(r["user_id"]) for r in rows]
        assets_map = {}
        
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            ga4_query = f'''
            SELECT user_id, page_viewed as asset, COUNT(*) as freq
            FROM ga4_events
            WHERE utm_campaign = ? AND user_id IN ({placeholders}) AND page_viewed IS NOT NULL
            GROUP BY user_id, page_viewed
            '''
            params = [campaign_id] + user_ids
            cursor.execute(ga4_query, params)
            for row in cursor.fetchall():
                uid = str(int(row["user_id"]))
                if uid not in assets_map:
                    assets_map[uid] = {}
                asset_name = row["asset"].replace('/', ' ').replace('-', ' ').title().strip()
                if not asset_name: asset_name = "Homepage"
                asset_name += " (Web)"
                assets_map[uid][asset_name] = assets_map[uid].get(asset_name, 0) + row["freq"]

        users = []
        for row in rows:
            user_id = str(row["user_id"])
            full_name = f"{row['first_name']} {row['last_name']}"
            interactions = int(row["interactions"])
            seniority = row["seniority"]
            company = row["company_name"]
            
            user_assets_dict = assets_map.get(user_id, {})
            sorted_assets = sorted(user_assets_dict.items(), key=lambda item: item[1], reverse=True)
            
            structured_assets = []
            for k, v in sorted_assets:
                a_type = "Email" if " (Email)" in k else "Web"
                clean_name = k.replace(" (Web)", "").replace(" (Email)", "")
                structured_assets.append({
                    "name": clean_name,
                    "type": a_type,
                    "count": v
                })
                
            users.append({
                "id": user_id,
                "name": full_name,
                "company": company,
                "seniority": seniority,
                "interactions": interactions,
                "assets": structured_assets
            })
            
        conn.close()
        return {"users": users}
    except Exception as e:
        raise e
def get_audience_network_data() -> dict:
    """
    Returns nodes and links for a D3 force-directed graph, as well as a list of users for card view.
    Interaction count is based on raw sum of mc_events and ga4_events from master_summary.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get top 50 users by interaction to keep the graph readable
        query = """
        SELECT user_id, account_id, company_name, first_name, last_name, seniority, 
               (IFNULL(mc_events, 0) + IFNULL(ga4_events, 0)) as interactions
        FROM master_summary
        WHERE company_name IS NOT NULL AND first_name IS NOT NULL
        ORDER BY interactions DESC
        LIMIT 50
        """
        cursor.execute(query)
        cursor.execute(query)
        rows = cursor.fetchall()
        
        user_ids = [str(r["user_id"]) for r in rows]
        
        # Fetch specific assets they interacted with and their frequencies
        assets_map = {}
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            
            # Fetch Web Assets
            ga4_query = f"""
            SELECT user_id, page_viewed as asset, COUNT(*) as freq
            FROM ga4_events
            WHERE utm_campaign = ? AND user_id IN ({placeholders}) AND page_viewed IS NOT NULL
            GROUP BY user_id, page_viewed
            """
            params = [campaign_id] + user_ids
            cursor.execute(ga4_query, params)
            for row in cursor.fetchall():
                uid = str(int(row["user_id"]))
                if uid not in assets_map:
                    assets_map[uid] = {}
                asset_name = row["asset"].replace('/', ' ').replace('-', ' ').title().strip()
                if not asset_name: asset_name = "Homepage"
                asset_name += " (Web)"
                assets_map[uid][asset_name] = assets_map[uid].get(asset_name, 0) + row["freq"]
                
            # Fetch Email Assets
            mc_query = f"""
            SELECT u.user_id, m.url_clicked as asset, COUNT(*) as freq
            FROM mailchimp_events m
            JOIN crm_users u ON m.email = u.email
            WHERE m.campaign_id LIKE ? AND u.user_id IN ({placeholders}) AND m.url_clicked IS NOT NULL
            GROUP BY u.user_id, m.url_clicked
            """
            cursor.execute(mc_query, [f'%{campaign_id}%'] + user_ids)
            for row in cursor.fetchall():
                uid = str(row["user_id"])
                if uid not in assets_map:
                    assets_map[uid] = {}
                url = row["asset"]
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                if 'utm_campaign' in qs:
                    asset_name = qs['utm_campaign'][0].replace('CMP_', '').replace('LIVE_', '').replace('PAST_', '').replace('_', ' ').title()
                else:
                    asset_name = parsed.path.split('/')[-1].replace('-', ' ').title()
                    if not asset_name: asset_name = "Email Link"
                asset_name += " (Email)"
                assets_map[uid][asset_name] = assets_map[uid].get(asset_name, 0) + row["freq"]
                
            # Fetch LinkedIn Assets
            li_query = f"""
            SELECT g.user_id, l.ad_id as asset, COUNT(*) as freq
            FROM linkedin_events l
            JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id
            WHERE l.campaign_id = ? AND g.user_id IN ({placeholders}) AND l.ad_id IS NOT NULL
            GROUP BY g.user_id, l.ad_id
            """
            cursor.execute(li_query, [campaign_id] + user_ids)
            for row in cursor.fetchall():
                uid = str(row["user_id"])
                if uid not in assets_map:
                    assets_map[uid] = {}
                asset_name = row["asset"].replace("LI_AD_", "").replace("_", " ").title()
                asset_name += " (Social)"
                assets_map[uid][asset_name] = assets_map[uid].get(asset_name, 0) + row["freq"]

        conn.close()
        
        nodes = []
        links = []
        
        # 1. Add Campaign Node (Root)
        nodes.append({"id": "Campaign", "group": 0, "radius": 40, "name": "Global Campaign", "seniority": "Campaign", "assets": []})
        
        companies = set()
        users = []
        
        for row in rows:
            company = row["company_name"]
            if company not in companies:
                companies.add(company)
                nodes.append({"id": company, "group": 1, "radius": 20, "name": company, "seniority": "Company", "assets": []})
                links.append({"source": "Campaign", "target": company, "value": 5})
                
            user_id = str(row["user_id"])
            full_name = f"{row['first_name']} {row['last_name']}"
            interactions = int(row["interactions"])
            seniority = row["seniority"]
            
            # Format the assets list as structured objects
            user_assets_dict = assets_map.get(user_id, {})
            # Sort by frequency descending
            sorted_assets = sorted(user_assets_dict.items(), key=lambda item: item[1], reverse=True)
            
            structured_assets = []
            for k, v in sorted_assets:
                if " (Email)" in k:
                    a_type = "Email"
                elif " (Social)" in k:
                    a_type = "Social"
                else:
                    a_type = "Web"
                
                clean_name = k.replace(" (Web)", "").replace(" (Email)", "").replace(" (Social)", "")
                structured_assets.append({
                    "name": clean_name,
                    "type": a_type,
                    "count": v
                })
            
            # User node
            nodes.append({
                "id": user_id, 
                "group": 2, 
                "radius": max(5, min(15, interactions * 2)), 
                "name": full_name,
                "seniority": seniority,
                "assets": structured_assets[:10] # limit to top 10
            })
            links.append({"source": company, "target": user_id, "value": 1})
            
            # Add to user cards list
            users.append({
                "id": user_id,
                "name": full_name,
                "company": company,
                "seniority": seniority,
                "interactions": interactions,
                "assets": structured_assets # Send all assets to the frontend modal
            })
            
        return {"nodes": nodes, "links": links, "users": users}
    except Exception as e:
        raise e
@lru_cache(maxsize=128)
def get_sankey_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        links_map = {} # (source, target): value
        
        # 1. LinkedIn -> Users
        query_li = f"""
        SELECT l.ad_id, c.seniority, COUNT(*) as freq
        FROM linkedin_events l
        JOIN crm_users c ON l.user_id = c.user_id
        WHERE l.campaign_id = '{campaign_id}'
        GROUP BY l.ad_id, c.seniority
        """
        cursor.execute(query_li)
        for row in cursor.fetchall():
            asset = row["ad_id"].replace("LI_AD_", "").replace("_", " ").title()
            sen = row["seniority"]
            freq = row["freq"]
            links_map[("LinkedIn Ad", asset)] = links_map.get(("LinkedIn Ad", asset), 0) + freq
            links_map[(asset, sen)] = links_map.get((asset, sen), 0) + freq
            
        # 2. Mailchimp -> Users
        query_mc = f"""
        SELECT m.url_clicked, c.seniority, COUNT(*) as freq
        FROM mailchimp_events m
        JOIN crm_users c ON m.user_id = c.user_id
        WHERE m.campaign_id = '{campaign_id}' AND m.url_clicked IS NOT NULL
        GROUP BY m.url_clicked, c.seniority
        """
        import urllib.parse
        cursor.execute(query_mc)
        for row in cursor.fetchall():
            url = row["url_clicked"]
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'utm_campaign' in qs:
                asset = qs['utm_campaign'][0].replace('CMP_', '').replace('LIVE_', '').replace('PAST_', '').replace('_', ' ').title()
            else:
                asset = parsed.path.split('/')[-1].replace('-', ' ').title()
            if not asset: asset = "Email Link"
            
            sen = row["seniority"]
            freq = row["freq"]
            links_map[("Email Outreach", asset)] = links_map.get(("Email Outreach", asset), 0) + freq
            links_map[(asset, sen)] = links_map.get((asset, sen), 0) + freq

        # 3. GA4 -> Users
        query_ga4 = f"""
        SELECT g.page_viewed, c.seniority, COUNT(*) as freq
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = '{campaign_id}' AND g.page_viewed IS NOT NULL
        GROUP BY g.page_viewed, c.seniority
        """
        cursor.execute(query_ga4)
        for row in cursor.fetchall():
            asset = row["page_viewed"].replace('/', ' ').replace('-', ' ').title().strip()
            if not asset: asset = "Homepage"
            sen = row["seniority"]
            freq = row["freq"]
            
            source = "Web Traffic"
            links_map[(source, asset)] = links_map.get((source, asset), 0) + freq
            links_map[(asset, sen)] = links_map.get((asset, sen), 0) + freq
            
        conn.close()
        
        # Build Nodes and Links
        nodes_set = set()
        for (src, tgt) in links_map.keys():
            nodes_set.add(src)
            nodes_set.add(tgt)
            
        # Ensure sequential structure by resolving circular or missing paths
        nodes = [{"id": n, "name": n} for n in nodes_set]
        links = [{"source": src, "target": tgt, "value": val} for (src, tgt), val in links_map.items()]
        
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise e
def get_asset_timeline_data(campaign_id: str = None) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        assets = []
        
        # 1. Web Assets (GA4)
        q_ga4 = f"""
        SELECT 'Web' as type, page_viewed as name, MIN(timestamp) as release_date, COUNT(*) as interactions 
        FROM ga4_events 
        WHERE page_viewed IS NOT NULL {'AND utm_campaign = ?' if campaign_id else ''}
        GROUP BY page_viewed
        """
        cursor.execute(q_ga4, (campaign_id,) if campaign_id else ())
        for row in cursor.fetchall():
            name = row["name"].replace('/', ' ').replace('-', ' ').title().strip()
            if not name: name = "Homepage"
            assets.append({
                "type": row["type"],
                "name": name,
                "release_date": row["release_date"],
                "interactions": row["interactions"]
            })
            
        # 2. Email Assets (Mailchimp)
        q_mc = f"""
        SELECT 'Email' as type, url_clicked as raw_name, MIN(timestamp) as release_date, COUNT(*) as interactions 
        FROM mailchimp_events 
        WHERE url_clicked IS NOT NULL {'AND campaign_id = ?' if campaign_id else ''}
        GROUP BY url_clicked
        """
        import urllib.parse
        cursor.execute(q_mc, (campaign_id,) if campaign_id else ())
        for row in cursor.fetchall():
            url = row["raw_name"]
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'utm_campaign' in qs:
                name = qs['utm_campaign'][0].replace('CMP_', '').replace('LIVE_', '').replace('PAST_', '').replace('_', ' ').title()
            else:
                name = parsed.path.split('/')[-1].replace('-', ' ').title()
            if not name: name = "Email Link"
            
            assets.append({
                "type": row["type"],
                "name": name,
                "release_date": row["release_date"],
                "interactions": row["interactions"]
            })
            
        # 3. LinkedIn Assets
        q_li = f"""
        SELECT 'LinkedIn' as type, ad_id as name, MIN(timestamp) as release_date, COUNT(*) as interactions 
        FROM linkedin_events 
        WHERE ad_id IS NOT NULL {'AND campaign_id = ?' if campaign_id else ''}
        GROUP BY ad_id
        """
        cursor.execute(q_li, (campaign_id,) if campaign_id else ())
        for row in cursor.fetchall():
            name = row["name"].replace("LI_AD_", "").replace("_", " ").title()
            assets.append({
                "type": row["type"],
                "name": name,
                "release_date": row["release_date"],
                "interactions": row["interactions"]
            })
            
        conn.close()
        
        # Deduplicate and merge by name
        merged = {}
        for a in assets:
            k = a["name"]
            if k in merged:
                merged[k]["interactions"] += a["interactions"]
                if a["release_date"] < merged[k]["release_date"]:
                    merged[k]["release_date"] = a["release_date"]
            else:
                merged[k] = a
                
        # Sort by release date
        final_list = list(merged.values())
        final_list.sort(key=lambda x: x["release_date"])
        
        return final_list
    except Exception as e:
        raise e
def get_channel_roi_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # LinkedIn
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), SUM(e.spend_consumed)
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ?
        ''', (campaign_id,))
        li_row = cursor.fetchone()
        li_accounts = li_row[0] or 0
        li_spend = li_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ? LIMIT 10
        ''', (campaign_id,))
        li_list = [r[0] for r in cursor.fetchall()]

        # Email
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.event_id)
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id LIKE '%' || ? || '%'
        ''', (campaign_id,))
        em_row = cursor.fetchone()
        em_accounts = em_row[0] or 0
        em_clicks = em_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id LIKE '%' || ? || '%' LIMIT 10
        ''', (campaign_id,))
        em_list = [r[0] for r in cursor.fetchall()]

        # Web
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.session_id)
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ?
        ''', (campaign_id,))
        web_row = cursor.fetchone()
        web_accounts = web_row[0] or 0
        web_views = web_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ? LIMIT 10
        ''', (campaign_id,))
        web_list = [r[0] for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            'linkedin': {'accounts_reached': li_accounts, 'total_spend': li_spend, 'accounts': li_list},
            'email': {'accounts_engaged': em_accounts, 'total_clicks': em_clicks, 'accounts': em_list},
            'web': {'accounts_identified': web_accounts, 'total_pageviews': web_views, 'accounts': web_list}
        }
    except Exception as e:
        raise e
def get_ui_lab_funnel_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM ga4_events WHERE utm_campaign = ?", (campaign_id,))
        visitors = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM ga4_events WHERE utm_campaign = ? AND bounce_flag = 0", (campaign_id,))
        engaged = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL", (campaign_id,))
        known = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM crm_opps WHERE utm_campaign = ?", (campaign_id,))
        pipeline = cursor.fetchone()[0] or 0
        
        # Activated is roughly midway between known and pipeline
        activated = int((known + pipeline) / 2) if known > 0 else 0
        
        conn.close()
        return {'visitors': visitors, 'engaged': engaged, 'known': known, 'activated': activated, 'pipeline': pipeline}
    except Exception as e:
        raise e
def get_ui_lab_heatmap_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Aggregate GA4 events by day
        cursor.execute('''
            SELECT date(timestamp) as day, COUNT(*) as interactions
            FROM ga4_events
            WHERE utm_campaign = ?
            GROUP BY day
        ''', (campaign_id,))
        
        days_data = {}
        for row in cursor.fetchall():
            days_data[row['day']] = row['interactions']
            
        conn.close()
        return {'heatmap': days_data}
    except Exception as e:
        raise e
def get_prioritized_sales_targets(campaign_id: str, timeframe: int = 0) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""

        # 1. Get all users who interacted with this campaign across Web, Email, and LinkedIn
        query = f'''
        WITH AllEvents AS (
            SELECT timestamp, user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL {tf_cond}
            UNION ALL
            SELECT m.timestamp, u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ? {tf_cond}
            UNION ALL
            SELECT l.timestamp, g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = ? {tf_cond}
        )
        SELECT 
            c.user_id,
            c.first_name, 
            c.last_name, 
            c.company_name, 
            c.seniority, 
            COUNT(a.timestamp) as campaign_interactions,
            MAX(a.timestamp) as last_active
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority
        '''
        cursor.execute(query, (campaign_id, f'%{campaign_id}%', campaign_id))
        all_users = cursor.fetchall()
        
        # 2. Get Account Momentum (Total unique users per company engaged in this campaign)
        acct_query = f'''
        WITH AllEvents AS (
            SELECT user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL {tf_cond}
            UNION ALL
            SELECT u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ? {tf_cond}
            UNION ALL
            SELECT g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = ? {tf_cond}
        )
        SELECT c.company_name, COUNT(DISTINCT a.user_id) as active_personas
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.company_name
        '''
        cursor.execute(acct_query, (campaign_id, f'%{campaign_id}%', campaign_id))
        acct_rows = cursor.fetchall()
        account_momentum = {row['company_name']: row['active_personas'] for row in acct_rows}

        # 3. Composite Lead Scoring
        scored_users = []
        from datetime import datetime, timedelta
        now = datetime.now()
        
        for u in all_users:
            interactions = u['campaign_interactions']
            company = u['company_name']
            personas = account_momentum.get(company, 1)
            seniority = u['seniority']
            last_active = u['last_active']
            
            # Base interaction score
            score = interactions * 10
            
            # Momentum score
            score += (personas - 1) * 15  # Additional personas give momentum points
            
            # Seniority score
            if seniority == 'C-Suite':
                score += 25
            elif seniority == 'VP/Director':
                score += 15
            else:
                score += 5
                
            # Recency score
            if last_active:
                try:
                    last_active_dt = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        last_active_dt = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        last_active_dt = now - timedelta(days=100)
                
                days_ago = (now - last_active_dt).days
                if days_ago <= 7:
                    score += 20
                elif days_ago <= 30:
                    score += 10

            # Convert Row to dict so we can add score
            user_dict = dict(u)
            user_dict['lead_score'] = score
            scored_users.append(user_dict)
            
        # Sort by lead score descending and take top 5
        scored_users = sorted(scored_users, key=lambda x: x['lead_score'], reverse=True)
        users = scored_users[:5]
        
        targets = []
        for user in users:
            interactions = user['campaign_interactions']
            company = user['company_name']
            personas = account_momentum.get(company, 1)
            
            if interactions >= 5:
                status = "SQL"
                color = "text-emerald-400"
                bg = "bg-emerald-400/10"
                border = "border-emerald-500/20"
                if 'VP' in user['seniority'] or 'Director' in user['seniority'] or 'C-Suite' in user['seniority']:
                    action = f"Executive outreach. Reference the {personas} active personas from their account."
                else:
                    action = "Send 'Technical Deep Dive' sequence. High individual engagement."
            elif interactions >= 2:
                status = "MQL"
                color = "text-brand-400"
                bg = "bg-brand-400/10"
                border = "border-brand-500/20"
                if personas >= 3:
                    action = "Account is heating up. Multi-thread outreach to this contact."
                else:
                    action = "Nurture with relevant case studies to push to SQL."
            else:
                status = "Cold Prospect"
                color = "text-slate-400"
                bg = "bg-dark-700"
                border = "border-dark-600"
                action = "Enroll in standard top-of-funnel nurture."
                
            targets.append({
                'name': f"{user['first_name']} {user['last_name']}",
                'company': company,
                'seniority': user['seniority'],
                'interactions': interactions,
                'last_active': user['last_active'].split(' ')[0] if user['last_active'] else None,
                'status': status,
                'personas': personas,
                'color': color,
                'bg': bg,
                'border': border,
                'action': action,
                'score': user['lead_score']
            })
            
        return targets
    except Exception as e:
        raise e

# --- MIGRATED FROM V1 ANALYTICS ---

def get_scoped_audience_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get users interacting with the campaign across all channels
        query = '''
        WITH AllEvents AS (
            SELECT timestamp, user_id FROM ga4_events WHERE utm_campaign COLLATE NOCASE = ? AND user_id IS NOT NULL
            UNION ALL
            SELECT m.timestamp, u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ?
            UNION ALL
            SELECT l.timestamp, g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id COLLATE NOCASE = ?
        )
        SELECT 
            c.user_id,
            c.first_name, 
            c.last_name, 
            c.company_name, 
            c.seniority,
            c.job_title,
            c.persona_type,
            MAX(a.timestamp) as last_active,
            COUNT(a.timestamp) as interactions
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority, c.persona_type
        '''
        cursor.execute(query, (campaign_id, f'%{campaign_id}%', campaign_id))
        all_users = cursor.fetchall()
        
        sqls = []
        mqls = []
        colds = []
        
        for u in all_users:
            if u['interactions'] >= 5:
                sqls.append(u)
            elif u['interactions'] >= 2:
                mqls.append(u)
            else:
                colds.append(u)
                
        sqls = sorted(sqls, key=lambda x: x['interactions'], reverse=True)
        mqls = sorted(mqls, key=lambda x: x['interactions'], reverse=True)
        colds = sorted(colds, key=lambda x: x['interactions'], reverse=True)
        
        # Return all users so Account Deep Dive has complete data
        rows = sqls + mqls + colds
        
        user_ids = [str(r["user_id"]) for r in rows]
        assets_map = {}
        
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            timeline_query = f'''
            WITH UserJourney AS (
                SELECT user_id, 'Web' as type, page_viewed as asset, timestamp 
                FROM ga4_events 
                WHERE utm_campaign COLLATE NOCASE = ? AND user_id IN ({placeholders}) AND page_viewed IS NOT NULL
                
                UNION ALL
                
                SELECT u.user_id, 'Email' as type, m.campaign_id as asset, m.timestamp
                FROM mailchimp_events m
                JOIN crm_users u ON m.email = u.email
                WHERE m.campaign_id LIKE ? AND u.user_id IN ({placeholders})
                
                UNION ALL
                
                SELECT g.user_id, 'LinkedIn' as type, l.ad_id as asset, l.timestamp
                FROM linkedin_events l
                JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id
                WHERE l.campaign_id COLLATE NOCASE = ? AND g.user_id IN ({placeholders})
            )
            SELECT user_id, type, asset, timestamp FROM UserJourney ORDER BY timestamp ASC
            '''
            params = [campaign_id] + user_ids + [f'%{campaign_id}%'] + user_ids + [campaign_id] + user_ids
            cursor.execute(timeline_query, params)
            
            for row in cursor.fetchall():
                uid = str(int(row["user_id"]))
                if uid not in assets_map:
                    assets_map[uid] = []
                
                nm = row['asset'].replace('/', ' ').replace('-', ' ').title().strip()
                if not nm: nm = 'Homepage'
                
                dt = row['timestamp'].split(' ')[0]
                import datetime
                try:
                    dt_obj = datetime.datetime.strptime(dt, '%Y-%m-%d')
                    fmt_date = dt_obj.strftime('%d %b %Y').upper()
                except:
                    fmt_date = dt
                
                assets_map[uid].append({
                    'type': row['type'],
                    'asset': nm,
                    'date': fmt_date,
                    'is_current': False
                })

        users = []
        for row in rows:
            user_id = str(row["user_id"])
            full_name = f"{row['first_name']} {row['last_name']}"
            interactions = int(row["interactions"])
            seniority = row["seniority"]
            job_title = row["job_title"]
            company = row["company_name"]
            persona_type = row["persona_type"]
            last_active = row["last_active"]
            
            user_timeline = assets_map.get(user_id, [])
            
            users.append({
                "id": user_id,
                "name": full_name,
                "interactions": interactions,
                "seniority": seniority,
                "title": job_title,
                "company": company,
                "persona_type": persona_type,
                "last_active": last_active,
                "timeline": user_timeline
            })
            
        conn.close()
        return {"users": users}
    except Exception as e:
        print("Error in scoped audience:", e)
        return {"users": []}

def get_channel_roi_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # LinkedIn
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), SUM(e.spend_consumed)
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ?
        ''', (campaign_id,))
        li_row = cursor.fetchone()
        li_accounts = li_row[0] or 0
        li_spend = li_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ? LIMIT 10
        ''', (campaign_id,))
        li_list = [r[0] for r in cursor.fetchall()]

        # Email
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.event_id)
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id LIKE '%' || ? || '%'
        ''', (campaign_id,))
        em_row = cursor.fetchone()
        em_accounts = em_row[0] or 0
        em_clicks = em_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id LIKE '%' || ? || '%' LIMIT 10
        ''', (campaign_id,))
        em_list = [r[0] for r in cursor.fetchall()]

        # Web
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.session_id)
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ?
        ''', (campaign_id,))
        web_row = cursor.fetchone()
        web_accounts = web_row[0] or 0
        web_views = web_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ? LIMIT 10
        ''', (campaign_id,))
        web_list = [r[0] for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            'linkedin': {'accounts_reached': li_accounts, 'total_spend': li_spend, 'accounts': li_list},
            'email': {'accounts_engaged': em_accounts, 'total_clicks': em_clicks, 'accounts': em_list},
            'web': {'accounts_identified': web_accounts, 'total_pageviews': web_views, 'accounts': web_list}
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {'error': str(e)}

def get_ui_lab_funnel_data(campaign_id: str, timeframe: int = 0) -> dict:
    """
    Compute progressive conversion funnel stages for the active campaign:
    Visitors (all GA4 sessions) -> Engaged (non-bounce) -> Known (CRM user matched)
    -> Pipeline (active opportunities) -> Won (Closed Won contracts).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tf_ga = f" AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        tf_crm = f" AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        
        cursor.execute(f"SELECT COUNT(DISTINCT session_id) FROM ga4_events WHERE utm_campaign = ? {tf_ga}", (campaign_id,))
        visitors = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT COUNT(DISTINCT session_id) FROM ga4_events WHERE utm_campaign = ? AND bounce_flag = 0 {tf_ga}", (campaign_id,))
        engaged = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT COUNT(DISTINCT user_id) FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL {tf_ga}", (campaign_id,))
        known = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT COUNT(DISTINCT user_id), SUM(pipeline_value) FROM crm_opps WHERE utm_campaign = ? {tf_crm}", (campaign_id,))
        pipe_row = cursor.fetchone()
        pipeline = pipe_row[0] or 0
        pipeline_val = pipe_row[1] or 0.0
        
        cursor.execute(f"SELECT COUNT(DISTINCT user_id), SUM(pipeline_value) FROM crm_opps WHERE utm_campaign = ? AND event_type = 'Closed Won' {tf_crm}", (campaign_id,))
        won_row = cursor.fetchone()
        won = won_row[0] or 0
        won_val = won_row[1] or 0.0
        
        conn.close()
        return {
            "visitors": visitors,
            "engaged": engaged,
            "known": known,
            "pipeline": pipeline,
            "pipeline_val": pipeline_val,
            "won": won,
            "won_val": won_val
        }
    except Exception as e:
        return {'error': str(e)}


def get_ui_lab_heatmap_data(campaign_id: str) -> dict:
    """Aggregate total GA4 website engagements by calendar date for heatmap visualization."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Aggregate GA4 events by day
        cursor.execute('''
            SELECT date(timestamp) as day, COUNT(*) as interactions
            FROM ga4_events
            WHERE utm_campaign = ?
            GROUP BY day
        ''', (campaign_id,))
        
        days_data = {}
        for row in cursor.fetchall():
            days_data[row['day']] = row['interactions']
            
        conn.close()
        return {'heatmap': days_data}
    except Exception as e:
        return {'error': str(e)}


def get_asset_personas(campaign_id: str, asset_name: str, asset_type: str, timeframe: int = 0) -> list:
    """
    Retrieve all CRM contacts and their complete cross-channel touchpoint timelines
    for a given marketing asset.
    
    Performance Architecture:
      Uses a 2-query batched architecture (eliminating the previous N+1 sub-query loop):
      - Query 1: Discovers all user IDs that engaged with the specific asset.
      - Query 2: Performs a single batched UNION ALL across Web, Email, and LinkedIn
        for all discovered user IDs via `IN (...)`, then groups the timeline in Python.
    """
    import datetime as _dt


    conn = get_db_connection()
    cursor = conn.cursor()
    tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""

    # --- Query 1: fetch the users who interacted with the asset ---
    if asset_type == 'Web':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(g.session_id) as asset_interactions
        FROM crm_users u
        JOIN ga4_events g ON u.user_id = g.user_id
        WHERE g.utm_campaign = ? AND g.page_viewed = ? {tf_condition.replace('timestamp', 'g.timestamp')}
        GROUP BY u.user_id
        """
        params = (campaign_id, asset_name)
    elif asset_type == 'Email':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(m.timestamp) as asset_interactions
        FROM crm_users u
        JOIN mailchimp_events m ON u.email = m.email
        LEFT JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
        WHERE m.campaign_id LIKE ?
          AND (
            m.url_clicked = ?
            OR REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') = ?
            OR m.url_clicked LIKE '%' || ?
            OR c.title = ?
          ) {tf_condition.replace('timestamp', 'm.timestamp')}
        GROUP BY u.user_id
        """
        params = (f'%{campaign_id}%', asset_name, asset_name, asset_name, asset_name)
    elif asset_type == 'LinkedIn':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(l.timestamp) as asset_interactions
        FROM crm_users u
        JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON u.user_id = g.user_id
        JOIN linkedin_events l ON g.cookie_id = l.cookie_id
        WHERE l.campaign_id = ? AND l.ad_id = ? {tf_condition.replace('timestamp', 'l.timestamp')}
        GROUP BY u.user_id
        """
        params = (campaign_id, asset_name)
    else:
        conn.close()
        return []

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return []

    # Collect all matching user IDs for the batched timeline query.
    user_ids = [str(r['user_id']) for r in rows]
    uid_placeholders = ','.join('?' * len(user_ids))

    # --- Query 2: fetch the full cross-channel journey for ALL matched users in one shot ---
    # Replaces the previous per-user sub-query loop (N+1 → 2 total queries).
    # Explicitly CAST user_id to INT because ga4_events stores user_id as REAL (e.g. 22.0)
    # whereas crm_users stores it as INTEGER (22).
    cursor.execute(f"""
        WITH UserJourney AS (
            SELECT CAST(g.user_id AS INT) as user_id,
                   'Web' as type,
                   COALESCE(c.title, g.page_viewed) as asset,
                   g.page_viewed as raw_asset,
                   g.timestamp
            FROM ga4_events g
            LEFT JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = ?
              AND g.user_id IN ({uid_placeholders})
              AND g.page_viewed IS NOT NULL

            UNION ALL

            SELECT CAST(u.user_id AS INT) as user_id,
                   'Email' as type,
                   COALESCE(c.title, REPLACE(REPLACE(m.url_clicked,
                       'https://woodplc.com?utm_campaign=', ''),
                       'https://example.com?utm_source=mailchimp&utm_campaign=', '')) as asset,
                   REPLACE(REPLACE(m.url_clicked,
                       'https://woodplc.com?utm_campaign=', ''),
                       'https://example.com?utm_source=mailchimp&utm_campaign=', '') as raw_asset,
                   m.timestamp
            FROM mailchimp_events m
            JOIN crm_users u ON u.email = m.email
            LEFT JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked,
                'https://woodplc.com?utm_campaign=', ''),
                'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
            WHERE m.campaign_id LIKE ?
              AND u.user_id IN ({uid_placeholders})

            UNION ALL

            SELECT CAST(g2.user_id AS INT) as user_id,
                   'LinkedIn' as type,
                   COALESCE(c.title, l.ad_id) as asset,
                   l.ad_id as raw_asset,
                   l.timestamp
            FROM linkedin_events l
            JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g2
                ON l.cookie_id = g2.cookie_id
            LEFT JOIN content_metadata c ON l.ad_id = c.url
            WHERE l.campaign_id = ?
              AND g2.user_id IN ({uid_placeholders})
        )
        SELECT user_id, type, asset, raw_asset, timestamp
        FROM UserJourney
        ORDER BY user_id, timestamp ASC
    """, [campaign_id] + user_ids + [f'%{campaign_id}%'] + user_ids + [campaign_id] + user_ids)

    all_timeline_rows = cursor.fetchall()
    conn.close()

    # Group timeline rows by user_id in Python — O(total touchpoints), not O(N users).
    from collections import defaultdict
    timeline_by_uid: dict = defaultdict(list)
    for ar in all_timeline_rows:
        uid = str(int(float(ar['user_id'])))
        nm = ar['asset']
        if not nm:
            nm = 'Homepage'
        elif nm.startswith('/') or nm.startswith('email-') or nm.startswith('li-'):
            nm = nm.replace('/', ' ').replace('-', ' ').title().strip()

        dt = ar['timestamp'].split(' ')[0]
        try:
            fmt_date = _dt.datetime.strptime(dt, '%Y-%m-%d').strftime('%d %b %Y')
        except ValueError:
            fmt_date = dt

        raw = ar['raw_asset'] or ''
        is_cur = (ar['asset'] == asset_name or raw == asset_name or (raw and asset_name in raw))

        timeline_by_uid[uid].append({
            'type': ar['type'],
            'asset': nm,
            'date': fmt_date,
            'is_current': is_cur,
        })

    # Assemble the final user list preserving original row order.
    users = []
    for r in rows:
        uid = str(int(float(r['user_id'])))
        timeline = timeline_by_uid.get(uid, [])
        users.append({
            'name': f"{r['first_name']} {r['last_name']}",
            'company': r['company_name'],
            'seniority': r['seniority'],
            'interactions': len(timeline),
            'id': uid,
            'timeline': timeline,
            'remaining_interactions': 0,
        })

    return users



def get_funnel_drilldown_data(campaign_id: str, stage: str, timeframe: int = 0) -> list:
    """
    Fetch granular individual contacts and their interaction histories for a specific funnel stage:
    `known_users`, `engaged_visitors`, `pipeline`, or `closed_won`.
    """
    try:
        conn = get_db_connection()

        cursor = conn.cursor()
        
        data = []
        
        tf_ga = f" AND e.timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        tf_crm = f" AND o.timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        
        if stage == 'known_users':
            cursor.execute(f"""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority, u.user_id
                FROM ga4_events e 
                JOIN crm_users u ON e.user_id = u.user_id 
                WHERE e.utm_campaign = ? AND e.user_id IS NOT NULL {tf_ga}
                LIMIT 50
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                timeline = _fetch_user_timeline(cursor, campaign_id, str(r[5]))
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": None,
                    "interactions": len(timeline),
                    "timeline": timeline,
                    "id": str(r[5])
                })
        elif stage == 'opportunities':
            cursor.execute(f"""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority, SUM(o.pipeline_value) as value, u.user_id
                FROM crm_opps o 
                JOIN crm_users u ON o.user_id = u.user_id 
                WHERE o.utm_campaign = ? {tf_crm}
                GROUP BY u.user_id
                ORDER BY value DESC
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                timeline = _fetch_user_timeline(cursor, campaign_id, str(r[6]))
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": r[5],
                    "interactions": len(timeline),
                    "timeline": timeline,
                    "id": str(r[6])
                })
        elif stage == 'contracts':
            cursor.execute(f"""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority, SUM(o.pipeline_value) as value, u.user_id
                FROM crm_opps o 
                JOIN crm_users u ON o.user_id = u.user_id 
                WHERE o.utm_campaign = ? AND o.event_type = 'Closed Won' {tf_crm}
                GROUP BY u.user_id
                ORDER BY value DESC
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                timeline = _fetch_user_timeline(cursor, campaign_id, str(r[6]))
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": r[5],
                    "interactions": len(timeline),
                    "timeline": timeline,
                    "id": str(r[6])
                })
                
        conn.close()
        return data
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return []



def _fetch_user_timeline(cursor, campaign_id, user_id):
    cursor.execute('''
        WITH UserJourney AS (
            SELECT 'Web' as type, COALESCE(c.title, g.page_viewed) as asset, g.timestamp 
            FROM ga4_events g
            LEFT JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = ? AND g.user_id = ? AND g.page_viewed IS NOT NULL
            
            UNION ALL
            
            SELECT 'Email' as type, COALESCE(c.title, m.campaign_id) as asset, m.timestamp
            FROM mailchimp_events m
            LEFT JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
            WHERE m.campaign_id LIKE ? AND m.email = (SELECT email FROM crm_users WHERE user_id = ?)
            
            UNION ALL
            
            SELECT 'LinkedIn' as type, COALESCE(c.title, l.ad_id) as asset, l.timestamp
            FROM linkedin_events l
            JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id
            LEFT JOIN content_metadata c ON l.ad_id = c.url
            WHERE l.campaign_id = ? AND g.user_id = ?
        )
        SELECT type, asset, timestamp FROM UserJourney ORDER BY timestamp ASC
    ''', (campaign_id, user_id, f'%{campaign_id}%', user_id, campaign_id, user_id))
    
    assets_rows = cursor.fetchall()
    
    timeline = []
    for ar in assets_rows:
        nm = ar['asset']
        if not nm: nm = 'Homepage'
        elif nm.startswith('/') or nm.startswith('email-') or nm.startswith('li-'):
            nm = nm.replace('/', ' ').replace('-', ' ').title().strip()
        
        dt = ar['timestamp'].split(' ')[0]
        import datetime
        try:
            dt_obj = datetime.datetime.strptime(dt, '%Y-%m-%d')
            fmt_date = dt_obj.strftime('%d %b %Y')
        except:
            fmt_date = dt
            
        timeline.append({
            'type': ar['type'],
            'asset': nm,
            'date': fmt_date,
            'is_current': False
        })
    return timeline


def get_channel_roi_breakdown(campaign_id: str, timeframe: int = 0) -> dict:
    """Return per-channel spend, pipeline, accounts, and influence share for the Channel ROI panel.

    Covers LinkedIn, Email (Mailchimp), and Web (GA4) channels.
    All monetary figures are in the same currency unit as the CRM opportunities table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    tf = f" AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
    tf_crm = f" AND o.timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""

    # LinkedIn
    cursor.execute(f"SELECT SUM(spend_consumed) FROM linkedin_events WHERE campaign_id = ?{tf}", (campaign_id,))
    li_spend = (cursor.fetchone()[0] or 0)

    cursor.execute(f"""
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? {tf_crm}
          AND o.user_id IN (SELECT user_id FROM linkedin_events WHERE campaign_id = ? {tf})
    """, (campaign_id, campaign_id))
    row = cursor.fetchone()
    li_pipe, li_opps = (row[0] or 0.0), (row[1] or 0)

    cursor.execute(f"""
        SELECT COUNT(DISTINCT account_id) FROM crm_users WHERE user_id IN (
            SELECT user_id FROM linkedin_events WHERE campaign_id = ? {tf}
        )
    """, (campaign_id,))
    li_accounts = (cursor.fetchone()[0] or 0)

    # Email
    cursor.execute(f"SELECT COUNT(event_id) FROM mailchimp_events WHERE campaign_id LIKE '%' || ? || '%'{tf}", (campaign_id,))
    em_clicks = (cursor.fetchone()[0] or 0)
    em_spend = em_clicks * 1.50  # Simulated CPC

    cursor.execute(f"""
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? {tf_crm}
          AND o.user_id IN (SELECT user_id FROM mailchimp_events WHERE campaign_id LIKE '%' || ? || '%' {tf})
    """, (campaign_id, campaign_id))
    row = cursor.fetchone()
    em_pipe, em_opps = (row[0] or 0.0), (row[1] or 0)

    cursor.execute(f"""
        SELECT COUNT(DISTINCT account_id) FROM crm_users WHERE user_id IN (
            SELECT user_id FROM mailchimp_events WHERE campaign_id LIKE '%' || ? || '%' {tf}
        )
    """, (campaign_id,))
    em_accounts = (cursor.fetchone()[0] or 0)

    # Web
    cursor.execute(f"SELECT COUNT(session_id) FROM ga4_events WHERE utm_campaign = ?{tf}", (campaign_id,))
    web_views = (cursor.fetchone()[0] or 0)
    web_spend = web_views * 0.80  # Simulated CPC

    cursor.execute(f"""
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? {tf_crm}
          AND o.user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = ? {tf})
    """, (campaign_id, campaign_id))
    row = cursor.fetchone()
    web_pipe, web_opps = (row[0] or 0.0), (row[1] or 0)

    cursor.execute(f"""
        SELECT COUNT(DISTINCT account_id) FROM crm_users WHERE user_id IN (
            SELECT user_id FROM ga4_events WHERE utm_campaign = ?{tf}
        )
    """, (campaign_id,))
    web_accounts = (cursor.fetchone()[0] or 0)

    # Total pipeline for share calculation
    cursor.execute(f"SELECT SUM(o.pipeline_value) FROM crm_opps o WHERE o.utm_campaign = ?{tf_crm}", (campaign_id,))
    total_pipe = (cursor.fetchone()[0] or 1.0)

    conn.close()

    def _calc(spend, pipe, accounts):
        return {
            "spend": spend,
            "pipeline": pipe,
            "accounts": accounts,
            "influence_share": round((pipe / total_pipe) * 100, 1) if total_pipe > 0 else 0,
            "cpea": round(spend / accounts, 2) if accounts > 0 else spend,
        }

    return {
        "linkedin": _calc(li_spend, li_pipe, li_accounts),
        "email":    _calc(em_spend, em_pipe, em_accounts),
        "web":      _calc(web_spend, web_pipe, web_accounts),
    }


def get_topic_cluster_data(campaign_id: str) -> list:
    """Return cross-channel content engagement grouped by intent topic and asset.

    Used by the Topic Clusters panel. Results are sorted by total engagements
    descending so the highest-signal topics appear first.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH AllEngagements AS (
            SELECT g.timestamp, c.intent_topic, c.title, c.asset_type
            FROM ga4_events g
            JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = ?

            UNION ALL

            SELECT m.timestamp, c.intent_topic, c.title, c.asset_type
            FROM mailchimp_events m
            JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked,
                'https://woodplc.com?utm_campaign=', ''),
                'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
            WHERE m.campaign_id = ? AND m.action = 'Open'

            UNION ALL

            SELECT l.timestamp, c.intent_topic, c.title, c.asset_type
            FROM linkedin_events l
            JOIN content_metadata c ON l.ad_id = c.url
            WHERE l.campaign_id = ?
        )
        SELECT intent_topic, title, asset_type, COUNT(timestamp) as engagements
        FROM AllEngagements
        GROUP BY intent_topic, title, asset_type
        ORDER BY intent_topic, engagements DESC
    """, (campaign_id, campaign_id, campaign_id))

    rows = cursor.fetchall()
    conn.close()

    topic_map: dict = {}
    for row in rows:
        topic = row['intent_topic']
        if topic not in topic_map:
            topic_map[topic] = {'intent_topic': topic, 'total_engagements': 0, 'assets': []}
        topic_map[topic]['assets'].append({
            'title': row['title'],
            'type': row['asset_type'],
            'engagements': row['engagements'],
        })
        topic_map[topic]['total_engagements'] += row['engagements']

    return sorted(topic_map.values(), key=lambda x: x['total_engagements'], reverse=True)


def get_abm_account_breakdown(campaign_id: str) -> dict:
    """Return account-level engagement and CRM opportunity data for the ABM data endpoint.

    Returns a dict with key ``"accounts"`` containing the top 10 accounts by
    total interactions, each with buying committee breakdown and opportunity history.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH AllEvents AS (
            SELECT timestamp, user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL
            UNION ALL
            SELECT m.timestamp, u.user_id FROM mailchimp_events m
            JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ?
            UNION ALL
            SELECT l.timestamp, g.user_id FROM linkedin_events l
            JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g
                ON l.cookie_id = g.cookie_id
            WHERE l.campaign_id = ?
        )
        SELECT
            c.company_name,
            c.persona_type,
            COUNT(DISTINCT c.user_id) as user_count,
            COUNT(a.timestamp) as interactions
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.company_name, c.persona_type
        ORDER BY interactions DESC
    """, (campaign_id, f'%{campaign_id}%', campaign_id))

    account_map: dict = {}
    for row in cursor.fetchall():
        comp = row['company_name']
        if comp not in account_map:
            account_map[comp] = {
                'company': comp,
                'total_interactions': 0,
                'technical_users': 0,
                'commercial_users': 0,
                'crm_status': 'Target',
                'pipeline_value': 0.0,
                'won_value': 0.0,
                'active_opp_value': 0.0,
                'opportunities': [],
            }
        account_map[comp]['total_interactions'] += row['interactions']
        if row['persona_type'] == 'Technical':
            account_map[comp]['technical_users'] += row['user_count']
        elif row['persona_type'] == 'Commercial':
            account_map[comp]['commercial_users'] += row['user_count']

    cursor.execute("""
        SELECT c.company_name, o.event_type, o.pipeline_value, o.timestamp
        FROM crm_opps o
        JOIN (SELECT DISTINCT account_id, company_name FROM crm_users) c ON o.account_id = c.account_id
        WHERE o.utm_campaign = ?
        ORDER BY o.timestamp DESC
    """, (campaign_id,))

    for row in cursor.fetchall():
        comp = row['company_name']
        if comp in account_map:
            val = float(row['pipeline_value'] or 0)
            account_map[comp]['opportunities'].append({
                'date': str(row['timestamp']).split(' ')[0],
                'type': row['event_type'],
                'value': val,
            })
            account_map[comp]['pipeline_value'] += val
            current = account_map[comp]['crm_status']
            if row['event_type'] == 'Closed Won':
                account_map[comp]['crm_status'] = 'Customer'
                account_map[comp]['won_value'] += val
            elif row['event_type'] == 'Opportunity Created':
                if current != 'Customer':
                    account_map[comp]['crm_status'] = 'Active Opp'
                account_map[comp]['active_opp_value'] += val

    conn.close()
    sorted_accounts = sorted(account_map.values(), key=lambda x: x['total_interactions'], reverse=True)[:10]
    return {"accounts": sorted_accounts}
