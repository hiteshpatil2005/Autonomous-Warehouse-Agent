"""
WareBot AI — FastAPI Backend Application
Integrates the discrete-event warehouse simulation engine with REST control endpoints
and real-time WebSocket streaming.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_router, simulation_router, benchmark_router
from app.services.simulation_manager import sim_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("warebot.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to gracefully clean up background simulation tasks."""
    logger.info("WareBot AI backend initializing...")
    yield
    logger.info("WareBot AI backend shutting down... Stopping simulation tasks.")
    await sim_manager.pause()


app = FastAPI(
    title="WareBot AI API",
    description="Autonomous Warehouse Robot Simulation — Backend Engine, REST API & WebSocket Stream",
    version="0.3.0",
    lifespan=lifespan,
)

# Allow requests from standard frontend development ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5200",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health_router)
app.include_router(simulation_router)
app.include_router(benchmark_router)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
