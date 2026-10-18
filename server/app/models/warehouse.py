"""
WareBot AI — Warehouse Models
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class CellType(str, Enum):
    """Grid cell types for 30x30 warehouse map."""
    FLOOR = "floor"
    SHELF = "shelf"
    ROBOT = "robot"
    PACKING = "packing"
    CHARGING = "charging"
    OBSTACLE = "obstacle"


class Shelf(BaseModel):
    """Warehouse inventory shelf."""
    shelf_id: str
    row: int
    col: int
    product_id: str
    product_name: str
    stock: int = Field(default=10, ge=0)
    max_capacity: int = Field(default=20, ge=1)

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)


class WarehouseMap(BaseModel):
    """
    Representation of the 30x30 warehouse environment.
    Includes shelves, stationary hubs, dynamic obstacles, and walkability checks.
    """
    rows: int = 30
    cols: int = 30
    shelves: List[Shelf] = Field(default_factory=list)
    robot_start: Tuple[int, int] = (28, 1)
    packing_station: Tuple[int, int] = (28, 14)
    charging_station: Tuple[int, int] = (28, 27)
    # Temporary obstacles: map of (row, col) string key "r,c" -> expiry_tick
    obstacles: Dict[str, int] = Field(default_factory=dict)

    # Shelf lookup caches
    def get_shelf_by_id(self, shelf_id: str) -> Optional[Shelf]:
        for s in self.shelves:
            if s.shelf_id == shelf_id:
                return s
        return None

    def get_shelf_at(self, row: int, col: int) -> Optional[Shelf]:
        for s in self.shelves:
            if s.row == row and s.col == col:
                return s
        return None

    def is_shelf(self, row: int, col: int) -> bool:
        return any(s.row == row and s.col == col for s in self.shelves)

    def is_obstacle(self, row: int, col: int) -> bool:
        return f"{row},{col}" in self.obstacles

    def is_in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_walkable(self, row: int, col: int) -> bool:
        """A cell is walkable if inside bounds, not a shelf, and not an active obstacle."""
        if not self.is_in_bounds(row, col):
            return False
        if self.is_shelf(row, col):
            return False
        if self.is_obstacle(row, col):
            return False
        return True

    def get_cell_type(self, row: int, col: int, robot_pos: Optional[Tuple[int, int]] = None) -> CellType:
        """Determine display cell type at coordinates."""
        if robot_pos and (row, col) == robot_pos:
            return CellType.ROBOT
        if (row, col) == self.packing_station:
            return CellType.PACKING
        if (row, col) == self.charging_station:
            return CellType.CHARGING
        if self.is_obstacle(row, col):
            return CellType.OBSTACLE
        if self.is_shelf(row, col):
            return CellType.SHELF
        return CellType.FLOOR

    def get_adjacent_walkable(self, target_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get walkable orthogonal neighbours adjacent to target cell."""
        tr, tc = target_pos
        candidates = [
            (tr - 1, tc),
            (tr + 1, tc),
            (tr, tc - 1),
            (tr, tc + 1)
        ]
        return [(r, c) for r, c in candidates if self.is_walkable(r, c)]
