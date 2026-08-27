def update_routes():
    with open('app/api/dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_route = """@router.get('/dashboard/audience-data-scoped')
async def get_audience_data_scoped(campaign_id: str):
    from app.services.analytics import get_scoped_audience_data
    from fastapi.responses import JSONResponse
    return JSONResponse(content=get_scoped_audience_data(campaign_id))

"""

    content = content.replace("@router.get('/dashboard/audience-data')", new_route + "@router.get('/dashboard/audience-data')")

    with open('app/api/dashboard.py', 'w', encoding='utf-8') as f:
        f.write(content)

update_routes()
