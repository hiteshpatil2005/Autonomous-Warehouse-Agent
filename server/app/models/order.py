"""
WareBot AI — Order Model and Lifecycle
"""

from enum import Enum
from typing import Optional, Tuple
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Priority classifications with associated urgency values."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

    @property
    def weight(self) -> float:
        weights = {
            Priority.LOW: 1.0,
            Priority.MEDIUM: 2.0,
            Priority.HIGH: 3.5,
            Priority.URGENT: 5.0,
        }
        return weights[self]


class OrderStatus(str, Enum):
    """
    Structured order lifecycle statuses:
    PENDING -> ASSIGNED -> PICKING -> RETURNING -> PACKING -> COMPLETED
    Exceptions: BLOCKED, CANCELLED
    """
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    PICKING = "PICKING"
    RETURNING = "RETURNING"
    PACKING = "PACKING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    """Warehouse customer pick-and-pack order."""
    order_id: str
    product_id: str
    product_name: str
    quantity: int = Field(default=1, ge=1)
    priority: Priority = Priority.MEDIUM
    shelf_id: str
    shelf_pos: Tuple[int, int]
    
    # Timing & Lifespan
    created_tick: int = 0
    deadline_tick: Optional[int] = None
    assigned_tick: Optional[int] = None
    completed_tick: Optional[int] = None
    completion_time_ticks: Optional[int] = None

    # Lifecycle state
    status: OrderStatus = OrderStatus.PENDING
    assigned_robot_id: Optional[str] = None
    energy_consumed: float = 0.0

    def is_overdue(self, current_tick: int) -> bool:
        """Check if order has passed its deadline and is not completed."""
        if self.deadline_tick is not None and self.status != OrderStatus.COMPLETED:
            return current_tick > self.deadline_tick
        return False

    def remaining_deadline(self, current_tick: int) -> Optional[int]:
        if self.deadline_tick is None:
            return None
        return self.deadline_tick - current_tick
