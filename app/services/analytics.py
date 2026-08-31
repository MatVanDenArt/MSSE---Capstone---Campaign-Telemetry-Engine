import sqlite3
import json

import os
DB_PATH = os.getenv("DATABASE_URL", "capstone.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_blended_cpa() -> dict:
    """
    Query total LinkedIn spend divided by total CRM opportunities.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total spend
        cursor.execute("SELECT SUM(spend_consumed) as total_spend FROM linkedin_events")
        spend_row = cursor.fetchone()
        total_spend = spend_row["total_spend"] if spend_row and spend_row["total_spend"] else 0.0
        
        # Get total closed won opps
        cursor.execute("SELECT COUNT(*) as total_opps FROM crm_opps WHERE event_type = 'Closed Won'")
        opps_row = cursor.fetchone()
        total_opps = opps_row["total_opps"] if opps_row and opps_row["total_opps"] else 0
        
        cpa = total_spend / total_opps if total_opps > 0 else 0.0
        
        conn.close()
        return {
            "total_spend": round(total_spend, 2),
            "total_opportunities": total_opps,
            "blended_cpa": round(cpa, 2)
        }
    except Exception as e:
        return {"error": str(e)}

def get_account_penetration(campaign_id: str) -> dict:
    """
    Group users by company_name and seniority to return a summarized dictionary.
    Filtered by those who interacted with the specified campaign.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT c.company_name, c.seniority, COUNT(c.user_id) as user_count
        FROM crm_users c
        WHERE c.user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL)
        GROUP BY c.company_name, c.seniority
        ORDER BY c.company_name, user_count DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        result = {}
        for row in rows:
            company = row["company_name"]
            seniority = row["seniority"]
            count = row["user_count"]
            
            if company not in result:
                result[company] = {}
            result[company][seniority] = count
            
        conn.close()
        return {"account_penetration": result}
    except Exception as e:
        return {"error": str(e)}

