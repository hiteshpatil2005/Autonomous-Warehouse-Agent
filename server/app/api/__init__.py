from app.api.health import router as health_router
from app.api.simulation import router as simulation_router
from app.api.benchmark import router as benchmark_router

__all__ = ["health_router", "simulation_router", "benchmark_router"]
