from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services.analytics import evaluate_trickle_threshold, get_account_penetration, calculate_blended_cpa, get_kpi_benchmarks, generate_strategic_tldr, get_asset_impact_matrix, get_all_campaigns, get_timeline_chart_data, get_asset_fatigue, generate_next_best_actions, get_audience_network_data, get_sankey_data, get_asset_timeline_data
import sqlite3
import urllib.parse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DB_PATH = "capstone.db"

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    campaigns = get_all_campaigns()
    return templates.TemplateResponse(request=request, name="lobby.html", context={"campaigns": campaigns})

@router.get("/dashboard/workspace", response_class=HTMLResponse)
async def get_workspace(request: Request, campaign_id: str):
    from app.services.analytics import get_campaign_start_date
    start_date = get_campaign_start_date(campaign_id)
    return templates.TemplateResponse(request=request, name="workspace.html", context={"campaign_id": campaign_id, "start_date": start_date})

@router.get("/dashboard/sidebar", response_class=HTMLResponse)
async def get_sidebar(request: Request):
    campaigns = get_all_campaigns()
    return templates.TemplateResponse(request=request, name="components/sidebar.html", context={"campaigns": campaigns})

@router.get("/dashboard/overview", response_class=HTMLResponse)
async def get_overview(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    assets = get_asset_fatigue(campaign_id, timeframe)
    
    return templates.TemplateResponse(request=request, name="components/overview.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "benchmarks": benchmarks,
        "assets": assets,
        "copilot_context_name": "Executive Overview",
        "copilot_actions": [
            {"label": "Gen Report", "command": "Generate an executive summary report"},
            {"label": "Analyze Funnel", "command": "Analyze funnel velocity"},
            {"label": "Forecast EOM", "command": "Forecast end of month ROI"}
        ],
        "copilot_tasks": [
            {
                "icon": "fa-chart-line",
                "icon_color": "text-rose-500",
                "title": "Funnel Velocity Alert",
                "subtitle": "CPA trending 12% higher than 30d avg",
                "action_command": "Analyze funnel velocity to identify bottlenecks"
            },
            {
                "icon": "fa-bullseye",
                "icon_color": "text-brand-500",
                "title": "Goal Tracking",
                "subtitle": "MQL target at 85% for the month",
                "action_command": "Forecast end of month ROI"
            }
        ]
    })