def evaluate_trickle_threshold(campaign_id: str) -> dict:
    """
    Identify if a campaign's daily traffic dropped >95% from its peak and sustained that for 7 days.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT date(timestamp) as day, COUNT(*) as daily_visits
        FROM ga4_events
        WHERE utm_campaign = ?
        GROUP BY day
        ORDER BY day ASC
        """
        cursor.execute(query, (campaign_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"is_active": False, "reason": "No traffic data"}
            
        daily_counts = [row["daily_visits"] for row in rows]
        peak = max(daily_counts)
        threshold = peak * 0.05
        
        if len(daily_counts) < 7:
            return {"is_active": True, "reason": "Not enough days to evaluate"}
            
        last_7_days = daily_counts[-7:]
        all_below_threshold = all(count <= threshold for count in last_7_days)
        
        is_active = not all_below_threshold
        
        return {
            "is_active": is_active,
            "peak_traffic": peak,
            "recent_traffic": last_7_days,
            "status": "Active" if is_active else "Past (Trickle Traffic Detected)"
        }
    except Exception as e:
        return {"error": str(e)}

def simulate_budget_shift(channel: str, budget: float) -> dict:
    """
    Use historical baseline conversion rates to mathematically project new pipeline volume based on the new budget.
    """
    try:
        if channel.lower() != "linkedin":
            return {"error": "Only linkedin budget simulation is currently supported."}
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(spend_consumed) as total_spend FROM linkedin_events")
        spend_row = cursor.fetchone()
        historical_spend = spend_row["total_spend"] if spend_row and spend_row["total_spend"] else 0.0
        
        cursor.execute("SELECT SUM(pipeline_value) as total_pipeline FROM crm_opps WHERE event_type = 'Closed Won'")
        pipe_row = cursor.fetchone()
        historical_pipeline = pipe_row["total_pipeline"] if pipe_row and pipe_row["total_pipeline"] else 0.0
        
        conn.close()
        
        if historical_spend == 0:
            return {"error": "No historical spend to calculate baseline."}
            
        roi_multiplier = historical_pipeline / historical_spend
        projected_pipeline = budget * roi_multiplier
        
        return {
            "channel": channel,
            "proposed_budget": round(budget, 2),
            "historical_roi_multiplier": round(roi_multiplier, 2),
            "projected_pipeline_value": round(projected_pipeline, 2)
        }
    except Exception as e:
        return {"error": str(e)}

def get_all_campaigns() -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all unique campaign IDs from linkedin_events
        cursor.execute("SELECT DISTINCT campaign_id FROM linkedin_events WHERE campaign_id IS NOT NULL")
        rows = cursor.fetchall()
        
        campaigns = []
        for row in rows:
            cid = row["campaign_id"]
            name = cid.replace("CMP_LIVE_", "").replace("CMP_PAST_", "").replace("_", " ").title()
            
            # Use the naming convention to determine active status since ghosts generate noise
            is_active = "LIVE" in cid
            
            # Fetch pipeline value
            cursor.execute(f"SELECT SUM(pipeline_value) as total_pipeline FROM crm_opps WHERE utm_campaign = '{cid}'")
            pipeline_row = cursor.fetchone()
            total_pipeline = pipeline_row["total_pipeline"] if pipeline_row and pipeline_row["total_pipeline"] else 0.0
            
            campaigns.append({
                "campaign_id": cid,
                "name": name,
                "is_active": is_active,
                "total_pipeline": total_pipeline
            })
            
        conn.close()
        # Sort active first
        campaigns.sort(key=lambda x: (not x["is_active"], x["name"]))
        return campaigns
    except Exception as e:
        print(f"Error fetching campaigns: {e}")
        return []

def get_kpi_benchmarks(campaign_id: str, timeframe: int = 90) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        def fetch_metrics(campaign_id: str, days: int = None):
            date_filter = ""
            if days:
                date_filter = f"AND timestamp >= datetime('now', '-{days} days')"
                
            cursor.execute(f"SELECT SUM(spend_consumed) as spend FROM linkedin_events WHERE campaign_id = '{campaign_id}' {date_filter}")
            spend = cursor.fetchone()["spend"] or 0.0
            
            cursor.execute(f"""
                SELECT COUNT(*) as conv_count 
                FROM ga4_events 
                WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL {date_filter}
            """)
            conversions = cursor.fetchone()["conv_count"] or 0
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT account_id) as acct_count FROM crm_users 
                WHERE user_id IN (
                    SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND user_id IS NOT NULL {date_filter}
                )
            """)
            accounts = cursor.fetchone()["acct_count"] or 0
            cpa = spend / accounts if accounts > 0 else 0.0
            
            return {"spend": spend, "accounts": accounts, "cpa": cpa, "conversions": conversions}

        live_metrics = fetch_metrics(campaign_id, timeframe)
        
        date_filter = f"AND timestamp < datetime('2026-06-30', '-{timeframe} days')"
        
        cursor.execute(f"SELECT SUM(spend_consumed) as spend FROM linkedin_events WHERE 1=1 {date_filter}")
        baseline_spend = cursor.fetchone()["spend"] or 0.0
        
        cursor.execute(f"""
            SELECT COUNT(*) as conv_count 
            FROM ga4_events 
            WHERE user_id IS NOT NULL {date_filter}
        """)
        baseline_conversions = cursor.fetchone()["conv_count"] or 0
        
        cursor.execute(f"SELECT COUNT(DISTINCT account_id) as acct_count FROM crm_users WHERE user_id IN (SELECT user_id FROM ga4_events WHERE user_id IS NOT NULL {date_filter})")
        baseline_accounts = cursor.fetchone()["acct_count"] or 0
        baseline_cpa = baseline_spend / baseline_accounts if baseline_accounts > 0 else 0.0
        
        baseline_metrics = {"spend": baseline_spend, "accounts": baseline_accounts, "cpa": baseline_cpa, "conversions": baseline_conversions}
        
        def calc_diff(current, baseline, lower_is_better=False):
            if baseline == 0: return 0, False
            diff = ((current - baseline) / baseline) * 100
            is_good = (diff < 0) if lower_is_better else (diff > 0)
            return round(diff, 1), is_good
            
        spend_diff, spend_good = calc_diff(live_metrics["spend"], baseline_metrics["spend"], lower_is_better=False)
        accounts_diff, accounts_good = calc_diff(live_metrics["accounts"], baseline_metrics["accounts"], lower_is_better=False)
        cpa_diff, cpa_good = calc_diff(live_metrics["cpa"], baseline_metrics["cpa"], lower_is_better=True)
        conv_diff, conv_good = calc_diff(live_metrics["conversions"], baseline_metrics["conversions"], lower_is_better=False)
        
        # Generate 14-day sparklines
        def get_sparkline(metric_type):
            data = []
            for i in range(13, -1, -1):
                day_start = f"datetime('2026-06-30', '-{i+1} days')"
                day_end = f"datetime('2026-06-30', '-{i} days')"
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
                    cursor.execute(f"SELECT COUNT(DISTINCT account_id) as c FROM crm_users WHERE user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}')")
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
                "conversions": live_metrics["conversions"]
            },
            "comparisons": {
                "spend": {"value": spend_diff, "good": spend_good},
                "accounts": {"value": accounts_diff, "good": accounts_good},
                "cpa": {"value": cpa_diff, "good": cpa_good},
                "conversions": {"value": conv_diff, "good": conv_good},
            },
            "sparklines": sparklines
        }
    except Exception as e:
        print(f"Error in benchmarks: {e}")
        return {
            "live": {"spend": 0, "accounts": 0, "cpa": 0, "conversions": 0}, 
            "comparisons": {}, 
            "sparklines": {
                "spend": [0]*14,
                "accounts": [0]*14,
                "cpa": [0]*14,
                "conversions": [0]*14
            }
        }


def get_campaign_start_date(campaign_id: str) -> str:
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
        print(e)
        return "Unknown"

def format_pipeline(val: float) -> str:
    if not val:
        return "$0"
    if val >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:.0f}"

def get_asset_impact_matrix(campaign_id: str, timeframe: int = 90) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If timeframe is 0 or large, treat it as All Time. Using 10000 for all time.
        tf_condition = "IS NOT NULL"  # Always show all-time impact in the matrix to reflect full asset performance
        
        query = f"""
        WITH AssetDrops AS (
            -- Web Assets
            SELECT 
                'Web' as type,
                page_viewed as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'ga4' as source
            FROM ga4_events 
            WHERE utm_campaign = '{campaign_id}' AND timestamp {tf_condition}
            AND page_viewed NOT IN ('/services/consulting', '/solutions/asset-performance-optimization', '/contact-sales', '/about/sustainability')
            GROUP BY page_viewed
            
            UNION ALL
            
            -- LinkedIn Ads
            SELECT 
                'LinkedIn' as type,
                ad_id as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'linkedin' as source
            FROM linkedin_events
            WHERE campaign_id = '{campaign_id}' AND timestamp {tf_condition}
            GROUP BY ad_id
            
            UNION ALL
            
            -- Mailchimp Emails
            SELECT
                'Email' as type,
                campaign_id as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'mailchimp' as source
            FROM mailchimp_events
            WHERE campaign_id LIKE '%{campaign_id}%' AND action = 'Open' AND timestamp {tf_condition}
            GROUP BY campaign_id
        )
        SELECT * FROM AssetDrops ORDER BY release_date ASC
        """
        cursor.execute(query)
        assets = [dict(row) for row in cursor.fetchall()]
        
        # Find the max score to calculate share % later
        max_score = 0
        
        for a in assets:
            if a['type'] == 'Web':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds, 
                       SUM(CASE 
                           WHEN u.seniority = 'C-Suite' THEN 20 
                           WHEN u.seniority = 'VP/Director' THEN 10 
                           WHEN u.seniority = 'Manager' THEN 5 
                           ELSE 1 
                       END) as score
                FROM crm_users u
                WHERE u.user_id IN (
                    SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{a['asset_name']}' AND user_id IS NOT NULL AND timestamp {tf_condition}
                )
                """
            elif a['type'] == 'LinkedIn':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds, 
                       SUM(CASE 
                           WHEN u.seniority = 'C-Suite' THEN 20 
                           WHEN u.seniority = 'VP/Director' THEN 10 
                           WHEN u.seniority = 'Manager' THEN 5 
                           ELSE 1 
                       END) as score
                FROM crm_users u
                WHERE u.user_id IN (
                    SELECT g.user_id FROM ga4_events g
                    JOIN linkedin_events l ON g.cookie_id = l.cookie_id
                    WHERE l.ad_id = '{a['asset_name']}' AND l.campaign_id = '{campaign_id}' AND g.user_id IS NOT NULL AND l.timestamp {tf_condition}
                )
                """
            elif a['type'] == 'Email':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds, 
                       SUM(CASE 
                           WHEN u.seniority = 'C-Suite' THEN 20 
                           WHEN u.seniority = 'VP/Director' THEN 10 
                           WHEN u.seniority = 'Manager' THEN 5 
                           ELSE 1 
                       END) as score
                FROM crm_users u
                WHERE u.email IN (
                    SELECT email FROM mailchimp_events WHERE campaign_id = '{a['asset_name']}' AND timestamp {tf_condition}
                )
                """
            
            cursor.execute(q)
            res = cursor.fetchone()
            accts = res['accts'] or 0
            inds = res['inds'] or 0
            base_score = res['score'] or 0
            
            a['accounts_activated'] = accts
            a['individuals_engaged'] = inds
            
            # Account breadth multiplier
            final_score = int(base_score * (1 + (accts * 0.1)))
            a['impact_score'] = final_score
            a['impact_formatted'] = f"{final_score:,} pts"
            if final_score > max_score:
                max_score = final_score
            a['date'] = str(a['release_date']).split(" ")[0]
            import datetime
            try:
                dt_obj = datetime.datetime.strptime(a['date'], '%Y-%m-%d')
                a['formatted_date'] = dt_obj.strftime('%d %B %Y')
            except:
                a['formatted_date'] = a['date']
            
        # Get all days in the campaign timeframe to pad the sparklines
        cursor.execute(f"SELECT DISTINCT strftime('%Y-%m-%d', timestamp) as day FROM ga4_events WHERE utm_campaign='{campaign_id}' AND timestamp {tf_condition} ORDER BY day")
        all_days = [r['day'] for r in cursor.fetchall()]

        for a in assets:
            a['pipeline_share'] = round((a['impact_score'] / max_score) * 100) if max_score > 0 else 0
            
            spark_dict = {}
            if a['type'] == 'Web':
                cursor.execute(f"SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{a['asset_name']}' AND timestamp {tf_condition} GROUP BY day")
            elif a['type'] == 'LinkedIn':
                cursor.execute(f"SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{a['asset_name']}' AND timestamp {tf_condition} GROUP BY day")
            elif a['type'] == 'Email':
                cursor.execute(f"SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c FROM mailchimp_events WHERE campaign_id = '{a['asset_name']}' AND timestamp {tf_condition} GROUP BY day")
            
            for r in cursor.fetchall():
                spark_dict[r['day']] = r['c']
                
            a['sparkline'] = [spark_dict.get(day, 0) for day in all_days]
            
            # AI Fatigue Detection
            non_zero_days = [x for x in a['sparkline'] if x > 0]
            if non_zero_days:
                peak = max(non_zero_days)
                recent_traffic = sum(a['sparkline'][-28:]) if len(a['sparkline']) >= 28 else sum(a['sparkline'])
                if peak > 20 and recent_traffic < peak * 0.1:
                    a['health'] = 'Fatigued'
                    a['badge_class'] = 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                    if a['type'] == 'Web':
                        a['ai_recommendation'] = 'Traffic dropping rapidly. Refresh page content or feature this page in the next email newsletter to reactivate intent.'
                    elif a['type'] == 'LinkedIn':
                        a['ai_recommendation'] = 'Ad fatigue detected. Rotate creative or pause campaign to preserve budget.'
                    else:
                        a['ai_recommendation'] = 'Engagement trickled off. Consider a follow-up sequence with fresh messaging.'
        
        conn.close()
        return assets
    except Exception as e:
        print(f"Error in impact matrix: {e}")
        return []

