"""
WareBot AI — Pydantic Schemas for API Serialization and Request Models
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────────────────

class CreateSimulationRequest(BaseModel):
    """Payload for initializing a new simulation scenario."""
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible map and orders")
    random_layout: bool = Field(default=False, description="Whether to use random shelf layout instead of structured grid")


class StepRequest(BaseModel):
    """Parameters when triggering discrete simulation steps."""
    steps: int = Field(default=1, ge=1, le=100, description="Number of ticks to advance")


class SpeedRequest(BaseModel):
    """Parameters for tuning simulation execution frequency."""
    speed: int = Field(default=2, ge=1, le=5, description="Speed multiplier (1=1Hz, 2=5Hz, 3=8Hz, 4=12Hz, 5=20Hz)")


class ObstacleTriggerRequest(BaseModel):
    """Payload for placing an obstacle."""
    row: Optional[int] = Field(default=None, ge=0, le=29, description="Target row coordinate (0-29)")
    col: Optional[int] = Field(default=None, ge=0, le=29, description="Target col coordinate (0-29)")
    duration_ticks: int = Field(default=15, ge=1, le=500, description="Ticks until obstacle expires")


class UrgentOrderRequest(BaseModel):
    """Payload for injecting an urgent order."""
    shelf_id: Optional[str] = Field(default=None, description="Specific shelf ID if desired")


class ReplenishRequest(BaseModel):
    """Payload for manual inventory replenishment."""
    shelf_id: Optional[str] = Field(default=None, description="Specific shelf ID to restock")
    amount: int = Field(default=5, ge=1, le=50, description="Quantity to add to inventory")


# ── Response Models ─────────────────────────────────────────────────────────

class ActionResponse(BaseModel):
    """Generic status response for operational commands."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class SimulationStatusResponse(BaseModel):
    """High-level simulation lifecycle status."""
    status: str
    simulation_id: str
    tick: int
    elapsed_time_seconds: float
    is_running: bool


class SimulationMetricsResponse(BaseModel):
    """Metrics snapshot response schema."""
    tick: int
    elapsed_time_seconds: float
    total_orders: int
    pending_orders: int
    in_progress_orders: int
    completed_orders: int
    overdue_orders: int
    robot_battery: float
    distance_travelled: int
    movement_count: int
    charging_time_ticks: int
    route_replanning_count: int
    blocked_movement_attempts: int
    successful_deliveries: int
    average_order_completion_ticks: float
    deadline_success_rate_percent: float
    energy_consumed_per_completed_order: float


class SimulationStateResponse(BaseModel):
    """Complete simulation snapshot schema."""
    tick: int
    elapsed_time_seconds: float
    grid: Dict[str, Any]
    robot: Dict[str, Any]
    orders: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    decision_inspector: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []
    status: Optional[str] = None
    simulation_id: Optional[str] = None
