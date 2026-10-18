"""
WareBot AI — Battery Management and Energy Safety Logic
"""

from typing import Optional, Tuple

from app.core.config import SimulationConfig, default_config
from app.models.robot import Robot
from app.models.warehouse import WarehouseMap
from app.simulation.pathfinding import find_path, find_path_to_adjacent, manhattan_distance


class BatteryManager:
    """
    Manages energy consumption, replenishment, feasibility checks,
    and safe operational reserves.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or default_config

    def estimate_energy_cost(
        self,
        warehouse_map: WarehouseMap,
        robot_pos: Tuple[int, int],
        shelf_pos: Tuple[int, int],
        packing_pos: Tuple[int, int],
        charging_pos: Tuple[int, int],
    ) -> Tuple[int, int, int, float]:
        """
        Calculate step distances and estimated energy for a complete mission cycle:
        1. Robot -> Shelf adjacent
        2. Shelf adjacent -> Packing station
        3. Packing station -> Charging station
        Returns (dist_to_shelf, dist_to_packing, dist_to_charger, total_energy_needed)
        """
        # Distance 1: Robot -> Shelf
        path1 = find_path_to_adjacent(warehouse_map, robot_pos, shelf_pos)
        if path1 is None:
            dist1 = manhattan_distance(robot_pos, shelf_pos)
        else:
            dist1 = max(0, len(path1) - 1)
        
        # Shelf pick location
        pick_loc = path1[-1] if path1 else shelf_pos

        # Distance 2: Shelf -> Packing
        path2 = find_path(warehouse_map, pick_loc, packing_pos)
        if path2 is None:
            dist2 = manhattan_distance(pick_loc, packing_pos)
        else:
            dist2 = max(0, len(path2) - 1)

        # Distance 3: Packing -> Charging
        path3 = find_path(warehouse_map, packing_pos, charging_pos)
        if path3 is None:
            dist3 = manhattan_distance(packing_pos, charging_pos)
        else:
            dist3 = max(0, len(path3) - 1)

        total_steps = dist1 + dist2 + dist3
        total_energy = (total_steps * self.config.movement_cost) + self.config.min_safety_reserve

        return dist1, dist2, dist3, total_energy

    def check_task_feasibility(
        self,
        warehouse_map: WarehouseMap,
        robot: Robot,
        shelf_pos: Tuple[int, int],
        packing_pos: Tuple[int, int],
        charging_pos: Tuple[int, int],
    ) -> Tuple[bool, float, str]:
        """
        Evaluate if current battery allows completing the order safely
        with mandatory reserve for returning to the charging dock.
        """
        d1, d2, d3, energy_needed = self.estimate_energy_cost(
            warehouse_map=warehouse_map,
            robot_pos=robot.pos,
            shelf_pos=shelf_pos,
            packing_pos=packing_pos,
            charging_pos=charging_pos,
        )

        if robot.battery < energy_needed:
            reason = (
                f"Insufficient battery ({robot.battery:.1f}%). "
                f"Estimated requirement: {energy_needed:.1f}% "
                f"(Trip: {d1 + d2 + d3} steps + {self.config.min_safety_reserve:.1f}% reserve)"
            )
            return False, energy_needed, reason

        return True, energy_needed, "Battery feasible"

    def consume_movement(self, robot: Robot, steps: int = 1) -> float:
        """Deduct movement energy per step. Clamps to zero."""
        cost = steps * self.config.movement_cost
        robot.battery = max(0.0, round(robot.battery - cost, 2))
        return cost

    def charge_tick(self, robot: Robot) -> float:
        """Recharge battery by configured rate at charging station. Clamps to capacity."""
        if robot.battery >= self.config.battery_capacity:
            return 0.0

        gained = min(
            self.config.charging_rate,
            self.config.battery_capacity - robot.battery,
        )
        robot.battery = min(self.config.battery_capacity, round(robot.battery + gained, 2))
        return gained

    def is_critical(self, robot: Robot) -> bool:
        """Returns True if battery is below critical threshold."""
        return robot.battery <= self.config.critical_battery_threshold

    def is_fully_charged(self, robot: Robot) -> bool:
        """Returns True if battery is at maximum capacity."""
        return robot.battery >= self.config.battery_capacity