def generate_strategic_tldr(metrics: dict) -> str:
    from google import genai
    from google.genai import types
    try:
        from app.services.llm_rotator import get_genai_client
        
        prompt = f"You are an AI Analyst. Review these campaign metrics: {metrics}. Write a strict 2-3 sentence executive summary. Highlight pipeline generated and CPA anomalies. Format it in plain text without markdown."
        response = None
        last_err = None
        for _ in range(3):
            try:
                client = get_genai_client()
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                break
            except Exception as e:
                last_err = e
                
        if not response:
            raise last_err
        return response.text
    except Exception as e:
        return "AI Insight temporarily unavailable. Please verify API Key configuration."

# --- Advanced Analytics for Sprint B ---
def get_timeline_chart_data(campaign_id: str, timeframe: int = 90) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determine grouping and timeframe conditions
        tf_condition = f"AND timestamp >= datetime('2026-06-30', '-{timeframe} days')" if timeframe > 0 else ""
        date_format = "'%Y-%m-%d'"
        
        # Group traffic
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM ga4_events WHERE utm_campaign = '{campaign_id}' {tf_condition} GROUP BY period ORDER BY period")
        traffic_rows = cursor.fetchall()
        
        # Group CRM opps
        cursor.execute(f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM crm_opps WHERE utm_campaign = '{campaign_id}' {tf_condition} GROUP BY period ORDER BY period")
        opps_rows = cursor.fetchall()
        
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
        return {
            "labels": sorted_periods,
            "traffic": [data_map[p]["traffic"] for p in sorted_periods],
            "opps": [data_map[p]["opps"] for p in sorted_periods],
            "ads": [data_map[p]["ads"] for p in sorted_periods],
            "email": [data_map[p]["email"] for p in sorted_periods]
        }
    except Exception as e:
        print(e)
        return {"labels": [], "traffic": [], "opps": [], "ads": [], "email": []}

def get_asset_fatigue(campaign_id: str, timeframe: int = 0) -> list:
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
            cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{p['page_viewed']}' AND timestamp >= date('2026-06-30', '-30 days') GROUP BY dt ORDER BY dt")
            recent_rows = cursor.fetchall()
            
            # Get prior 30 days sum
            cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{p['page_viewed']}' AND timestamp >= date('2026-06-30', '-60 days') AND timestamp < date('2026-06-30', '-30 days')")
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
        print(e)
        return []

def generate_next_best_actions(campaign_id: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        actions = []
        
        # Rule 1: High Spend, Zero CRM Opps
        cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE campaign_id = '{campaign_id}'")
        spend = cursor.fetchone()["s"] or 0
        
        cursor.execute(f"SELECT COUNT(*) as c FROM crm_opps WHERE utm_campaign = '{campaign_id}'")
        opps = cursor.fetchone()["c"] or 0
        
        if spend > 1000 and opps == 0:
            actions.append({
                "id": "ACT_001",
                "severity": "high",
                "icon": "fa-triangle-exclamation text-rose-500",
                "message": f"LinkedIn spend has exceeded ${spend:,.0f} with zero pipeline generated.",
                "button_text": "Pause Ads",
                "endpoint": f"/api/dashboard/execute-action?type=pause_ads&campaign_id={campaign_id}"
            })
            
        # Rule 2: High Traffic, Low Conversion (Form fills)
        cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}'")
        traffic = cursor.fetchone()["c"] or 0
        cursor.execute(f"SELECT COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%'")
        mc = cursor.fetchone()["c"] or 0
        
        if traffic > 100 and mc < (traffic * 0.02):
            actions.append({
                "id": "ACT_002",
                "severity": "medium",
                "icon": "fa-circle-exclamation text-amber-500",
                "message": f"Traffic is healthy ({traffic} visits) but conversion is below 2%.",
                "button_text": "A/B Test Landing Page",
                "endpoint": f"/api/dashboard/execute-action?type=ab_test&campaign_id={campaign_id}"
            })
            
        conn.close()
        return actions
    except Exception as e:
        print(e)
        return []

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

def get_audience_network_data() -> dict:
    """
    Returns nodes and links for a D3 force-directed graph, as well as a list of users for card view.
    Interaction count is based on raw sum of mc_events and ga4_events from master_summary.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get top 50 users by interaction to keep the graph readable
        query = f"""
        SELECT user_id, account_id, company_name, first_name, last_name, seniority, job_title,
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
            job_title = row["job_title"]
            
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
                "title": job_title,
                "seniority": seniority,
                "interactions": interactions,
                "assets": structured_assets # Send all assets to the frontend modal
            })
            
        return {"nodes": nodes, "links": links, "users": users}
    except Exception as e:
        return {"error": str(e)}

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
        import traceback
        print(traceback.format_exc())
        return {"error": str(e)}

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
        import traceback
        print(traceback.format_exc())
        return []



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