@router.get("/dashboard/performance", response_class=HTMLResponse)
async def get_performance(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    
    dynamic_tasks = []
    if matrix:
        top_asset = max(matrix, key=lambda x: x.get('impact_score', 0))
        if top_asset:
            encoded_asset = urllib.parse.quote(top_asset.get('asset_name', 'Asset'))
            dynamic_tasks.append({
                "icon": "fa-arrow-trend-up",
                "icon_color": "text-emerald-500",
                "title": f"Top Asset: {top_asset.get('asset_name', 'Asset')}",
                "subtitle": f"Driving high impact with {top_asset.get('engagement', 0)} interactions",
                "action_command": f"/api/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={encoded_asset}",
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
                
            dynamic_tasks.append({
                "icon": "fa-battery-quarter",
                "icon_color": "text-rose-500",
                "title": f"Fatigue: {asset.get('asset_name', 'Asset')}",
                "subtitle": short_subtitle,
                "action_command": f"/api/dashboard/investigate-asset?campaign_id={campaign_id}&asset_name={encoded_asset}",
                "is_programmatic": True
            })

    return templates.TemplateResponse(request=request, name="components/performance.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "chart_data": chart_data,
        "matrix": matrix,
        "copilot_context_name": "Asset Performance",
        "copilot_actions": [
            {"label": "Check Fatigue", "command": "Check for asset fatigue"},
            {"label": "Suggest Rotation", "command": "Suggest asset rotation"},
            {"label": "Analyze Mix", "command": "Analyze channel mix"}
        ],
        "copilot_tasks": dynamic_tasks
    })

@router.get("/dashboard/audience", response_class=HTMLResponse)
async def get_audience(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    from app.services.analytics import get_prioritized_sales_targets
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    
    from datetime import datetime
    
    # Map prioritized sales targets to Copilot Priority Actions
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
        
        copilot_tasks.append({
            "icon": "fa-bullseye",
            "icon_color": icon_col,
            "title": f"Follow-up: {t['name']} ({t['company']})",
            "subtitle": subtitle,
            "is_programmatic": True,
            "action_command": f"/api/dashboard/investigate-target?campaign_id={campaign_id}&name={encoded_name}&company={encoded_company}"
        })

    return templates.TemplateResponse(request=request, name="components/audience.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "penetration": penetration,
        "copilot_context_name": "Audience & Accounts",
        "copilot_actions": [
            {"label": "Sync SQLs to CRM", "command": "Sync SQLs to CRM"},
            {"label": "Draft Outreach", "command": "Draft executive outreach"},
            {"label": "Find Lookalikes", "command": "Find lookalike accounts"}
        ],
        "copilot_tasks": copilot_tasks
    })

from functools import lru_cache

@lru_cache(maxsize=32)
def cached_generate_strategic_tldr(campaign_id: str, timeframe: int):
    from app.services.analytics import get_kpi_benchmarks, generate_strategic_tldr
    benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
    return generate_strategic_tldr(benchmarks)

@router.get("/dashboard/tldr", response_class=HTMLResponse)
async def get_tldr(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    tldr = cached_generate_strategic_tldr(campaign_id, timeframe)
    return HTMLResponse(content=tldr)

@router.get("/dashboard/investigate-target", response_class=HTMLResponse)
async def investigate_target(campaign_id: str, name: str, company: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = f"""
        SELECT g.page_viewed, g.timestamp, g.utm_source, c.seniority
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = ? AND (c.first_name || ' ' || c.last_name) = ? AND c.company_name = ?
        ORDER BY g.timestamp DESC
        LIMIT 10
    """
    cursor.execute(query, (campaign_id, name, company))
    rows = cursor.fetchall()
    conn.close()
    
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
        from app.services.llm_rotator import get_legacy_generative_model
        if ("GEMINI_API_KEY" in os.environ or "GEMINI_API_KEYS" in os.environ) and rows:
            model = get_legacy_generative_model('gemini-3.5-flash')
            context_str = f"Target: {name} at {company} (Seniority: {rows[0]['seniority'] if rows else 'Unknown'}).\nRecent 10 Interactions (Chronological):\n"
            for r in rows:
                context_str += f"- {r['timestamp']}: {r['page_viewed']} via {r['utm_source']}\n"
                
            prompt = f"Act as an expert B2B marketing AI. Review this chronological interaction data. Provide a brief 2-3 sentence summary justifying why this account is a priority Sales Qualified Lead (SQL). Mention their seniority and timeline of engagement (recency) if relevant. Keep it strategic and punchy. Data:\n{context_str}"
            
            response = None
            last_err = None
            for _ in range(3): # Try up to 3 times to get a working key
                try:
                    # Requesting a new model re-rolls the random API key
                    model = get_legacy_generative_model('gemini-3.5-flash')
                    response = model.generate_content(prompt)
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
                    <span class="text-xs font-bold text-slate-300 tracking-widest uppercase">Target Analysis: {name}</span>
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
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Execute: Draft executive outreach for {name} at {company}"}}' class="flex-1 py-2 bg-fuchsia-900/20 hover:bg-fuchsia-600/20 border border-fuchsia-500/50 hover:border-fuchsia-500 text-fuchsia-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-bolt"></i> Draft Outreach
                    </button>
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Execute: Sync {name} to CRM"}}' class="flex-1 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-slate-300 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        Sync to CRM
                    </button>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=html_content)

@router.get("/dashboard/investigate-asset", response_class=HTMLResponse)
async def investigate_asset(campaign_id: str, asset_name: str):
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
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Execute: Suggest asset rotation for {asset_name}"}}' class="flex-1 py-2 bg-brand-900/20 hover:bg-brand-600/20 border border-brand-500/50 hover:border-brand-500 text-brand-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-arrows-rotate"></i> Suggest Rotation
                    </button>
                    <button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "Execute: Draft newsletter mention for {asset_name}"}}' class="flex-1 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-slate-300 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2">
                        <i class="fa-solid fa-envelope"></i> Draft Mention
                    </button>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=html_content)

async def get_account_penetration_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26"):
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    return templates.TemplateResponse(request=request, name="components/account_penetration.html", context={
        "campaign_id": campaign_id,
        "penetration": penetration
    })

