"""
WareBot AI — Autonomous Utility-Based Decision Engine
Evaluates pending orders using multi-factor utility scoring and hard safety constraints.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.config import SimulationConfig, default_config
from app.models.order import Order, OrderStatus, Priority
from app.models.robot import Robot
from app.models.warehouse import WarehouseMap
from app.simulation.battery_manager import BatteryManager
from app.simulation.pathfinding import find_path, find_path_to_adjacent, manhattan_distance


class CandidateEvaluation(BaseModel):
    """Detailed score breakdown for an order candidate."""
    order_id: str
    product_name: str
    priority: Priority
    shelf_id: str
    is_feasible: bool
    rejection_reason: Optional[str] = None
    urgency_score: float = 0.0
    deadline_score: float = 0.0
    proximity_shelf_score: float = 0.0
    proximity_packing_score: float = 0.0
    inventory_score: float = 0.0
    route_risk_penalty: float = 0.0
    total_utility: float = 0.0
    est_distance: int = 0
    est_energy_cost: float = 0.0


class DecisionResult(BaseModel):
    """Full decision inspector snapshot returned by the autonomous decision engine."""
    selected_order_id: Optional[str] = None
    selected_order: Optional[Order] = None
    winning_score: float = 0.0
    explanation: str
    candidates_count: int = 0
    feasible_count: int = 0
    rejected_count: int = 0
    evaluations: List[CandidateEvaluation] = Field(default_factory=list)
    rejections: Dict[str, str] = Field(default_factory=dict)
    est_route_distance: int = 0
    est_energy_cost: float = 0.0
    battery_feasible: bool = True


class AutonomousDecisionEngine:
    """
    Transparent utility-based decision engine implementing hard safety constraints
    and weighted multi-factor evaluation for order dispatch.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or default_config
        self.battery_manager = BatteryManager(self.config)

    def evaluate_order(
        self,
        order: Order,
        robot: Robot,
        warehouse_map: WarehouseMap,
        current_tick: int,
    ) -> CandidateEvaluation:
        """Evaluate a single pending order candidate against safety constraints and utility weights."""
        eval_item = CandidateEvaluation(
            order_id=order.order_id,
            product_name=order.product_name,
            priority=order.priority,
            shelf_id=order.shelf_id,
            is_feasible=True,
        )

        # ── Constraint 1: Order Status Check ──
        if order.status != OrderStatus.PENDING:
            eval_item.is_feasible = False
            eval_item.rejection_reason = f"Order status is {order.status.value}, not PENDING"
            return eval_item

        # ── Constraint 2: Inventory Availability Check ──
        shelf = warehouse_map.get_shelf_by_id(order.shelf_id)
        if not shelf:
            eval_item.is_feasible = False
            eval_item.rejection_reason = f"Shelf {order.shelf_id} not found in warehouse"
            return eval_item

        if shelf.stock < order.quantity:
            eval_item.is_feasible = False
            eval_item.rejection_reason = (
                f"Insufficient stock for {order.product_name} on {shelf.shelf_id} "
                f"({shelf.stock} available, {order.quantity} required)"
            )
            return eval_item

        # ── Constraint 3: Reachability Check ──
        shelf_path = find_path_to_adjacent(warehouse_map, robot.pos, shelf.pos)
        if not shelf_path:
            eval_item.is_feasible = False
            eval_item.rejection_reason = f"No passable route to shelf {shelf.shelf_id}"
            return eval_item

        pick_pos = shelf_path[-1]
        packing_path = find_path(warehouse_map, pick_pos, warehouse_map.packing_station)
        if not packing_path:
            eval_item.is_feasible = False
            eval_item.rejection_reason = "No passable route from shelf to packing station"
            return eval_item

        charger_path = find_path(warehouse_map, warehouse_map.packing_station, warehouse_map.charging_station)
        if not charger_path:
            eval_item.is_feasible = False
            eval_item.rejection_reason = "No passable route from packing station to charging station"
            return eval_item

        # ── Constraint 4: Battery Feasibility Check ──
        feasible_bat, energy_needed, reason = self.battery_manager.check_task_feasibility(
            warehouse_map=warehouse_map,
            robot=robot,
            shelf_pos=shelf.pos,
            packing_pos=warehouse_map.packing_station,
            charging_pos=warehouse_map.charging_station,
        )

        d1 = max(0, len(shelf_path) - 1)
        d2 = max(0, len(packing_path) - 1)
        eval_item.est_distance = d1 + d2
        eval_item.est_energy_cost = energy_needed

        if not feasible_bat:
            eval_item.is_feasible = False
            eval_item.rejection_reason = reason
            return eval_item

        # ── Utility Scoring for Feasible Candidates ──
        # Factor A: Priority Urgency (0.0 to 1.0 * urgency_weight)
        urgency_factor = order.priority.weight / 5.0
        eval_item.urgency_score = round(urgency_factor * self.config.urgency_weight, 2)

        # Factor B: Deadline Pressure
        if order.deadline_tick is not None:
            ticks_left = order.deadline_tick - current_tick
            if ticks_left <= 0:
                deadline_factor = 1.0  # Overdue - highest urgency
            else:
                deadline_factor = max(0.0, min(1.0, 1.0 - (ticks_left / 120.0)))
        else:
            deadline_factor = 0.25
        eval_item.deadline_score = round(deadline_factor * self.config.deadline_weight, 2)

        # Factor C: Distance to Shelf (Proximity bonus)
        # Max theoretical distance in 30x30 grid is 60
        max_grid_dist = self.config.grid_rows + self.config.grid_cols
        dist_robot_shelf = d1
        prox_shelf_factor = max(0.0, 1.0 - (dist_robot_shelf / max_grid_dist))
        eval_item.proximity_shelf_score = round(prox_shelf_factor * self.config.distance_shelf_weight, 2)

        # Factor D: Distance from Shelf to Packing Station
        dist_shelf_packing = d2
        prox_pack_factor = max(0.0, 1.0 - (dist_shelf_packing / max_grid_dist))
        eval_item.proximity_packing_score = round(prox_pack_factor * self.config.distance_packing_weight, 2)

        # Factor E: Stock Availability (high stock is lower risk)
        stock_factor = min(1.0, shelf.stock / float(shelf.max_capacity))
        eval_item.inventory_score = round(stock_factor * self.config.inventory_weight, 2)

        # Factor F: Route Obstacle Risk (penalty if temporary obstacles are nearby)
        risk_penalty = 0.0
        for obs_key in warehouse_map.obstacles:
            r_str, c_str = obs_key.split(",")
            obs_coord = (int(r_str), int(c_str))
            if manhattan_distance(shelf.pos, obs_coord) <= 2:
                risk_penalty += 3.0
        eval_item.route_risk_penalty = round(min(15.0, risk_penalty), 2)

        eval_item.total_utility = round(
            eval_item.urgency_score
            + eval_item.deadline_score
            + eval_item.proximity_shelf_score
            + eval_item.proximity_packing_score
            + eval_item.inventory_score
            - eval_item.route_risk_penalty,
            2,
        )

        return eval_item

    def select_best_order(
        self,
        robot: Robot,
        orders: List[Order],
        warehouse_map: WarehouseMap,
        current_tick: int,
    ) -> DecisionResult:
        """
        Evaluate all pending orders, reject infeasible ones,
        and select the one with highest utility score.
        """
        pending_orders = [o for o in orders if o.status == OrderStatus.PENDING]
        evaluations: List[CandidateEvaluation] = []
        rejections: Dict[str, str] = {}

        for order in pending_orders:
            evaluation = self.evaluate_order(order, robot, warehouse_map, current_tick)
            evaluations.append(evaluation)
            if not evaluation.is_feasible:
                rejections[order.order_id] = evaluation.rejection_reason or "Unknown constraint violation"

        feasible_evals = [e for e in evaluations if e.is_feasible]

        if not feasible_evals:
            if not pending_orders:
                explanation = "Queue empty: No pending orders awaiting fulfillment."
            else:
                explanation = f"All {len(pending_orders)} pending orders rejected due to safety or battery constraints."

            return DecisionResult(
                selected_order_id=None,
                selected_order=None,
                winning_score=0.0,
                explanation=explanation,
                candidates_count=len(pending_orders),
                feasible_count=0,
                rejected_count=len(rejections),
                evaluations=evaluations,
                rejections=rejections,
                battery_feasible=not (robot.battery < self.config.critical_battery_threshold),
            )

        # Sort descending by total utility score
        feasible_evals.sort(key=lambda x: x.total_utility, reverse=True)
        winner = feasible_evals[0]

        selected_order = next((o for o in pending_orders if o.order_id == winner.order_id), None)

        explanation = (
            f"Selected {winner.order_id} ({winner.product_name}) with top utility score of {winner.total_utility:.1f}. "
            f"Priority: {winner.priority.value} (+{winner.urgency_score:.1f}), "
            f"Deadline pressure (+{winner.deadline_score:.1f}), "
            f"Shelf distance {winner.est_distance} steps (+{winner.proximity_shelf_score:.1f})."
        )

        return DecisionResult(
            selected_order_id=winner.order_id,
            selected_order=selected_order,
            winning_score=winner.total_utility,
            explanation=explanation,
            candidates_count=len(pending_orders),
            feasible_count=len(feasible_evals),
            rejected_count=len(rejections),
            evaluations=evaluations,
            rejections=rejections,
            est_route_distance=winner.est_distance,
            est_energy_cost=winner.est_energy_cost,
            battery_feasible=True,
        )