def get_ui_lab_funnel_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM ga4_events WHERE utm_campaign = ?", (campaign_id,))
        visitors = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM ga4_events WHERE utm_campaign = ? AND bounce_flag = 0", (campaign_id,))
        engaged = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL", (campaign_id,))
        known = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id), SUM(pipeline_value) FROM crm_opps WHERE utm_campaign = ?", (campaign_id,))
        pipe_row = cursor.fetchone()
        pipeline = pipe_row[0] or 0
        pipeline_val = pipe_row[1] or 0.0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id), SUM(pipeline_value) FROM crm_opps WHERE utm_campaign = ? AND event_type = 'Closed Won'", (campaign_id,))
        won_row = cursor.fetchone()
        won = won_row[0] or 0
        won_val = won_row[1] or 0.0
        
        conn.close()
        return {
            'visitors': visitors, 
            'engaged': engaged, 
            'known': known, 
            'pipeline': pipeline, 
            'pipeline_val': pipeline_val,
            'won': won,
            'won_val': won_val
        }
    except Exception as e:
        return {'error': str(e)}

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
        return {'error': str(e)}

def get_prioritized_sales_targets(campaign_id: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get all users who interacted with this campaign across Web, Email, and LinkedIn
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
            COUNT(a.timestamp) as campaign_interactions,
            MAX(a.timestamp) as last_active
        FROM AllEvents a
        JOIN crm_users c ON a.user_id = c.user_id
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority
        '''
        cursor.execute(query, (campaign_id, f'%{campaign_id}%', campaign_id))
        all_users = cursor.fetchall()
        
        # 2. Get Account Momentum (Total unique users per company engaged in this campaign)
        acct_query = '''
        WITH AllEvents AS (
            SELECT user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL
            UNION ALL
            SELECT u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ?
            UNION ALL
            SELECT g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = ?
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
        import traceback
        print(f"Error fetching prioritized targets: {e}")
        traceback.print_exc()
        return []


def get_asset_personas(campaign_id: str, asset_name: str, asset_type: str, timeframe: int = 0) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
    # first find users who interacted with the asset
    if asset_type == 'Web':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(g.session_id) as asset_interactions
        FROM crm_users u
        JOIN ga4_events g ON u.user_id = g.user_id
        WHERE g.utm_campaign = ? AND g.page_viewed = ? {tf_condition.replace('timestamp', 'g.timestamp')}
        GROUP BY u.user_id
        """
    elif asset_type == 'Email':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(m.timestamp) as asset_interactions
        FROM crm_users u
        JOIN mailchimp_events m ON u.email = m.email
        WHERE m.campaign_id LIKE ? AND m.url_clicked = ? {tf_condition.replace('timestamp', 'm.timestamp')}
        GROUP BY u.user_id
        """
    elif asset_type == 'LinkedIn':
        query = f"""
        SELECT u.user_id, u.first_name, u.last_name, u.company_name, u.seniority, COUNT(l.timestamp) as asset_interactions
        FROM crm_users u
        JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON u.user_id = g.user_id
        JOIN linkedin_events l ON g.cookie_id = l.cookie_id
        WHERE l.campaign_id = ? AND l.ad_id = ? {tf_condition.replace('timestamp', 'l.timestamp')}
        GROUP BY u.user_id
        """
    
    param1 = f'%{campaign_id}%' if asset_type == 'Email' else campaign_id
    cursor.execute(query, (param1, asset_name))
    rows = cursor.fetchall()
    
    users = []
    for r in rows:
        # Get individual touchpoints (assets) for this specific user
        uid = str(r['user_id'])
        cursor.execute("""
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
        """, (campaign_id, uid, f'%{campaign_id}%', uid, campaign_id, uid))
        assets_rows = cursor.fetchall()
        
        timeline = []
        for ar in assets_rows:
            nm = ar['asset']
            if not nm: nm = 'Homepage'
            elif nm.startswith('/') or nm.startswith('email-') or nm.startswith('li-'):
                nm = nm.replace('/', ' ').replace('-', ' ').title().strip()
            
            # format date
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
                'is_current': ar['asset'] == asset_name
            })
        
        total_interactions = len(timeline)
        
        users.append({
            'name': f"{r['first_name']} {r['last_name']}",
            'company': r['company_name'],
            'seniority': r['seniority'],
            'interactions': total_interactions, 
            'id': uid,
            'timeline': timeline,
            'remaining_interactions': 0
        })
        
    conn.close()
    return users

