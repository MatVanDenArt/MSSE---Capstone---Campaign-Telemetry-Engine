from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services.analytics_v2 import evaluate_trickle_threshold, get_account_penetration, calculate_blended_cpa, get_kpi_benchmarks, generate_strategic_tldr, get_asset_impact_matrix, get_all_campaigns, get_timeline_chart_data, get_asset_fatigue, generate_next_best_actions, get_audience_network_data, get_sankey_data, get_asset_timeline_data, get_tam_penetration, calculate_share_of_voice
import sqlite3
import urllib.parse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

import os
DB_PATH = os.getenv("DATABASE_URL", "capstone.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()



@router.get("/dashboard/workspace", response_class=HTMLResponse)
def get_workspace(request: Request, campaign_id: str):
    from app.services.analytics_v2 import get_campaign_start_date
    start_date = get_campaign_start_date(campaign_id)
    return templates.TemplateResponse(request=request, name="workspace_v2.html", context={"campaign_id": campaign_id, "start_date": start_date})

@router.get("/dashboard/sidebar", response_class=HTMLResponse)
def get_sidebar(request: Request):
    campaigns = get_all_campaigns()
    return templates.TemplateResponse(request=request, name="components/sidebar.html", context={"campaigns": campaigns})

@router.get("/dashboard/overview", response_class=HTMLResponse)
def get_overview(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    assets = get_asset_fatigue(campaign_id, timeframe)
    
    from app.services.analytics_v2 import get_tam_penetration, calculate_share_of_voice, get_all_campaigns
    tam = get_tam_penetration(campaign_id)
    sov = calculate_share_of_voice(campaign_id)
    campaigns = get_all_campaigns()
    campaign_data = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)

    return templates.TemplateResponse(request=request, name="components/overview_v2.html", context={
        "campaign_id": campaign_id,
        "campaign_data": campaign_data,
        "timeframe": timeframe,
        "benchmarks": benchmarks,
        "assets": assets,
        "tam": tam,
        "sov": sov,
        "copilot_context_name": "Executive Overview",
        "copilot_actions": [
            {"label": "Forecast Shortfall", "command": "Forecast Q4 Pipeline shortfall and recommend precise budget reallocations.", "intent": "analyze", "icon": "fa-chart-pie"},
            {"label": "Pacing Analysis", "command": "Analyze budget pacing against pipeline generation targets.", "intent": "analyze", "icon": "fa-money-bill-trend-up"},
            {"label": "Executive KPIs", "command": "Pull executive pipeline KPIs and blended CPA.", "intent": "analyze", "icon": "fa-briefcase"}
        ],
        "copilot_tasks": generate_next_best_actions(campaign_id)
    })
@router.get("/dashboard/performance", response_class=HTMLResponse)
def get_performance(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    
    import uuid
    dynamic_tasks = []
    if matrix:
        top_asset = max(matrix, key=lambda x: x.get('impact_score', 0))
        if top_asset:
            encoded_asset = urllib.parse.quote(top_asset.get('asset_name', 'Asset'))
            tid = f"TRG_{uuid.uuid4().hex[:8]}"
            dynamic_tasks.append({
                "id": tid,
                "icon": "fa-arrow-trend-up",
                "icon_color": "text-emerald-500",
                "title": f"Top Asset: {top_asset.get('asset_name', 'Asset')}",
                "subtitle": f"Driving high impact with {top_asset.get('engagement', 0)} interactions",
                "action_command": f"/api/v2/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={encoded_asset}&trigger_id={tid}",
                "is_programmatic": True
            })
            
        fatigued_assets = [m for m in matrix if m.get('health') == 'Fatigued' or m.get('ai_recommendation')]
        for asset in fatigued_assets:
            encoded_asset = urllib.parse.quote(asset.get('asset_name', 'Asset'))
            # Simplify subtitle for the list view
            health_status = asset.get('health', 'Fatigued')
            short_subtitle = "Traffic dropping rapidly" if "Traffic dropping" in asset.get('ai_recommendation', '') else "Engagement trickling off"
            if "Ad fatigue" in asset.get('ai_recommendation', ''):
                short_subtitle = "Ad fatigue detected"
                
            tid = f"TRG_{uuid.uuid4().hex[:8]}"
            dynamic_tasks.append({
                "id": tid,
                "icon": "fa-battery-quarter",
                "icon_color": "text-rose-500",
                "title": f"Fatigue: {asset.get('asset_name', 'Asset')}",
                "subtitle": short_subtitle,
                "action_command": f"/api/v2/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={encoded_asset}&trigger_id={tid}",
                "is_programmatic": True
            })

        # Simulated Triggers based on Optimal Comparator Outline
        if len(matrix) > 2:
            bounce_asset = matrix[1].get('asset_name', 'Landing Page')
            enc_bounce = urllib.parse.quote(bounce_asset)
            tid2 = f"TRG_{uuid.uuid4().hex[:8]}"
            dynamic_tasks.append({
                "id": tid2,
                "icon": "fa-arrow-right-from-bracket",
                "icon_color": "text-rose-500",
                "title": f"High Bounce Rate: {bounce_asset}",
                "subtitle": "Traffic is high but conversion is < 1%",
                "action_command": f"/api/v2/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={enc_bounce}&trigger_id={tid2}",
                "is_programmatic": True
            })
            
            spike_asset = matrix[2].get('asset_name', 'Webinar')
            enc_spike = urllib.parse.quote(spike_asset)
            tid3 = f"TRG_{uuid.uuid4().hex[:8]}"
            dynamic_tasks.append({
                "id": tid3,
                "icon": "fa-bolt",
                "icon_color": "text-emerald-500",
                "title": f"Conversion Spike: {spike_asset}",
                "subtitle": "Converting at 3x the historical baseline",
                "action_command": f"/api/v2/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={enc_spike}&trigger_id={tid3}",
                "is_programmatic": True
            })

    return templates.TemplateResponse(request=request, name="components/performance_v2.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "chart_data": chart_data,
        "matrix": matrix,
        "copilot_context_name": "Asset Performance",
        "copilot_actions": [
            {"label": "Analyze Fatigue", "command": "Analyze the fatigue rate of top assets against historical baselines.", "intent": "analyze", "icon": "fa-battery-quarter"},
            {"label": "Compare Baselines", "command": "Compare asset baselines to identify the highest ROI channel.", "intent": "analyze", "icon": "fa-code-compare"},
            {"label": "Generate A/B Test", "command": "Generate A/B test variants for underperforming assets.", "intent": "draft", "icon": "fa-flask"}
        ],
        "copilot_tasks": dynamic_tasks
    })

@router.get("/dashboard/audience", response_class=HTMLResponse)
def get_audience(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    from app.services.analytics import get_prioritized_sales_targets
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    
    from datetime import datetime
    
    # Map prioritized sales targets to Copilot Priority Actions
    import uuid
    raw_targets = get_prioritized_sales_targets(campaign_id)[:4] # Top 4 targets
    copilot_tasks = []
    for t in raw_targets:
        icon_col = "text-sky-400" if t['status'] == 'SQL' else "text-fuchsia-500"
        
        # Calculate relative date
        try:
            last_active_date = datetime.strptime(t['last_active'], "%Y-%m-%d")
            delta = datetime.now() - last_active_date
            if delta.days == 0:
                relative_date = "Today"
            elif delta.days == 1:
                relative_date = "Yesterday"
            else:
                relative_date = f"{delta.days} days ago"
        except:
            relative_date = t['last_active']
            
        subtitle = f"{t['interactions']} interactions | Last active {relative_date}"
        
        import urllib.parse
        encoded_name = urllib.parse.quote(t['name'])
        encoded_company = urllib.parse.quote(t['company'])
        
        tid = f"TRG_{uuid.uuid4().hex[:8]}"
        copilot_tasks.append({
            "id": tid,
            "icon": "fa-bullseye",
            "icon_color": icon_col,
            "title": f"Follow-up: {t['name']} ({t['company']})",
            "subtitle": subtitle,
            "is_programmatic": True,
            "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name={encoded_name}&company={encoded_company}&trigger_id={tid}"
        })
        
    # Simulated ABM Triggers based on Optimal Comparator Outline
    tid_stalled = f"TRG_{uuid.uuid4().hex[:8]}"
    copilot_tasks.append({
        "id": tid_stalled,
        "icon": "fa-hourglass-end",
        "icon_color": "text-rose-500",
        "title": "Stalled Account: BP plc",
        "subtitle": "High early engagement, zero activity in 14 days",
        "is_programmatic": True,
        "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name=Unknown&company=BP&trigger_id={tid_stalled}"
    })
    
    tid_cross = f"TRG_{uuid.uuid4().hex[:8]}"
    copilot_tasks.append({
        "id": tid_cross,
        "icon": "fa-network-wired",
        "icon_color": "text-emerald-500",
        "title": "Cross-Department Expansion: Shell",
        "subtitle": "Engineering and Marketing consuming content simultaneously",
        "is_programmatic": True,
        "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name=Unknown&company=Shell&trigger_id={tid_cross}"
    })

    return templates.TemplateResponse(request=request, name="components/audience_v2.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "penetration": penetration,
        "copilot_context_name": "Audience & Accounts",
        "copilot_actions": [
            {"label": "Map Committee", "command": "Map the entire buying committee for stalled accounts and identify persona blind spots.", "intent": "analyze", "icon": "fa-sitemap"},
            {"label": "Surge Signals", "command": "Identify intent surge signals across target accounts in the last 48 hours.", "intent": "analyze", "icon": "fa-bolt"},
            {"label": "Draft Outreach", "command": "Draft a personalized outreach sequence for the stalled accounts.", "intent": "draft", "icon": "fa-envelope"}
        ],
        "copilot_tasks": copilot_tasks
    })

@router.get("/dashboard/audience-actions", response_class=HTMLResponse)
def get_audience_actions(request: Request, campaign_id: str, company: str = None):
    from app.services.analytics import get_prioritized_sales_targets
    import uuid
    import urllib.parse
    from datetime import datetime
    
    raw_targets = get_prioritized_sales_targets(campaign_id)
    if company:
        raw_targets = [t for t in raw_targets if t['company'] == company]
    
    raw_targets = raw_targets[:4]
    
    copilot_tasks = []
    for t in raw_targets:
        icon_col = "text-sky-400" if t['status'] == 'SQL' else "text-fuchsia-500"
        try:
            last_active_date = datetime.strptime(t['last_active'], "%Y-%m-%d")
            delta = datetime.now() - last_active_date
            if delta.days == 0:
                relative_date = "Today"
            elif delta.days == 1:
                relative_date = "Yesterday"
            else:
                relative_date = f"{delta.days} days ago"
        except:
            relative_date = t['last_active']
            
        subtitle = f"{t['interactions']} interactions | Last active {relative_date}"
        encoded_name = urllib.parse.quote(t['name'])
        encoded_company = urllib.parse.quote(t['company'])
        
        tid = f"TRG_{uuid.uuid4().hex[:8]}"
        copilot_tasks.append({
            "id": tid,
            "icon": "fa-bullseye",
            "icon_color": icon_col,
            "title": f"Follow-up: {t['name']} ({t['company']})",
            "subtitle": subtitle,
            "is_programmatic": True,
            "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name={encoded_name}&company={encoded_company}&trigger_id={tid}"
        })
        
    if not company:
        tid_stalled = f"TRG_{uuid.uuid4().hex[:8]}"
        copilot_tasks.append({
            "id": tid_stalled,
            "icon": "fa-hourglass-end",
            "icon_color": "text-rose-500",
            "title": "Stalled Account: BP plc",
            "subtitle": "High early engagement, zero activity in 14 days",
            "is_programmatic": True,
            "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name=Unknown&company=BP&trigger_id={tid_stalled}"
        })
        
        tid_cross = f"TRG_{uuid.uuid4().hex[:8]}"
        copilot_tasks.append({
            "id": tid_cross,
            "icon": "fa-network-wired",
            "icon_color": "text-emerald-500",
            "title": "Cross-Department Expansion: Shell",
            "subtitle": "Engineering and Marketing consuming content simultaneously",
            "is_programmatic": True,
            "action_command": f"/api/v2/dashboard/investigate-target?campaign_id={campaign_id}&name=Unknown&company=Shell&trigger_id={tid_cross}"
        })
        
    copilot_actions = [
        {"label": "Map Committee", "command": f"Map the entire buying committee for {company or 'stalled accounts'} and identify persona blind spots.", "intent": "analyze", "icon": "fa-sitemap"},
        {"label": "Surge Signals", "command": f"Identify intent surge signals across {company or 'target accounts'} in the last 48 hours.", "intent": "analyze", "icon": "fa-bolt"},
        {"label": "Draft Outreach", "command": f"Draft a personalized outreach sequence for {company or 'the stalled accounts'}.", "intent": "draft", "icon": "fa-envelope"}
    ]
        
    return templates.TemplateResponse(request=request, name="components/oob_copilot.html", context={
        "copilot_actions": copilot_actions,
        "copilot_tasks": copilot_tasks
    })

from functools import lru_cache

@lru_cache(maxsize=32)
def cached_generate_strategic_tldr(campaign_id: str, timeframe: int):
    from app.services.analytics_v2 import get_kpi_benchmarks, generate_strategic_tldr, get_all_campaigns
    benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
    
    campaigns = get_all_campaigns()
    campaign_data = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)
    
    payload = {
        "pipeline_generated_dollars": campaign_data["total_pipeline"] if campaign_data else 0,
        "total_spend_dollars": benchmarks["live"]["spend"],
        "cpa_dollars": benchmarks["live"]["cpa"],
        "cpa_percent_change": benchmarks["comparisons"]["cpa"]["value"],
        "closed_won_contracts": benchmarks["live"]["conversions"]
    }
    
    return generate_strategic_tldr(payload)

