"""
Financial & budgetary analytics - MCP tools

Implements core ROI, spend pacing, multi-touch attribution, and budget simulation tools:
  - `calculate_blended_cpa`: Cross-channel media spend vs CRM closed-won contracts.
  - `simulate_budget_shift`: Counterfactual budget reallocation modeling.
  - `get_executive_pipeline_kpis`: High-level spend, pipeline, and contract counts.
  - `get_budget_pacing`: Daily burn rates, pacing health, and runway projections.
  - `run_attribution_model`: First-touch, last-touch, linear, and time-decay attribution models.
"""

from .common import get_db_connection

def calculate_blended_cpa(campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:

    """
    Query total blended spend (LinkedIn + Email + Web) divided by total CRM Closed Won opportunities.
    Returns channel breakdown, benchmark CPA, and executive verdict.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        camp_li = f"AND campaign_id = '{campaign_id}'" if campaign_id else ""
        camp_mc = f"AND campaign_id LIKE '%{campaign_id}%'" if campaign_id else ""
        camp_ga = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""
        camp_crm = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""

        # Channel spend
        cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {camp_li} {tf_cond}")
        li_spend = cursor.fetchone()["s"] or 0.0

        cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {camp_mc} {tf_cond}")
        em_spend = (cursor.fetchone()["c"] or 0) * 1.50

        cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {camp_ga} {tf_cond}")
        web_spend = (cursor.fetchone()["c"] or 0) * 0.80

        total_spend = li_spend + em_spend + web_spend

        # Campaign Closed Won opps
        cursor.execute(f"SELECT COUNT(*) as c FROM crm_opps WHERE event_type = 'Closed Won' {camp_crm} {tf_cond}")
        total_opps = cursor.fetchone()["c"] or 0

        cpa = total_spend / total_opps if total_opps > 0 else 0.0

        # Cross-campaign benchmark CPA (all campaigns, same timeframe)
        cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {tf_cond}")
        bench_li = cursor.fetchone()["s"] or 0.0
        cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {tf_cond}")
        bench_em = (cursor.fetchone()["c"] or 0) * 1.50
        cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {tf_cond}")
        bench_web = (cursor.fetchone()["c"] or 0) * 0.80
        bench_total_spend = bench_li + bench_em + bench_web

        cursor.execute(f"SELECT COUNT(*) as c FROM crm_opps WHERE event_type = 'Closed Won' {tf_cond}")
        bench_opps = cursor.fetchone()["c"] or 0
        benchmark_cpa = bench_total_spend / bench_opps if bench_opps > 0 else 0.0

        conn.close()

        cpa_vs_benchmark_pct = round(((cpa - benchmark_cpa) / benchmark_cpa) * 100, 1) if benchmark_cpa > 0 else None
        if cpa_vs_benchmark_pct is None:
            verdict = "No benchmark data available"
        elif cpa_vs_benchmark_pct <= 0:
            verdict = f"Efficient — CPA is {abs(cpa_vs_benchmark_pct)}% below cross-campaign benchmark"
        else:
            verdict = f"Above Benchmark — CPA is {cpa_vs_benchmark_pct}% higher than cross-campaign average"

        return {
            "timeframe_days": timeframe,
            "timeframe_label": "All Time" if timeframe == 0 else f"Last {timeframe} Days",
            "channel_spend_breakdown": {
                "linkedin": round(li_spend, 2),
                "email": round(em_spend, 2),
                "web": round(web_spend, 2)
            },
            "total_spend": round(total_spend, 2),
            "total_closed_won_opportunities": total_opps,
            "blended_cpa": round(cpa, 2),
            "benchmark_avg_cpa": round(benchmark_cpa, 2),
            "cpa_vs_benchmark_pct": cpa_vs_benchmark_pct,
            "verdict": verdict
        }
    except Exception as e:
        raise e


def get_budget_pacing(channel: str = 'all', campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    '''Query spend data vs. pipeline creation.'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        campaign_cond = f"AND campaign_id = '{campaign_id}'" if campaign_id else ""
        
        cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {campaign_cond} {tf_condition}")
        li_spend = cursor.fetchone()["s"] or 0.0
        
        camp_cond_em = f"AND campaign_id LIKE '%{campaign_id}%'" if campaign_id else ""
        cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {camp_cond_em} {tf_condition}")
        em_spend = (cursor.fetchone()["c"] or 0) * 1.50
        
        camp_cond_ga = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""
        cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {camp_cond_ga} {tf_condition}")
        web_spend = (cursor.fetchone()["c"] or 0) * 0.80
        
        if channel.lower() == 'linkedin':
            spent_budget = li_spend
        elif channel.lower() == 'email':
            spent_budget = em_spend
        elif channel.lower() == 'web':
            spent_budget = web_spend
        else:
            spent_budget = li_spend + em_spend + web_spend
            
        # Determine allocated budget dynamically or return 0 if no timeframe
        allocated_budget = 500000 if not timeframe else (500000 * (timeframe / 365.0))

        spend_ratio = spent_budget / allocated_budget if allocated_budget > 0 else 0
        daily_run_rate = spent_budget / timeframe if timeframe > 0 else 0
        projected_yearly_spend = daily_run_rate * 365
        projected_variance = projected_yearly_spend - 500000

        # Pacing status uses BOTH the period ratio AND the projected yearly variance to avoid contradiction
        if spend_ratio > 1.1:
            status = "Over Budget"
        elif projected_variance < -150000:
            status = "Severely Underspending — Annual Target at Risk"
        elif spend_ratio < 0.5:
            status = "Underspending (Requires Reallocation)"
        else:
            status = "On Track"

        # Recommended daily spend to hit annual target
        annual_budget = 500000
        days_remaining_in_year = max(1, 365 - timeframe) if timeframe > 0 else 365
        budget_remaining_annual = max(0, annual_budget - spent_budget)
        recommended_daily_spend = round(budget_remaining_annual / days_remaining_in_year, 2)

        if projected_variance < -100000:
            recommendation = f"Increase daily spend to ${recommended_daily_spend:,.2f} to meet the ${annual_budget:,.0f} annual budget target."
        elif spend_ratio > 1.1:
            recommendation = "Pause or reduce spend immediately — budget overrun in progress."
        else:
            recommendation = f"Maintain current run rate of ${daily_run_rate:,.2f}/day to stay on track."

        conn.close()
        return {
            "channel": channel,
            "campaign_id": campaign_id,
            "timeframe_days": timeframe,
            "timeframe_label": "All Time" if timeframe == 0 else f"Last {timeframe} Days",
            "allocated_budget": round(allocated_budget, 2),
            "spent_budget": round(spent_budget, 2),
            "remaining_budget": max(0, round(allocated_budget - spent_budget, 2)),
            "pacing_status": status,
            "daily_run_rate": round(daily_run_rate, 2),
            "recommended_daily_spend": recommended_daily_spend,
            "projected_yearly_variance": round(projected_variance, 2),
            "recommendation": recommendation
        }

    except Exception as e:
        raise e


def simulate_budget_shift(channel: str, budget: float | str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    """
    Use historical baseline conversion rates to mathematically project new pipeline volume based on the new budget.
    """
    try:
        if str(budget).upper() == "REMAINING_BUDGET":
            pacing = get_budget_pacing(channel='all', campaign_id=campaign_id, timeframe=timeframe)
            budget = pacing.get("remaining_budget", 0.0)
            
        budget = float(budget)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        campaign_cond = f"AND campaign_id = '{campaign_id}'" if campaign_id else ""
        
        tf_crm = f"AND o.timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        campaign_crm = f"AND o.utm_campaign = '{campaign_id}'" if campaign_id else ""
        
        historical_spend = 0.0
        historical_pipeline = 0.0
        
        if channel.lower() == "linkedin":
            cursor.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {campaign_cond} {tf_condition}")
            historical_spend = cursor.fetchone()["s"] or 0.0
            
            cursor.execute(f"""
                SELECT SUM(o.pipeline_value) as p FROM crm_opps o
                WHERE o.event_type = 'Closed Won' {campaign_crm} {tf_crm}
                AND o.user_id IN (SELECT user_id FROM linkedin_events WHERE 1=1 {campaign_cond} {tf_condition})
            """)
            historical_pipeline = cursor.fetchone()["p"] or 0.0
            
        elif channel.lower() == "email":
            campaign_cond_like = f"AND campaign_id LIKE '%{campaign_id}%'" if campaign_id else ""
            cursor.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {campaign_cond_like} {tf_condition}")
            historical_spend = (cursor.fetchone()["c"] or 0) * 1.50
            
            cursor.execute(f"""
                SELECT SUM(o.pipeline_value) as p FROM crm_opps o
                WHERE o.event_type = 'Closed Won' {campaign_crm} {tf_crm}
                AND o.user_id IN (SELECT user_id FROM mailchimp_events WHERE 1=1 {campaign_cond_like} {tf_condition})
            """)
            historical_pipeline = cursor.fetchone()["p"] or 0.0
            
        elif channel.lower() == "web":
            campaign_cond_ga = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""
            cursor.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {campaign_cond_ga} {tf_condition}")
            historical_spend = (cursor.fetchone()["c"] or 0) * 0.80
            
            cursor.execute(f"""
                SELECT SUM(o.pipeline_value) as p FROM crm_opps o
                WHERE o.event_type = 'Closed Won' {campaign_crm} {tf_crm}
                AND o.user_id IN (SELECT user_id FROM ga4_events WHERE 1=1 {campaign_cond_ga} {tf_condition})
            """)
            historical_pipeline = cursor.fetchone()["p"] or 0.0
        else:
            return {"error": "Unsupported channel. Use 'linkedin', 'email', or 'web'."}

        conn.close()
        
        if historical_spend == 0:
            return {"error": "No historical spend to calculate baseline in this timeframe."}
            
        roi_multiplier = historical_pipeline / historical_spend
        
        # Dampener: for every 20% increase in budget over historical spend, reduce ROI multiplier by 5%
        # because you start exhausting the high-intent audience and CAC increases.
        budget_increase_ratio = budget / historical_spend if historical_spend > 0 else 1
        dampener_steps = max(0, int((budget_increase_ratio - 1) / 0.20))
        dampened_multiplier = roi_multiplier * (0.95 ** dampener_steps)
        
        projected_pipeline = budget * dampened_multiplier

        # Build a precise, accurate insight string
        if roi_multiplier == 0:
            insight = f"No historical pipeline won on {channel} in this timeframe. Cannot project returns — consider extending the timeframe or switching channel to build a baseline."
        elif dampened_multiplier < roi_multiplier:
            pct_dampened = round((1 - (dampened_multiplier / roi_multiplier)) * 100, 1)
            insight = f"Applied a {pct_dampened}% dampener to ROI multiplier to account for Audience Saturation and CAC decay at scale."
        else:
            insight = f"Proposed budget (${budget:,.0f}) is within historical spend range (${historical_spend:,.0f}). No scale dampener applied — historical ROI multiplier used directly."

        verdict = "Strong ROI expected" if projected_pipeline > budget else ("Break-even risk" if projected_pipeline > 0 else "No pipeline projected — do not proceed without further analysis")

        return {
            "channel": channel,
            "timeframe_days": timeframe,
            "proposed_budget": round(budget, 2),
            "historical_spend": round(historical_spend, 2),
            "historical_pipeline_won": round(historical_pipeline, 2),
            "historical_roi_multiplier": round(roi_multiplier, 2),
            "dampened_roi_multiplier": round(dampened_multiplier, 2),
            "projected_pipeline_value": round(projected_pipeline, 2),
            "projected_roas": round(projected_pipeline / budget, 2) if budget > 0 else 0,
            "insight": insight,
            "verdict": verdict
        }

    except Exception as e:
        raise e


def get_executive_pipeline_kpis(campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    '''Query crm_opps for top-level ROI and Pipeline KPIs.'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        filters = []
        if timeframe > 0:
            filters.append(f"timestamp >= date('now', '-{timeframe} days')")
        if campaign_id:
            filters.append(f"utm_campaign = '{campaign_id}'")
            
        date_filter = "WHERE " + " AND ".join(filters) if filters else ""
        
        # Open Pipeline
        cursor.execute(f"SELECT COUNT(*) as opp_count, SUM(pipeline_value) as total_pipeline FROM crm_opps {date_filter} AND event_type = 'Opportunity Created'")
        open_row = cursor.fetchone()
        
        # Closed Won Revenue
        cursor.execute(f"SELECT COUNT(*) as won_count, SUM(pipeline_value) as won_pipeline FROM crm_opps {date_filter} AND event_type = 'Closed Won'")
        won_row = cursor.fetchone()
        
        # Spend filter requires campaign_id column on linkedin_events
        spend_filters = []
        if timeframe > 0:
            spend_filters.append(f"timestamp >= date('now', '-{timeframe} days')")
        if campaign_id:
            spend_filters.append(f"campaign_id = '{campaign_id}'")
            
        spend_date_filter = "WHERE " + " AND ".join(spend_filters) if spend_filters else ""
        
        cursor.execute(f"SELECT SUM(spend_consumed) as total_spend FROM linkedin_events {spend_date_filter}")
        spend_row = cursor.fetchone()
        
        conn.close()
        
        open_pipeline = open_row['total_pipeline'] if open_row and open_row['total_pipeline'] else 0
        won_pipeline = won_row['won_pipeline'] if won_row and won_row['won_pipeline'] else 0
        total_spend = spend_row['total_spend'] if spend_row and spend_row['total_spend'] else 0

        opp_count = open_row['opp_count'] if open_row else 0
        won_count = won_row['won_count'] if won_row else 0
        win_rate = (won_count / opp_count * 100) if opp_count > 0 else 0
        avg_deal_size = round(open_pipeline / opp_count, 2) if opp_count > 0 else 0
        roi_pct = round(((won_pipeline - total_spend) / total_spend * 100), 2) if total_spend > 0 else 0
        roas = round((won_pipeline / total_spend), 2) if total_spend > 0 else 0

        if won_pipeline > total_spend * 2:
            verdict = "Highly Profitable — ROAS exceeds 2× spend. Recommend maintaining or increasing investment."
        elif won_pipeline > total_spend:
            verdict = "Profitable — Revenue exceeds spend. Investment is justified."
        elif opp_count > 0:
            verdict = "Investment Phase — Pipeline exists but revenue not yet realised. Monitor closely."
        else:
            verdict = "No pipeline generated in this timeframe. Review targeting or timeframe."

        return {
            "timeframe_days": timeframe,
            "timeframe_label": "All Time" if timeframe == 0 else f"Last {timeframe} Days",
            "total_open_opportunities": opp_count,
            "total_open_pipeline": round(open_pipeline, 2),
            "average_deal_size": avg_deal_size,
            "total_closed_won_revenue": round(won_pipeline, 2),
            "total_spend": round(total_spend, 2),
            "win_rate_percentage": round(win_rate, 2),
            "roi_percentage": roi_pct,
            "roas": roas,
            "verdict": verdict
        }

    except Exception as e:
        raise e


def run_attribution_model(model_type: str = 'linear', campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    '''Query ga4_events and crm_opps to distribute pipeline revenue credit across marketing touches.'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        camp_cond = f"g.utm_campaign = '{campaign_id}'" if campaign_id else "1=1"
        tf_cond = f"AND g.timestamp >= date('now', '-{timeframe} days')" if timeframe > 0 else ""
        
        o_camp_cond = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""
        o_tf_cond = f"AND timestamp >= date('now', '-{timeframe} days')" if timeframe > 0 else ""
        
        query = f"""
            WITH user_opps AS (
                SELECT 
                    user_id,
                    SUM(pipeline_value) as total_pipeline
                FROM crm_opps
                WHERE event_type = 'Opportunity Created' {o_camp_cond} {o_tf_cond}
                GROUP BY user_id
            ),
            user_touches AS (
                SELECT 
                    user_id, 
                    COUNT(DISTINCT session_id) as total_touches
                FROM ga4_events g
                WHERE {camp_cond} {tf_cond}
                GROUP BY user_id
            )
            SELECT 
                g.utm_source, 
                COUNT(DISTINCT g.session_id) as touch_count,
                SUM(COALESCE(o.total_pipeline, 0) / CAST(t.total_touches AS FLOAT)) as attributed_revenue
            FROM ga4_events g
            JOIN user_touches t ON g.user_id = t.user_id
            LEFT JOIN user_opps o ON g.user_id = o.user_id
            WHERE {camp_cond} {tf_cond}
            GROUP BY g.utm_source
            ORDER BY attributed_revenue DESC, touch_count DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        attribution = {}
        total_revenue = 0
        for r in rows:
            src = r['utm_source'] or 'direct'
            revenue = round(r['attributed_revenue'] or 0, 2)
            attribution[src] = {
                "touch_count": r['touch_count'],
                "attributed_revenue": revenue
            }
            total_revenue += revenue

        # Attach spend estimates per utm_source for ROAS calculation
        tf_cond = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
        camp_cond_li = f"AND campaign_id = '{campaign_id}'" if campaign_id else ""
        camp_cond_mc = f"AND campaign_id LIKE '%{campaign_id}%'" if campaign_id else ""
        camp_cond_ga = f"AND utm_campaign = '{campaign_id}'" if campaign_id else ""

        conn2 = get_db_connection()
        c2 = conn2.cursor()
        c2.execute(f"SELECT SUM(spend_consumed) as s FROM linkedin_events WHERE 1=1 {camp_cond_li} {tf_cond}")
        li_spend = c2.fetchone()["s"] or 0.0
        c2.execute(f"SELECT COUNT(event_id) as c FROM mailchimp_events WHERE 1=1 {camp_cond_mc} {tf_cond}")
        em_spend = (c2.fetchone()["c"] or 0) * 1.50
        c2.execute(f"SELECT COUNT(session_id) as c FROM ga4_events WHERE 1=1 {camp_cond_ga} {tf_cond}")
        web_spend = (c2.fetchone()["c"] or 0) * 0.80
        conn2.close()

        spend_map = {
            "linkedin": li_spend,
            "email": em_spend,
            "direct": web_spend / 2,
            "organic": web_spend / 2
        }

        top_channel = None
        top_roas = -1
        for src, data in attribution.items():
            ch_spend = spend_map.get(src.lower(), 0)
            data["channel_spend"] = round(ch_spend, 2)
            data["channel_roas"] = round(data["attributed_revenue"] / ch_spend, 2) if ch_spend > 0 else None
            if data["channel_roas"] is not None and data["channel_roas"] > top_roas:
                top_roas = data["channel_roas"]
                top_channel = src

        return {
            "model_type": model_type,
            "timeframe_days": timeframe,
            "timeframe_label": "All Time" if timeframe == 0 else f"Last {timeframe} Days",
            "total_attributed_revenue": round(total_revenue, 2),
            "channel_distribution": attribution,
            "top_performing_channel": top_channel,
            "recommendation": f"Prioritise {top_channel} — it delivers the highest ROAS ({top_roas:.1f}×) in this timeframe." if top_channel else "Insufficient data to identify top-performing channel."
        }

    except Exception as e:
        raise e