def get_funnel_drilldown_data(campaign_id: str, stage: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        data = []
        if stage == 'known_users':
            cursor.execute("""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority 
                FROM ga4_events e 
                JOIN crm_users u ON e.user_id = u.user_id 
                WHERE e.utm_campaign = ? AND e.user_id IS NOT NULL
                LIMIT 50
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": None
                })
        elif stage == 'opportunities':
            cursor.execute("""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority, SUM(o.pipeline_value) as value
                FROM crm_opps o 
                JOIN crm_users u ON o.user_id = u.user_id 
                WHERE o.utm_campaign = ?
                GROUP BY u.user_id
                ORDER BY value DESC
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": r[5]
                })
        elif stage == 'contracts':
            cursor.execute("""
                SELECT DISTINCT u.company_name, u.first_name, u.last_name, u.job_title, u.seniority, SUM(o.pipeline_value) as value
                FROM crm_opps o 
                JOIN crm_users u ON o.user_id = u.user_id 
                WHERE o.utm_campaign = ? AND o.event_type = 'Closed Won'
                GROUP BY u.user_id
                ORDER BY value DESC
            """, (campaign_id,))
            rows = cursor.fetchall()
            for r in rows:
                data.append({
                    "company_name": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "job_title": r[3],
                    "seniority": r[4],
                    "value": r[5]
                })
        
        conn.close()
        return data
    except Exception as e:
        print(f"Error in drilldown: {e}")
        return []
