"""
WareBot AI — Health Check Endpoint
"""

from fastapi import APIRouter

router = APIRouter(tags=["Infrastructure"])
health_router = router



@router.get("/health")
async def health_check():
    """Health check endpoint — confirms server and simulation engine are operational."""
    return {
        "status": "ok",
        "service": "WareBot AI",
        "version": "0.2.0",
        "engine": "autonomous-simulation-engine",
        "capabilities": [
            "map_generator_50_shelves",
            "astar_pathfinding",
            "utility_decision_engine",
            "battery_management",
            "dynamic_events",
        ],
    }
