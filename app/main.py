"""
Campaign Telemetry Engine (CTE) - Application Entrypoint

This module bootstraps the FastAPI application, mounts static assets and Jinja2
HTML templates, registers the route controllers (Dashboard and AI Chat), and
defines the top-level navigation routes (Lobby, Root Redirect, and Health Probe).

Architecture Note:
    The application follows a Server-Driven UI (SDUI) pattern using HTMX and
    Alpine.js. The FastAPI backend serves both full workspace pages and modular
    HTML partials that are swapped dynamically into the DOM without client-side
    build tooling.
"""

from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import chat, dashboard

# Load environment configuration (API keys, DB paths, Redis URL)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager controlling startup and shutdown events.
    Database connections and worker pools are maintained per-request/service.
    """
    print("Application starting up...")
    yield
    print("Application shutting down...")


# Initialize application instance
app = FastAPI(
    lifespan=lifespan,
    title="Wood Group Campaign Telemetry Engine",
    version="1.0.0",
    description="ABM telemetry dashboard with autonomous AI copilot and multi-touch attribution"
)

# Static file serving and HTML template configuration
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount API & View Routers under the standard /api prefix
app.include_router(dashboard.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/lobby", response_class=HTMLResponse)
async def get_lobby(request: Request):
    """
    Campaign Selection Lobby.
    Serves the entrypoint card grid where users select which B2B campaign to inspect.
    """
    from app.services.analytics import get_all_campaigns
    campaigns = get_all_campaigns()
    return templates.TemplateResponse(
        request=request,
        name="lobby.html",
        context={"campaigns": campaigns}
    )


@app.get("/")
async def read_root():
    """
    Root redirect. Sends first-time visitors directly to the campaign lobby.
    """
    return RedirectResponse(url="/lobby")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serves the modern SVG favicon directly to browsers requesting /favicon.ico."""
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "favicon.svg"), media_type="image/svg+xml")


@app.get("/health")
async def health_check():
    """
    Health check probe for container platforms (Render, Kubernetes, Docker).
    Returns HTTP 200 with JSON payload to verify process responsiveness.
    """
    return {"status": "ok"}
