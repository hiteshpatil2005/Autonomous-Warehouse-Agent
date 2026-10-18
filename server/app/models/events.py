"""
WareBot AI — Event Models
"""

from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event taxonomy for activity logs and simulation tracking."""
    SIMULATION_START = "SIMULATION_START"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_ASSIGNED = "ORDER_ASSIGNED"
    PICKING_STARTED = "PICKING_STARTED"
    PICKING_COMPLETED = "PICKING_COMPLETED"
    RETURNING_TO_PACKING = "RETURNING_TO_PACKING"
    PACKING_STARTED = "PACKING_STARTED"
    PACKING_COMPLETED = "PACKING_COMPLETED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    LOW_BATTERY_WARNING = "LOW_BATTERY_WARNING"
    CHARGING_STARTED = "CHARGING_STARTED"
    CHARGING_COMPLETED = "CHARGING_COMPLETED"
    OBSTACLE_DETECTED = "OBSTACLE_DETECTED"
    OBSTACLE_EXPIRED = "OBSTACLE_EXPIRED"
    ROUTE_REPLANNED = "ROUTE_REPLANNED"
    STOCK_REPLENISHED = "STOCK_REPLENISHED"
    DEADLINE_MISSED = "DEADLINE_MISSED"
    ROBOT_BLOCKED = "ROBOT_BLOCKED"
    TASK_REJECTED = "TASK_REJECTED"


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class SimEvent(BaseModel):
    """Discrete simulation event log item."""
    id: str
    tick: int
    event_type: EventType
    severity: EventSeverity
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
