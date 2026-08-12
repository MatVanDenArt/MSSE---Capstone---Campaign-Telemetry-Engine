from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services.analytics import evaluate_trickle_threshold, get_account_penetration, calculate_blended_cpa, get_kpi_benchmarks, generate_strategic_tldr, get_asset_impact_matrix, get_all_campaigns, get_timeline_chart_data, get_asset_fatigue, generate_next_best_actions, get_audience_network_data, get_sankey_data, get_asset_timeline_data
import sqlite3

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
        "assets": assets
    })

@router.get("/dashboard/performance", response_class=HTMLResponse)
async def get_performance(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    chart_data = get_timeline_chart_data(campaign_id, timeframe)
    matrix = get_asset_impact_matrix(campaign_id, timeframe)
    return templates.TemplateResponse(request=request, name="components/performance.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "chart_data": chart_data,
        "matrix": matrix
    })

@router.get("/dashboard/audience", response_class=HTMLResponse)
async def get_audience(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    data = get_account_penetration(campaign_id)
    penetration = data.get("account_penetration", {})
    return templates.TemplateResponse(request=request, name="components/audience.html", context={
        "campaign_id": campaign_id,
        "timeframe": timeframe,
        "penetration": penetration
    })

@router.get("/dashboard/tldr", response_class=HTMLResponse)
async def get_tldr(request: Request, campaign_id: str = "CMP_LIVE_DECARBONIZATION_25_26", timeframe: int = 0):
    benchmarks = get_kpi_benchmarks(campaign_id, timeframe)
    tldr = generate_strategic_tldr(benchmarks)
    return HTMLResponse(content=tldr)

@router.get("/dashboard/account-penetration", response_class=HTMLResponse)
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

