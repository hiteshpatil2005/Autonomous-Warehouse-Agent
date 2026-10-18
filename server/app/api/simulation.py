"""
WareBot AI — Simulation REST and WebSocket API Routes
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.schemas.simulation import (
    ActionResponse,
    CreateSimulationRequest,
    ObstacleTriggerRequest,
    ReplenishRequest,
    SimulationMetricsResponse,
    SimulationStateResponse,
    SimulationStatusResponse,
    SpeedRequest,
    StepRequest,
    UrgentOrderRequest,
)
from app.services.connection_manager import ws_manager
from app.services.simulation_manager import sim_manager

logger = logging.getLogger("warebot.api.simulation")

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


# ── REST Lifecycle Endpoints ────────────────────────────────────────────────

@router.post(
    "/create",
    response_model=SimulationStateResponse,
    summary="Create a new simulation scenario",
)
async def create_simulation(req: CreateSimulationRequest = CreateSimulationRequest()):
    """Create a new warehouse map and order queue with optional reproducible seed."""
    try:
        state = await sim_manager.create_simulation(
            seed=req.seed,
            random_layout=req.random_layout,
        )
        return state
    except Exception as exc:
        logger.error(f"Failed to create simulation: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/state",
    response_model=SimulationStateResponse,
    summary="Get current full simulation state",
)
async def get_simulation_state():
    """Retrieve full JSON snapshot of grid, robot, orders, metrics, inspector, and events."""
    return sim_manager.get_full_state()


@router.post(
    "/start",
    response_model=SimulationStatusResponse,
    summary="Start continuous simulation execution",
)
async def start_simulation():
    """Start autonomous robot execution loop."""
    res = await sim_manager.start()
    return res


@router.post(
    "/pause",
    response_model=SimulationStatusResponse,
    summary="Pause simulation execution",
)
async def pause_simulation():
    """Pause execution loop without losing state."""
    res = await sim_manager.pause()
    return res


@router.post(
    "/resume",
    response_model=SimulationStatusResponse,
    summary="Resume execution from pause",
)
async def resume_simulation():
    """Resume continuous execution loop."""
    res = await sim_manager.resume()
    return res


@router.post(
    "/reset",
    response_model=SimulationStateResponse,
    summary="Reset simulation to initial state",
)
async def reset_simulation():
    """Reset robot, orders, metrics, and obstacles cleanly."""
    state = await sim_manager.reset()
    return state


@router.post(
    "/step",
    response_model=SimulationStateResponse,
    summary="Advance simulation by exact tick count",
)
async def step_simulation(req: StepRequest = StepRequest()):
    """Advance simulation by 1 (or N) ticks while paused or idle."""
    try:
        state = await sim_manager.step(steps=req.steps)
        return state
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/speed",
    response_model=SimulationStatusResponse,
    summary="Update execution speed level",
)
async def set_speed(req: SpeedRequest):
    """Set execution speed (1 to 5)."""
    sim_manager.set_speed(req.speed)
    return sim_manager.get_status_summary()


# ── Scenario Event Triggers ─────────────────────────────────────────────────

@router.post(
    "/obstacles",
    response_model=ActionResponse,
    summary="Add temporary obstacle",
)
async def add_obstacle(req: ObstacleTriggerRequest = ObstacleTriggerRequest()):
    """
    Place a temporary obstacle on the warehouse floor.
    Validates that target cell is not on a robot, station, or shelf.
    """
    try:
        res = await sim_manager.add_obstacle(
            row=req.row,
            col=req.col,
            duration_ticks=req.duration_ticks,
        )
        return ActionResponse(status=res["status"], message=res["message"], data=res.get("data"))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/orders/urgent",
    response_model=ActionResponse,
    summary="Inject an urgent priority order",
)
async def add_urgent_order():
    """Create a high-urgency order and append to queue."""
    try:
        res = await sim_manager.add_urgent_order()
        return ActionResponse(status=res["status"], message=res["message"], data={"order_id": res["order_id"]})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/inventory/replenish",
    response_model=ActionResponse,
    summary="Replenish shelf stock",
)
async def replenish_inventory(req: ReplenishRequest = ReplenishRequest()):
    """Restock a specific or random shelf."""
    try:
        res = await sim_manager.replenish_inventory(
            shelf_id=req.shelf_id,
            amount=req.amount,
        )
        return ActionResponse(status=res["status"], message=res["message"], data=res.get("data"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Query & Sub-Resource Endpoints ──────────────────────────────────────────

@router.get("/orders", summary="Retrieve all orders and their current status")
async def get_orders():
    """Retrieve full list of warehouse orders."""
    return {"orders": sim_manager.get_orders()}


@router.get("/metrics", response_model=Dict[str, Any], summary="Retrieve simulation metrics")
async def get_metrics():
    """Retrieve live metrics snapshot."""
    return sim_manager.get_metrics()


@router.get("/events", summary="Retrieve recent activity log events")
async def get_events():
    """Retrieve chronological simulation event stream."""
    return {"events": sim_manager.get_events()}


@router.get("/decision", summary="Retrieve latest AI decision inspector details")
async def get_decision():
    """Retrieve latest decision inspector breakdown, utility scores, and reasons."""
    return {"decision": sim_manager.get_decision()}


# ── WebSocket Real-Time Stream ──────────────────────────────────────────────

@router.websocket("/stream")
async def simulation_stream(websocket: WebSocket):
    """
    WebSocket endpoint streaming live warehouse simulation updates.
    Sends initial snapshot immediately on connect, then broadcasts
    all subsequent state changes and events.
    """
    await ws_manager.connect(websocket)

    # Immediately push initial authoritative state snapshot
    try:
        initial_state = sim_manager.get_full_state()
        await websocket.send_json({
            "type": "simulation_state",
            "simulation_id": sim_manager.simulation_id,
            "data": initial_state,
        })
    except Exception as exc:
        logger.warning(f"Error sending initial WebSocket snapshot: {exc}")
        ws_manager.disconnect(websocket)
        return

    # Keep connection open and accept client messages (ping, commands)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle client-directed WebSocket messages if any
            action = data.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong"})
            elif action == "step":
                await sim_manager.step(steps=data.get("steps", 1))
            elif action == "pause":
                await sim_manager.pause()
            elif action == "resume":
                await sim_manager.resume()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug(f"WebSocket client loop terminated: {exc}")
        ws_manager.disconnect(websocket)
