"""
Asset performance & content health - MCP tools

Implements creative analytics, fatigue monitoring, and baseline benchmarking tools:
  - `evaluate_trickle_threshold`: Detects traffic decay (>95% drop sustained for 7 days).
  - `get_asset_impact_matrix`: Composite scoring of assets based on engagement and pipeline influence.
  - `compare_asset_baselines`: Benchmark content performance against historical portfolio averages.
  - `calculate_share_of_voice`: Brand impression and click dominance across marketing channels.
"""

from functools import lru_cache
import datetime
import hashlib
from .common import get_db_connection

def evaluate_trickle_threshold(campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:

    """
    Identify if a campaign's daily traffic dropped >95% from its peak and sustained that for 7 days.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
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
        trickle_threshold = round(threshold)
        avg_recent = round(sum(last_7_days) / len(last_7_days), 1)

        if is_active:
            verdict = "ACTIVE: Campaign traffic is within normal operating range."
            recommendation = "No action required — campaign is generating meaningful traffic."
        else:
            verdict = "INACTIVE: Trickle threshold breached — campaign traffic has effectively ended."
            recommendation = "Consider archiving this campaign and reallocating its remaining budget to active campaigns."
        
        return {
            "is_active": is_active,
            "verdict": verdict,
            "threshold_rule": "Trickle = daily traffic drops >95% from peak AND sustains that for 7+ consecutive days",
            "threshold_breached": not is_active,
            "peak_daily_traffic": peak,
            "trickle_threshold_daily_visits": trickle_threshold,
            "avg_last_7_days_traffic": avg_recent,
            "recommendation": recommendation,
            "status": "Active" if is_active else "Past (Trickle Traffic Detected)"
        }
    except Exception as e:
        raise e


@lru_cache(maxsize=128)
def get_asset_impact_matrix(campaign_id: str = None, timeframe: int = 0, **kwargs) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Timeframe filter logic
        tf_condition = f">= datetime('now', '-{timeframe} days')" if timeframe > 0 else "IS NOT NULL"
        
        query = f"""
        WITH AssetDrops AS (
            -- Web Assets
            SELECT 'Web' as type, 
                   g.page_viewed as asset_name, 
                   COALESCE(c.title, g.page_viewed) as title,
                   MIN(g.timestamp) as release_date, 
                   SUM(CASE WHEN g.timestamp {tf_condition} THEN 1 ELSE 0 END) as engagement, 
                   'ga4' as source
            FROM ga4_events g
            LEFT JOIN content_metadata c ON g.page_viewed = c.url
            WHERE g.utm_campaign = '{campaign_id}' 
            AND g.page_viewed NOT IN ('/services/consulting', '/solutions/asset-performance-optimization', '/contact-sales', '/about/sustainability', '/')
            GROUP BY g.page_viewed
            
            UNION ALL
            
            -- LinkedIn Ads
            SELECT 'LinkedIn' as type, 
                   l.ad_id as asset_name, 
                   COALESCE(c.title, l.ad_id) as title,
                   MIN(l.timestamp) as release_date, 
                   SUM(CASE WHEN l.timestamp {tf_condition} THEN 1 ELSE 0 END) as engagement, 
                   'linkedin' as source
            FROM linkedin_events l 
            LEFT JOIN content_metadata c ON l.ad_id = c.url
            WHERE l.campaign_id = '{campaign_id}' 
            GROUP BY l.ad_id
            
            UNION ALL
            
            -- Mailchimp Emails
            SELECT 'Email' as type, 
                   REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') as asset_name, 
                   COALESCE(c.title, REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '')) as title,
                   MIN(m.timestamp) as release_date, 
                   SUM(CASE WHEN m.timestamp {tf_condition} THEN 1 ELSE 0 END) as engagement, 
                   'mailchimp' as source
            FROM mailchimp_events m 
            LEFT JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
            WHERE m.campaign_id = '{campaign_id}' AND m.action = 'Open' 
            GROUP BY m.url_clicked
        )
        SELECT * FROM AssetDrops WHERE engagement > 0 ORDER BY release_date ASC
        """
        cursor.execute(query)
        assets = [dict(row) for row in cursor.fetchall()]
        
        if not assets:
            conn.close()
            return []

        # Fetch metrics grouped by asset
        web_metrics_query = f"""
            SELECT g.page_viewed as asset_name, COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds,
                   SUM(CASE WHEN u.seniority = 'C-Suite' THEN 20 WHEN u.seniority = 'VP/Director' THEN 10 WHEN u.seniority = 'Manager' THEN 5 ELSE 1 END) as score
            FROM ga4_events g JOIN crm_users u ON g.user_id = u.user_id
            WHERE g.utm_campaign = '{campaign_id}' AND g.timestamp {tf_condition}
            GROUP BY g.page_viewed
        """
        linkedin_metrics_query = f"""
            SELECT l.ad_id as asset_name, COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds,
                   SUM(CASE WHEN u.seniority = 'C-Suite' THEN 20 WHEN u.seniority = 'VP/Director' THEN 10 WHEN u.seniority = 'Manager' THEN 5 ELSE 1 END) as score
            FROM linkedin_events l JOIN ga4_events g ON l.cookie_id = g.cookie_id JOIN crm_users u ON g.user_id = u.user_id
            WHERE l.campaign_id = '{campaign_id}' AND l.timestamp {tf_condition}
            GROUP BY l.ad_id
        """
        email_metrics_query = f"""
            SELECT REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') as asset_name, COUNT(DISTINCT u.account_id) as accts, COUNT(DISTINCT u.user_id) as inds,
                   SUM(CASE WHEN u.seniority = 'C-Suite' THEN 20 WHEN u.seniority = 'VP/Director' THEN 10 WHEN u.seniority = 'Manager' THEN 5 ELSE 1 END) as score
            FROM mailchimp_events m JOIN crm_users u ON m.email = u.email
            WHERE m.campaign_id = '{campaign_id}' AND m.action = 'Open' AND m.timestamp {tf_condition}
            GROUP BY m.url_clicked
        """
        
        metrics_map = {}
        for q in [web_metrics_query, linkedin_metrics_query, email_metrics_query]:
            cursor.execute(q)
            for r in cursor.fetchall():
                metrics_map[r['asset_name']] = {'accts': r['accts'] or 0, 'inds': r['inds'] or 0, 'score': r['score'] or 0}

        # Fetch sparklines grouped by asset
        spark_query = f"""
            SELECT 'Web' as type, page_viewed as asset_name, strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c 
            FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND timestamp {tf_condition} GROUP BY page_viewed, day
            UNION ALL
            SELECT 'LinkedIn' as type, ad_id as asset_name, strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c 
            FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND timestamp {tf_condition} GROUP BY ad_id, day
            UNION ALL
            SELECT 'Email' as type, REPLACE(REPLACE(url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') as asset_name, strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as c 
            FROM mailchimp_events WHERE campaign_id = '{campaign_id}' AND action = 'Open' AND timestamp {tf_condition} GROUP BY url_clicked, day
        """
        cursor.execute(spark_query)
        spark_map = {}
        for r in cursor.fetchall():
            key = f"{r['type']}_{r['asset_name']}"
            if key not in spark_map:
                spark_map[key] = {}
            spark_map[key][r['day']] = r['c']

        # Get all days in the campaign timeframe to pad the sparklines
        cursor.execute(f"SELECT DISTINCT strftime('%Y-%m-%d', timestamp) as day FROM ga4_events WHERE utm_campaign='{campaign_id}' AND timestamp {tf_condition} ORDER BY day")
        all_days = [r['day'] for r in cursor.fetchall()]

        max_score = 0
        for a in assets:
            m = metrics_map.get(a['asset_name'], {'accts': 0, 'inds': 0, 'score': 0})
            a['accounts_activated'] = m['accts']
            a['individuals_engaged'] = m['inds']
            
            final_score = int(m['score'] * (1 + (m['accts'] * 0.1)))
            a['impact_score'] = final_score
            a['impact_formatted'] = f"{final_score:,} pts"
            if final_score > max_score:
                max_score = final_score
                
            a['date'] = str(a['release_date']).split(" ")[0]
            try:
                dt_obj = datetime.datetime.strptime(a['date'], '%Y-%m-%d')
                a['formatted_date'] = dt_obj.strftime('%d %B %Y')
            except:
                a['formatted_date'] = a['date']

        # -----------------------------
        # CRM Attribution Logic (Sprint 1)
        # -----------------------------
        cursor.execute('SELECT o.event_id, o.account_id, o.pipeline_value, o.timestamp, u.company_name FROM crm_opps o JOIN (SELECT DISTINCT account_id, company_name FROM crm_users) u ON o.account_id = u.account_id WHERE o.utm_campaign = ?', (campaign_id,))
        opps = [dict(r) for r in cursor.fetchall()]

        # Map account_id -> list of (asset_name, first_touch)
        q = f'''
        WITH AllEvents AS (
            SELECT 'Web' as type, page_viewed as asset_name, timestamp, user_id FROM ga4_events WHERE user_id IS NOT NULL AND utm_campaign = '{campaign_id}'
            UNION ALL
            SELECT 'Email' as type, REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') as asset_name, m.timestamp, u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id = '{campaign_id}'
            UNION ALL
            SELECT 'LinkedIn' as type, l.ad_id as asset_name, l.timestamp, g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = '{campaign_id}'
        )
        SELECT u.account_id, a.asset_name, MIN(a.timestamp) as first_touch
        FROM AllEvents a
        JOIN crm_users u ON a.user_id = u.user_id
        GROUP BY u.account_id, a.asset_name
        '''
        cursor.execute(q)
        touches = [dict(r) for r in cursor.fetchall()]

        touch_map = {}
        for t in touches:
            if t['asset_name']:
                acc = t['account_id']
                if acc not in touch_map:
                    touch_map[acc] = []
                touch_map[acc].append({'asset_name': t['asset_name'], 'first_touch': t['first_touch']})

        asset_attribution = {}
        for opp in opps:
            acc = opp['account_id']
            opp_val = float(opp['pipeline_value'] or 0)
            opp_time = opp['timestamp']
            
            touched_assets = []
            if acc in touch_map:
                for t in touch_map[acc]:
                    if t['first_touch'] <= opp_time:
                        touched_assets.append(t['asset_name'])
                        
            if touched_assets:
                fractional = opp_val / len(touched_assets)
                for asset in touched_assets:
                    if asset not in asset_attribution:
                        asset_attribution[asset] = {'pipeline_influenced': 0.0, 'fractional_pipeline': 0.0, 'opps': []}
                    
                    asset_attribution[asset]['pipeline_influenced'] += opp_val
                    asset_attribution[asset]['fractional_pipeline'] += fractional
                    asset_attribution[asset]['opps'].append({
                        'company': opp['company_name'],
                        'date': str(opp_time).split(' ')[0],
                        'value': opp_val
                    })

        for a in assets:
            a['pipeline_share'] = round((a['impact_score'] / max_score) * 100) if max_score > 0 else 0
            
            # Attach attribution
            attr = asset_attribution.get(a['asset_name'], {'pipeline_influenced': 0.0, 'fractional_pipeline': 0.0, 'opps': []})
            a['pipeline_influenced'] = attr['pipeline_influenced']
            a['fractional_pipeline'] = attr['fractional_pipeline']
            a['influenced_opps'] = sorted(attr['opps'], key=lambda x: x['date'], reverse=True)
            
            s_dict = spark_map.get(f"{a['type']}_{a['asset_name']}", {})
            a['sparkline'] = [s_dict.get(day, 0) for day in all_days]
            a['sparkline_dates'] = all_days
            
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
        raise e


def compare_asset_baselines(asset_a: str, asset_b: str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    '''Compare two assets based on pipeline influence and conversion metrics rather than vanity views.'''
    try:
        # We need campaign_id for the matrix, default if not provided
        if not campaign_id:
            campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'
            
        assets_data = get_asset_impact_matrix(campaign_id=campaign_id, timeframe=timeframe)
        
        data_a = next((item for item in assets_data if item["asset_name"] == asset_a), None)
        data_b = next((item for item in assets_data if item["asset_name"] == asset_b), None)
        
        if not data_a and not data_b:
            return {"error": f"Neither asset '{asset_a}' nor '{asset_b}' found in campaign {campaign_id}."}
            
        def extract_metrics(data, name):
            if not data:
                return {"name": name, "views_or_clicks": 0, "pipeline_influenced": 0.0, "impact_score": 0}
            return {
                "name": name,
                "views_or_clicks": data.get('engagement', 0),
                "pipeline_influenced": data.get('pipeline_influenced', 0.0),
                "impact_score": data.get('impact_score', 0)
            }
            
        metrics_a = extract_metrics(data_a, asset_a)
        metrics_b = extract_metrics(data_b, asset_b)
        
        pipe_a = metrics_a['pipeline_influenced']
        pipe_b = metrics_b['pipeline_influenced']
        engagement_a = metrics_a['views_or_clicks']
        engagement_b = metrics_b['views_or_clicks']
        fractional_a = data_a.get('fractional_pipeline', 0.0) if data_a else 0.0
        fractional_b = data_b.get('fractional_pipeline', 0.0) if data_b else 0.0

        if pipe_a > pipe_b:
            winner = asset_a
            winner_rationale = f"{asset_a} generated ${pipe_a:,.0f} in influenced pipeline vs ${pipe_b:,.0f} — clear revenue winner."
        elif pipe_b > pipe_a:
            winner = asset_b
            winner_rationale = f"{asset_b} generated ${pipe_b:,.0f} in influenced pipeline vs ${pipe_a:,.0f} — clear revenue winner."
        elif fractional_a > fractional_b:
            winner = asset_a
            winner_rationale = f"Pipeline tied. {asset_a} holds higher fractional pipeline attribution (${fractional_a:,.0f} vs ${fractional_b:,.0f})."
        elif fractional_b > fractional_a:
            winner = asset_b
            winner_rationale = f"Pipeline tied. {asset_b} holds higher fractional pipeline attribution (${fractional_b:,.0f} vs ${fractional_b:,.0f})."
        elif engagement_a > engagement_b:
            winner = asset_a
            winner_rationale = f"No pipeline difference. {asset_a} wins on engagement volume ({engagement_a} vs {engagement_b}). Extend timeframe for stronger signal."
        elif engagement_b > engagement_a:
            winner = asset_b
            winner_rationale = f"No pipeline difference. {asset_b} wins on engagement volume ({engagement_b} vs {engagement_a}). Extend timeframe for stronger signal."
        else:
            winner = "tie"
            winner_rationale = "No meaningful difference on pipeline or engagement. A/B test is inconclusive — extend timeframe or increase sample size."

        low_data_warning = ""
        if engagement_a < 50 and engagement_b < 50:
            low_data_warning = "⚠️ Low statistical confidence: both assets have under 50 engagements. Results may not be reliable — consider extending the timeframe."

        return {
            "timeframe_days": timeframe,
            "asset_a": metrics_a,
            "asset_b": metrics_b,
            "winner": winner,
            "winner_rationale": winner_rationale,
            "statistical_warning": low_data_warning if low_data_warning else "Sufficient data volume for comparison."
        }

    except Exception as e:
        raise e


def calculate_share_of_voice(campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    """
    Deterministic estimate for Topic Share of Voice (SOV) anchored to relative LinkedIn spend.
    In production this would use a third-party intent data API (e.g. Bombora, G2).
    Uses a deterministic seed from campaign_id so results are consistent across calls.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        camp_cond = f"AND campaign_id = '{campaign_id}'" if campaign_id else ""
        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {camp_cond} {tf_cond}")
        actual_spend = cursor.fetchone()["s"] or 0.0
        conn.close()
    except Exception:
        actual_spend = 0.0

    seed_val = int(hashlib.md5((campaign_id or "global").encode()).hexdigest()[:8], 16) % 1000
    market_multiplier = 3.5 + (seed_val % 5) * 0.15
    simulated_market = actual_spend * market_multiplier if actual_spend > 0 else 50000
    wood_pct = round(min(60.0, (actual_spend / simulated_market) * 100), 1) if simulated_market > 0 else 30.0
    aker_pct = round(wood_pct * 0.72, 1)
    baker_pct = round(wood_pct * 0.53, 1)
    others_pct = max(0.0, round(100.0 - wood_pct - aker_pct - baker_pct, 1))

    competitor_avg = round((aker_pct + baker_pct + others_pct) / 3, 1)
    is_leader = wood_pct > aker_pct
    delta = round(wood_pct - aker_pct, 1)
    topic = campaign_id.replace("CMP_LIVE_", "").replace("CMP_PAST_", "").replace("_", " ").title() if campaign_id else "All Topics"
    timeframe_label = "All Time" if timeframe == 0 else f"Last {timeframe} Days"

    return {
        "metric_name": "Topic Share of Voice",
        "topic": topic,
        "timeframe": timeframe_label,
        "our_sov_pct": wood_pct,
        "value": f"{wood_pct}%",
        "raw_value": wood_pct,
        "delta": delta,
        "leader": "Wood Group" if is_leader else "Aker Solutions",
        "competitor_avg": competitor_avg,
        "competitor_distribution": {
            "Wood Group": f"{wood_pct}%",
            "Aker Solutions": f"{aker_pct}%",
            "Baker Hughes": f"{baker_pct}%",
            "Others": f"{others_pct}%"
        },
        "verdict": "Market Leader" if is_leader else "Challenger — close the gap",
        "recommendation": "Maintain spend to defend leadership position." if is_leader else "Increase LinkedIn spend or content cadence to close the SOV gap.",
        "data_source": "Simulated from relative LinkedIn spend (production: Bombora or G2 API)"
    }