@router.get("/dashboard/penetration-details", response_class=HTMLResponse)
async def get_penetration_details(request: Request, campaign_id: str, company: str, seniority: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = f"""
        SELECT DISTINCT page_viewed 
        FROM ga4_events 
        WHERE utm_campaign = ? AND user_id IN (
            SELECT user_id FROM crm_users WHERE company_name = ? AND seniority = ?
        )
    """
    cursor.execute(query, (campaign_id, company, seniority))
    rows = cursor.fetchall()
    conn.close()
    
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
async def get_timeline_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    return templates.TemplateResponse(request=request, name="components/timeline.html", context={
        "campaign_id": campaign_id,
        "chart_data": chart_data,
        "matrix": matrix
    })

@router.get("/dashboard/asset-fatigue", response_class=HTMLResponse)
async def get_asset_fatigue_view(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26"):
    assets = get_asset_fatigue(campaign_id)
    return templates.TemplateResponse(request=request, name="components/asset_fatigue.html", context={
        "campaign_id": campaign_id,
        "assets": assets
    })

@router.get("/dashboard/alerts", response_class=HTMLResponse)
async def get_alerts_view(request: Request, campaign_id: str):
    actions = generate_next_best_actions(campaign_id)
    if not actions:
        return HTMLResponse(content="") # Empty response if no alerts
    return templates.TemplateResponse(request=request, name="components/alerts.html", context={
        "actions": actions
    })

@router.post("/dashboard/execute-action", response_class=HTMLResponse)
async def execute_action(request: Request, type: str, campaign_id: str):
    # Mock execution endpoint
    return HTMLResponse(content=f"<span class='text-emerald-400 font-bold'><i class='fa-solid fa-check mr-2'></i>Action Executed</span>")

@router.get("/dashboard/data-model")
async def get_data_model_view(request: Request, campaign_id: str):
    from app.services.analytics import get_asset_fatigue
    assets = get_asset_fatigue(campaign_id, 90)
    return templates.TemplateResponse(request=request, name="components/data_model.html", context={
        "campaign_id": campaign_id,
        "assets": assets
    })

@router.get("/dashboard/audience-data-scoped")
async def get_audience_data_scoped(campaign_id: str):
    from app.services.analytics import get_scoped_audience_data
    from fastapi.responses import JSONResponse
    return JSONResponse(content=get_scoped_audience_data(campaign_id))

@router.get("/dashboard/audience-data")
async def get_audience_data(campaign_id: str = None):
    data = get_audience_network_data() # We will update this later if needed
    return JSONResponse(content=data)

@router.get("/dashboard/sankey-data")
async def get_sankey_data_route(campaign_id: str):
    data = get_sankey_data(campaign_id)
    return JSONResponse(content=data)

@router.get("/dashboard/asset-timeline")
async def get_asset_timeline_data_route(campaign_id: str, timeframe: int = 0):
    data = get_asset_timeline_data(campaign_id, timeframe)
    return JSONResponse(content=data)


@router.get('/dashboard/ui-lab/channel-roi')
async def ui_lab_channel_roi(campaign_id: str):
    from app.services.analytics import get_channel_roi_data
    return JSONResponse(content=get_channel_roi_data(campaign_id))

@router.get('/dashboard/ui-lab/funnel')
async def ui_lab_funnel(campaign_id: str):
    from app.services.analytics import get_ui_lab_funnel_data
    return JSONResponse(content=get_ui_lab_funnel_data(campaign_id))

@router.get('/dashboard/ui-lab/heatmap')
async def ui_lab_heatmap(campaign_id: str):
    from app.services.analytics import get_ui_lab_heatmap_data
    return JSONResponse(content=get_ui_lab_heatmap_data(campaign_id))


@router.get('/dashboard/sales-alerts')
async def get_sales_alerts(campaign_id: str):
    from app.services.analytics import get_prioritized_sales_targets
    from fastapi.responses import JSONResponse
    return JSONResponse(content=get_prioritized_sales_targets(campaign_id))


from app.services.analytics import get_asset_personas

@router.get("/asset-personas")
async def get_asset_personas_endpoint(campaign_id: str, asset_name: str, type: str):
    users = get_asset_personas(campaign_id, asset_name, type)
    return JSONResponse(content=users)