@router.get("/dashboard/tldr", response_class=HTMLResponse)
def get_tldr(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    tldr = cached_generate_strategic_tldr(campaign_id, timeframe)
    return HTMLResponse(content=tldr)

@router.get("/dashboard/investigate-target", response_class=HTMLResponse)
def investigate_target(campaign_id: str, name: str, company: str, trigger_id: str = None, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    if name == 'Unknown':
        query = f"""
            SELECT g.page_viewed, g.timestamp, g.utm_source, c.seniority, (c.first_name || ' ' || c.last_name) as full_name
            FROM ga4_events g
            JOIN crm_users c ON g.user_id = c.user_id
            WHERE g.utm_campaign = ? AND c.company_name LIKE ?
            ORDER BY g.timestamp DESC
            LIMIT 10
        """
        cursor.execute(query, (campaign_id, f"%{company}%"))
    else:
        query = f"""
            SELECT g.page_viewed, g.timestamp, g.utm_source, c.seniority, (c.first_name || ' ' || c.last_name) as full_name
            FROM ga4_events g
            JOIN crm_users c ON g.user_id = c.user_id
            WHERE g.utm_campaign = ? AND (c.first_name || ' ' || c.last_name) = ? AND c.company_name = ?
            ORDER BY g.timestamp DESC
            LIMIT 10
        """
        cursor.execute(query, (campaign_id, name, company))
    rows = cursor.fetchall()
    
    if not rows:
        history_items = "<div class='text-slate-500 text-xs py-2'>No specific interaction data found.</div>"
    else:
        from datetime import datetime
        history_items = '<ul class="relative border-l border-dark-600 ml-2 space-y-4 pt-1 pb-2">'
        for idx, r in enumerate(rows):
            src = r['utm_source'].lower() if r['utm_source'] else ''
            if 'linkedin' in src or 'social' in src:
                icon = 'fa-brands fa-linkedin text-sky-500'
            elif 'email' in src:
                icon = 'fa-solid fa-envelope text-amber-500'
            else:
                icon = 'fa-solid fa-globe text-emerald-500'
                
            try:
                dt = datetime.strptime(r['timestamp'].split('.')[0], "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%d %b %Y").upper()
            except:
                date_str = r['timestamp'].split(' ')[0] if r['timestamp'] else 'Unknown'
                
            page_clean = r['page_viewed'].strip('/').replace('/', ' ').replace('-', ' ').title()
                
            dot_class = 'bg-brand-500 shadow-[0_0_8px_rgba(56,189,248,0.6)]' if idx == 0 else 'bg-dark-600'
            text_class = 'text-brand-300 bg-brand-900/10' if idx == 0 else 'text-slate-300'
            icon_class = f"mr-2 text-xs {icon} {'opacity-100 drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' if idx == 0 else 'opacity-70'}"
            
            history_items += f"""
            <li class="relative pl-5">
                <div class="absolute -left-[6.5px] top-1 w-3 h-3 rounded-full border-2 border-dark-900 z-10 transition-colors {dot_class}"></div>
                <div class="flex flex-col">
                    <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">{date_str}</span>
                    <div class="flex items-center text-sm font-medium w-full rounded pr-2 py-0.5 {text_class}">
                        <i class="{icon_class}"></i>
                        <span class="truncate" title="{r['page_viewed']}">{page_clean}</span>
                    </div>
                </div>
            </li>
            """
        history_items += '</ul>'

    ai_summary_html = ""
    try:
        import os
        from app.services.llm_rotator import get_genai_client
        if ("GEMINI_API_KEY" in os.environ or "GEMINI_API_KEYS" in os.environ) and rows:
            from google.genai import types
            context_str = f"Target: {name} at {company} (Seniority: {rows[0]['seniority'] if rows else 'Unknown'}).\nRecent 10 Interactions (Chronological):\n"
            for r in rows:
                context_str += f"- {r['timestamp']}: {r['page_viewed']} via {r['utm_source']}\n"
                
            prompt = f"Act as an expert B2B marketing AI. Review this chronological interaction data. Provide a brief 2-3 sentence summary justifying why this account is a priority Sales Qualified Lead (SQL). Mention their seniority and timeline of engagement (recency) if relevant. Keep it strategic and punchy. Data:\n{context_str}"
            
            response = None
            last_err = None
            for _ in range(3): # Try up to 3 times to get a working key
                try:
                    # Requesting a new client re-rolls the random API key
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
                
            ai_summary_html = f"""
            <div class="mb-4 text-slate-300 text-sm leading-relaxed border-l-2 border-fuchsia-500 pl-3">
                <span class="text-[10px] text-fuchsia-500 font-bold uppercase tracking-widest block mb-1">AI Context Analysis</span>
                {response.text}
            </div>
            """
    except Exception as e:
        ai_summary_html = f"""
        <div class="mb-4 text-rose-400 text-xs font-mono bg-rose-900/20 p-2 border border-rose-900/50">
            AI Context Unavailable (Rate Limit Exceeded). Displaying raw interaction data below.
        </div>
        """

    html_content = f"""
    <div class="flex gap-3 my-4">
        <div class="w-6 h-6 bg-slate-700 flex items-center justify-center shrink-0 border border-slate-600">
            <i class="fa-solid fa-server text-[10px] text-slate-300"></i>
        </div>
        <div class="w-full">
            <div class="bg-black border border-dark-700">
                <div class="p-3 border-b border-dark-700 bg-dark-900 flex justify-between items-center">
                    <span class="text-xs font-bold text-slate-300 tracking-widest uppercase">Target Analysis: {name if name != 'Unknown' else company}</span>
                    <span class="text-sky-400 text-[10px] font-bold"><i class="fa-solid fa-check-circle"></i> SQL</span>
                </div>
                <div class="p-4 flex flex-col">
                    {ai_summary_html}
                    <div class="mt-2 flex flex-col divide-y divide-dark-800">
                        <div class="mb-2 text-xs text-brand-400 font-bold uppercase tracking-widest border-b border-dark-700 pb-2">Interaction History</div>
                        {history_items}
                    </div>
                </div>
                <div class="p-3 border-t border-dark-700 bg-dark-900 flex gap-2">
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Draft executive outreach for {name} at {company}", "intent": "draft"}}' class="flex-1 py-2 bg-fuchsia-900/20 hover:bg-fuchsia-600/20 border border-fuchsia-500/50 hover:border-fuchsia-500 text-fuchsia-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-bolt"></i> Draft Outreach
                    </button>
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Sync {name} to CRM", "intent": "automate"}}' class="flex-1 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-slate-300 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        Sync to CRM
                    </button>
                </div>
            </div>
        </div>
    </div>
    """
    
    if trigger_id:
        html_content += f'<div id="task-card-{trigger_id}" hx-swap-oob="delete"></div>'
        
    return HTMLResponse(content=html_content)

@router.get("/dashboard/investigate-asset", response_class=HTMLResponse)
def investigate_asset(campaign_id: str, asset_name: str, trigger_id: str = None):
    matrix = get_asset_impact_matrix(campaign_id, 0)
    asset = next((m for m in matrix if m['asset_name'] == asset_name), None)
    
    if not asset:
        return HTMLResponse(content=f"<div class='p-4 text-slate-400'>Asset {asset_name} not found.</div>")
        
    ai_rec = asset.get('ai_recommendation', 'No specific AI analysis available for this asset.')
    health = asset.get('health', 'Unknown')
    
    if health == 'Fatigued':
        status_color = 'rose'
        icon = 'fa-battery-quarter'
    elif health in ['Warning', 'At Risk']:
        status_color = 'amber'
        icon = 'fa-triangle-exclamation'
    else:
        status_color = 'emerald'
        icon = 'fa-arrow-trend-up'
    
    html_content = f"""
    <div class="flex gap-3 my-4">
        <div class="w-6 h-6 bg-slate-700 flex items-center justify-center shrink-0 border border-slate-600">
            <i class="fa-solid fa-server text-[10px] text-slate-300"></i>
        </div>
        <div class="w-full">
            <div class="bg-black border border-dark-700">
                <div class="p-3 border-b border-dark-700 bg-dark-900 flex justify-between items-center">
                    <span class="text-xs font-bold text-slate-300 tracking-widest uppercase">Asset Analysis: {asset_name}</span>
                    <span class="text-{status_color}-500 text-[10px] font-bold"><i class="fa-solid {icon}"></i> {health}</span>
                </div>
                <div class="p-4 flex flex-col">
                    <div class="mb-2 text-slate-300 text-sm leading-relaxed border-l-2 border-brand-500 pl-3">
                        <span class="text-[10px] text-brand-400 font-bold uppercase tracking-widest block mb-1">AI Context Analysis</span>
                        {ai_rec}
                    </div>
                </div>
                <div class="p-3 border-t border-dark-700 bg-dark-900 flex gap-2">
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Suggest asset rotation for {asset_name}", "intent": "analyze"}}' class="flex-1 py-2 bg-brand-900/20 hover:bg-brand-600/20 border border-brand-500/50 hover:border-brand-500 text-brand-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-arrows-rotate"></i> Suggest Rotation
                    </button>
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Draft newsletter mention for {asset_name}", "intent": "draft"}}' class="flex-1 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-slate-300 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-envelope"></i> Draft Mention
                    </button>
                </div>
            </div>
        </div>
    </div>
    """
    
    if trigger_id:
        html_content += f'<div id="task-card-{trigger_id}" hx-swap-oob="delete"></div>'
        
    return HTMLResponse(content=html_content)

def get_account_penetration_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26"):
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    return templates.TemplateResponse(request=request, name="components/account_penetration.html", context={
        "campaign_id": campaign_id,
        "penetration": penetration
    })

@router.get("/dashboard/penetration-details", response_class=HTMLResponse)
def get_penetration_details(request: Request, campaign_id: str, company: str, seniority: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    query = f"""
        SELECT DISTINCT page_viewed 
        FROM ga4_events 
        WHERE utm_campaign = ? AND user_id IN (
            SELECT user_id FROM crm_users WHERE company_name = ? AND seniority = ?
        )
    """
    cursor.execute(query, (campaign_id, company, seniority))
    rows = cursor.fetchall()
    
    assets_html = "".join([f"<li><i class='fa-solid fa-file-pdf text-rose-400 mr-2'></i> {r['page_viewed'].replace('/', '')}</li>" for r in rows]) if rows else "<li class='text-slate-500'>No specific assets consumed</li>"
    
    return HTMLResponse(content=f"""
    <div class="p-6 bg-dark-800 rounded-lg border border-dark-600 shadow-2xl absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 min-w-[400px]">
        <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-slate-100">{company} - {seniority}</h3>
            <button onclick="this.parentElement.parentElement.remove()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <p class="text-sm text-slate-300 mb-4">Actual Content Consumed:</p>
        <ul class="space-y-2 text-sm text-slate-400">
            {assets_html}
        </ul>
    </div>
    """)

@router.get("/dashboard/timeline", response_class=HTMLResponse)
def get_timeline_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    return templates.TemplateResponse(request=request, name="components/timeline.html", context={
        "campaign_id": campaign_id,
        "chart_data": chart_data,
        "matrix": matrix
    })

@router.get("/dashboard/asset-fatigue", response_class=HTMLResponse)
def get_asset_fatigue_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26"):
    assets = get_asset_fatigue(campaign_id)
    return templates.TemplateResponse(request=request, name="components/asset_fatigue.html", context={
        "campaign_id": campaign_id,
        "assets": assets
    })

@router.get("/dashboard/alerts", response_class=HTMLResponse)
def get_alerts_view(request: Request, campaign_id: str):
    actions = generate_next_best_actions(campaign_id)
    if not actions:
        return HTMLResponse(content="") # Empty response if no alerts
    return templates.TemplateResponse(request=request, name="components/alerts.html", context={
        "actions": actions
    })

@router.post("/dashboard/execute-action", response_class=HTMLResponse)
def execute_action(request: Request, type: str, campaign_id: str):
    # Mock execution endpoint
    return HTMLResponse(content=f"<span class='text-emerald-400 font-bold'><i class='fa-solid fa-check mr-2'></i>Action Executed</span>")

@router.get("/dashboard/data-model")
def get_data_model_view(request: Request, campaign_id: str):
    from app.services.analytics import get_asset_fatigue
    assets = get_asset_fatigue(campaign_id, 90)
    return templates.TemplateResponse(request=request, name="components/data_model.html", context={
        "campaign_id": campaign_id,
        "assets": assets
    })

@router.get("/dashboard/audience-data-scoped")
def get_audience_data_scoped(campaign_id: str):
    from app.services.analytics import get_scoped_audience_data
    from fastapi.responses import JSONResponse
    return JSONResponse(content=get_scoped_audience_data(campaign_id))

@router.get("/dashboard/audience-data")
def get_audience_data(campaign_id: str = None):
    data = get_audience_network_data() # We will update this later if needed
    return JSONResponse(content=data)

@router.get("/dashboard/sankey-data")
def get_sankey_data_route(campaign_id: str):
    data = get_sankey_data(campaign_id)
    return JSONResponse(content=data)

@router.get("/dashboard/asset-timeline")
def get_asset_timeline_data_route(campaign_id: str, timeframe: int = 0):
    data = get_asset_timeline_data(campaign_id, timeframe)
    return JSONResponse(content=data)

@router.delete("/dashboard/trigger/{trigger_id}", response_class=HTMLResponse)
def resolve_trigger(trigger_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE action_triggers SET resolved_status = 1 WHERE id = ?", (trigger_id,))
    db.commit()
    return HTMLResponse(content="")

@router.post("/dashboard/generate-ai-insight")
async def generate_ai_insight(request: Request):
    from app.services.llm_rotator import get_genai_client
    from fastapi.responses import JSONResponse
    import json
    
    try:
        data = await request.json()
        company = data.get("company", "Unknown")
        
        prompt = f"""You are an expert Strategic Account Executive.
Analyze the following engagement data for the account '{company}'.
Data:
{json.dumps(data, indent=2)}

Output your response strictly as a JSON object with the following keys:
- "diagnosis": A short, single-paragraph synthesis evaluating the health of this account (committee gaps, intent topics, momentum). Don't just repeat the numbers. Identify risks (e.g. missing executives, stalled users) or momentum.
- "signals": An array of 1 to 3 signal objects. Each object must have:
    - "icon": A FontAwesome class (e.g., 'fa-arrow-trend-up', 'fa-triangle-exclamation', 'fa-hourglass-half', 'fa-check')
    - "color": A Tailwind text color (e.g., 'text-emerald-400', 'text-rose-400', 'text-amber-400', 'text-slate-400')
    - "label": A short 1-2 word label (e.g., 'Surge Signal', 'Friction Alert', 'Stall Risk', 'Status')
    - "text": A brief 1-sentence description of the signal.

Ensure valid JSON output.
"""
        client = get_genai_client()
        from starlette.concurrency import run_in_threadpool
        resp = await run_in_threadpool(client.models.generate_content, model="gemini-3.6-flash", contents=prompt)
        
        try:
            result = json.loads(resp.text)
        except json.JSONDecodeError:
            text = resp.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            
        return JSONResponse(content=result)
    except Exception as e:
        print(f"Error generating insight: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)


@router.get('/dashboard/ui-lab/channel-roi')
def ui_lab_channel_roi(campaign_id: str):
    matrix = get_asset_impact_matrix(campaign_id, 0)
    return templates.TemplateResponse(request=Request({"type": "http"}), name="components/mod_channel_roi.html", context={"matrix": matrix})

@router.get('/dashboard/v2/channel-roi-data')
def v2_channel_roi_data(campaign_id: str):
    from app.services.analytics import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # LinkedIn
    cursor.execute('''SELECT SUM(spend_consumed) FROM linkedin_events WHERE campaign_id = ?''', (campaign_id,))
    li_spend = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? AND o.user_id IN (SELECT user_id FROM linkedin_events WHERE campaign_id = ?)
    ''', (campaign_id, campaign_id))
    row = cursor.fetchone()
    li_pipe = row[0] or 0.0
    li_opps = row[1] or 0
    
    # Email
    cursor.execute('''SELECT COUNT(event_id) FROM mailchimp_events WHERE campaign_id LIKE '%' || ? || '%' ''', (campaign_id,))
    em_clicks = cursor.fetchone()[0] or 0
    em_spend = em_clicks * 1.50 # Simulated CPC
    
    cursor.execute('''
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? AND o.user_id IN (SELECT user_id FROM mailchimp_events WHERE campaign_id LIKE '%' || ? || '%')
    ''', (campaign_id, campaign_id))
    row = cursor.fetchone()
    em_pipe = row[0] or 0.0
    em_opps = row[1] or 0
    
    # Web
    cursor.execute('''SELECT COUNT(session_id) FROM ga4_events WHERE utm_campaign = ?''', (campaign_id,))
    web_views = cursor.fetchone()[0] or 0
    web_spend = web_views * 0.80 # Simulated CPC
    
    cursor.execute('''
        SELECT SUM(o.pipeline_value), COUNT(o.event_id)
        FROM crm_opps o
        WHERE o.utm_campaign = ? AND o.user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = ?)
    ''', (campaign_id, campaign_id))
    row = cursor.fetchone()
    web_pipe = row[0] or 0.0
    web_opps = row[1] or 0
    
    conn.close()

    def calc_metrics(spend, pipe, opps):
        return {
            "spend": spend,
            "pipeline": pipe,
            "opps": opps,
            "roi_multiplier": round(pipe / spend, 1) if spend > 0 else 0,
            "cpo": round(spend / opps, 2) if opps > 0 else 0
        }

    return JSONResponse(content={
        "linkedin": calc_metrics(li_spend, li_pipe, li_opps),
        "email": calc_metrics(em_spend, em_pipe, em_opps),
        "web": calc_metrics(web_spend, web_pipe, web_opps)
    })
def ui_lab_channel_roi_data(campaign_id: str):
    from app.services.analytics import get_channel_roi_data
    return JSONResponse(content=get_channel_roi_data(campaign_id))

@router.get("/dashboard/target-accounts-modal", response_class=HTMLResponse)
def get_target_accounts_modal(request: Request, campaign_id: str):
    from app.services.analytics import get_prioritized_sales_targets
    targets = get_prioritized_sales_targets(campaign_id)
    return templates.TemplateResponse(request=request, name="components/target_accounts_modal.html", context={"targets": targets, "campaign_id": campaign_id})

@router.get("/dashboard/topic-clusters", response_class=HTMLResponse)
def get_topic_clusters(request: Request, campaign_id: str):
    from app.services.analytics import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Base query for all engagements mapped to topics and assets
    query = '''
    WITH AllEngagements AS (
        SELECT g.timestamp, c.intent_topic, c.title, c.asset_type
        FROM ga4_events g
        JOIN content_metadata c ON g.page_viewed = c.url
        WHERE g.utm_campaign = ?
        
        UNION ALL
        
        SELECT m.timestamp, c.intent_topic, c.title, c.asset_type
        FROM mailchimp_events m
        JOIN content_metadata c ON REPLACE(REPLACE(m.url_clicked, 'https://woodplc.com?utm_campaign=', ''), 'https://example.com?utm_source=mailchimp&utm_campaign=', '') = c.url
        WHERE m.campaign_id = ? AND m.action = 'Open'
        
        UNION ALL
        
        SELECT l.timestamp, c.intent_topic, c.title, c.asset_type
        FROM linkedin_events l
        JOIN content_metadata c ON l.ad_id = c.url
        WHERE l.campaign_id = ?
    )
    SELECT 
        intent_topic,
        title,
        asset_type,
        COUNT(timestamp) as engagements
    FROM AllEngagements
    GROUP BY intent_topic, title, asset_type
    ORDER BY intent_topic, engagements DESC
    '''
    cursor.execute(query, (campaign_id, campaign_id, campaign_id))
    rows = cursor.fetchall()
    conn.close()
    
    # Process into hierarchical dictionary
    topic_map = {}
    for row in rows:
        topic = row['intent_topic']
        if topic not in topic_map:
            topic_map[topic] = {
                'intent_topic': topic,
                'total_engagements': 0,
                'assets': []
            }
        topic_map[topic]['assets'].append({
            'title': row['title'],
            'type': row['asset_type'],
            'engagements': row['engagements']
        })
        topic_map[topic]['total_engagements'] += row['engagements']
        
    # Sort topics by total engagements
    sorted_topics = sorted(list(topic_map.values()), key=lambda x: x['total_engagements'], reverse=True)
    
    return templates.TemplateResponse(request=request, name="components/topic_clusters.html", context={
        "campaign_id": campaign_id,
        "topics": sorted_topics
    })

@router.get("/dashboard/abm-data")
def get_abm_data(campaign_id: str):
    from app.services.analytics import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Buying Committee (Users by Persona Type)
    query = '''
    WITH AllEvents AS (
        SELECT timestamp, user_id FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL
        UNION ALL
        SELECT m.timestamp, u.user_id FROM mailchimp_events m JOIN crm_users u ON m.email = u.email WHERE m.campaign_id LIKE ?
        UNION ALL
        SELECT l.timestamp, g.user_id FROM linkedin_events l JOIN (SELECT DISTINCT cookie_id, user_id FROM ga4_events WHERE user_id IS NOT NULL) g ON l.cookie_id = g.cookie_id WHERE l.campaign_id = ?
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
    '''
    cursor.execute(query, (campaign_id, f'%{campaign_id}%', campaign_id))
    accounts = cursor.fetchall()
    
    # Process into structured account objects
    account_map = {}
    for row in accounts:
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
                'opportunities': []
            }
        
        account_map[comp]['total_interactions'] += row['interactions']
        if row['persona_type'] == 'Technical':
            account_map[comp]['technical_users'] += row['user_count']
        elif row['persona_type'] == 'Commercial':
            account_map[comp]['commercial_users'] += row['user_count']
            
    # Add CRM Opportunities data
    opps_query = '''
    SELECT c.company_name, o.event_type, o.pipeline_value, o.timestamp
    FROM crm_opps o
    JOIN (SELECT DISTINCT account_id, company_name FROM crm_users) c ON o.account_id = c.account_id
    WHERE o.utm_campaign = ?
    ORDER BY o.timestamp DESC
    '''
    cursor.execute(opps_query, (campaign_id,))
    for row in cursor.fetchall():
        comp = row['company_name']
        if comp in account_map:
            val = float(row['pipeline_value'] or 0)
            account_map[comp]['opportunities'].append({
                'date': str(row['timestamp']).split(' ')[0],
                'type': row['event_type'],
                'value': val
            })
            account_map[comp]['pipeline_value'] += val
            
            # Update CRM status and specific values
            current = account_map[comp]['crm_status']
            if row['event_type'] == 'Closed Won':
                account_map[comp]['crm_status'] = 'Customer'
                account_map[comp]['won_value'] += val
            elif row['event_type'] == 'Opportunity Created':
                if current != 'Customer':
                    account_map[comp]['crm_status'] = 'Active Opp'
                account_map[comp]['active_opp_value'] += val
                
    sorted_accounts = sorted(list(account_map.values()), key=lambda x: x['total_interactions'], reverse=True)[:10]

    conn.close()
    return {"accounts": sorted_accounts}

@router.get("/v2/api/targets")
def v2_api_targets(campaign_id: str):
    from app.services.analytics import get_ui_lab_funnel_data
    return JSONResponse(content=get_ui_lab_funnel_data(campaign_id))

@router.get('/dashboard/v2/funnel-drilldown', response_class=HTMLResponse)
def get_funnel_drilldown(request: Request, campaign_id: str, stage: str):
    from app.services.analytics import get_funnel_drilldown_data
    data = get_funnel_drilldown_data(campaign_id, stage)
    return templates.TemplateResponse(request=request, name="components/mod_v2_funnel_modal.html", context={"data": data, "stage": stage})

@router.get('/dashboard/ui-lab/funnel')
def ui_lab_funnel(campaign_id: str):
    from app.services.analytics import get_ui_lab_funnel_data
    return JSONResponse(content=get_ui_lab_funnel_data(campaign_id))

@router.get('/dashboard/ui-lab/heatmap')
def ui_lab_heatmap(campaign_id: str):
    from app.services.analytics import get_ui_lab_heatmap_data
    return JSONResponse(content=get_ui_lab_heatmap_data(campaign_id))


@router.get('/dashboard/sales-alerts')
def get_sales_alerts(campaign_id: str):
    from app.services.analytics import get_prioritized_sales_targets
    from fastapi.responses import JSONResponse
    return JSONResponse(content=get_prioritized_sales_targets(campaign_id))


from app.services.analytics import get_asset_personas

@router.get("/asset-personas")
def get_asset_personas_endpoint(campaign_id: str, asset_name: str, type: str, timeframe: int = 0):
    users = get_asset_personas(campaign_id, asset_name, type, timeframe)
    return JSONResponse(content=users)

@router.get("/telemetry/ai-calls")
def get_ai_telemetry():
    from app.services.llm_rotator import get_telemetry
    data = get_telemetry()
    return JSONResponse(content=data)

