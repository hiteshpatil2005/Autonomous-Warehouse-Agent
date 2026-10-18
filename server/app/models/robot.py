"""
WareBot AI — Robot Model
"""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class RobotState(str, Enum):
    """Finite states for autonomous warehouse robot."""
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    PICKING = "PICKING"
    RETURNING = "RETURNING"
    PACKING = "PACKING"
    CHARGING = "CHARGING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"


class Robot(BaseModel):
    """
    Autonomous mobile robot representation.
    Maintains location, energy, current goal, path state, and execution history.
    """
    robot_id: str = "RB-01"
    row: int = 28
    col: int = 1
    state: RobotState = RobotState.IDLE
    battery: float = Field(default=100.0, ge=0.0, le=100.0)

    # Task tracking
    current_order_id: Optional[str] = None
    target_pos: Optional[Tuple[int, int]] = None
    target_type: Optional[str] = None  # "SHELF", "PACKING", "CHARGING"
    
    # Navigation tracking
    planned_route: List[Tuple[int, int]] = Field(default_factory=list)
    traversed_path: List[Tuple[int, int]] = Field(default_factory=list)
    total_distance_travelled: int = 0
    completed_movement_count: int = 0

    # Operational status
    current_action: str = "Awaiting mission"
    action_ticks_remaining: int = 0

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)

    def set_pos(self, new_pos: Tuple[int, int]):
        self.row, self.col = new_pos

    def is_battery_critical(self, threshold: float = 20.0) -> bool:
        return self.battery <= threshold
