from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

from app.data.generator import generate_b2b_data
from app.data.etl import run_etl
from app.api import chat, dashboard

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

app = FastAPI(lifespan=lifespan, title="Wood Group Campaign Telemetry Engine")

# Include Routers
app.include_router(dashboard.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/")
async def read_root():
    """
    Redirect root to the dashboard.
    """
    return RedirectResponse(url="/api/dashboard")
