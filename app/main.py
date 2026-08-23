from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

from app.data.generator import generate_b2b_data
from app.data.etl import run_etl
from app.api import chat, dashboard, dashboard_v2

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Application starting up...")
    # print("Triggering Data Seeding...")
    # dataframes = generate_b2b_data()
    # run_etl(dataframes, db_path="capstone.db")
    # print("Data Seeding Complete.")
    
    yield
    
    # Shutdown logic
    print("Application shutting down...")

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="app/templates")

from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan, title="Wood Group Campaign Telemetry Engine")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(dashboard_v2.router, prefix="/api/v2")
app.include_router(chat.router, prefix="/api")

@app.get("/lobby", response_class=HTMLResponse)
async def get_lobby(request: Request):
    from app.services.analytics import get_all_campaigns
    campaigns = get_all_campaigns()
    return templates.TemplateResponse(request=request, name="lobby.html", context={"campaigns": campaigns})

@app.get("/")
async def read_root():
    """
    Redirect root to the lobby.
    """
    return RedirectResponse(url="/lobby")
