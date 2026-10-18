"""
WareBot AI — Warehouse Simulation Engine
Orchestrates the complete warehouse environment, autonomous robot lifecycle,
pathfinding, battery safety, utility dispatch, and event progression.
"""

import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import SimulationConfig, default_config
from app.models.events import EventSeverity, EventType, SimEvent
from app.models.order import Order, OrderStatus, Priority
from app.models.robot import Robot, RobotState
from app.models.warehouse import Shelf, WarehouseMap
from app.simulation.battery_manager import BatteryManager
from app.simulation.decision_engine import AutonomousDecisionEngine, DecisionResult
from app.simulation.event_engine import EventEngine
from app.simulation.map_generator import generate_warehouse_map
from app.simulation.pathfinding import (
    find_path,
    find_path_to_adjacent,
    is_route_valid,
    manhattan_distance,
    recalculate_route,
)


class WarehouseEngine:
    """
    Complete discrete-event warehouse simulation engine.
    Exposes a deterministic step() interface for headless testing and API control.
    """

    def __init__(
        self,
        seed: Optional[int] = 42,
        config: Optional[SimulationConfig] = None,
        random_layout: bool = False,
    ):
        self.config = config or default_config
        self.seed = seed
        self.random_layout = random_layout
        self.rng = random.Random(seed)

        # Simulation Components
        self.battery_manager = BatteryManager(self.config)
        self.decision_engine = AutonomousDecisionEngine(self.config)
        self.event_engine = EventEngine(self.config, seed=seed)

        # Simulation State
        self.tick: int = 0
        self.elapsed_time_seconds: float = 0.0
        self.warehouse_map: WarehouseMap = generate_warehouse_map(
            seed=seed,
            config=self.config,
            random_layout=random_layout,
        )
        self.robot: Robot = Robot(
            robot_id="RB-01",
            row=self.config.robot_start_pos[0],
            col=self.config.robot_start_pos[1],
            state=RobotState.IDLE,
            battery=self.config.initial_battery,
        )
        self.orders: List[Order] = []
        self.event_history: List[SimEvent] = []
        self.last_decision: Optional[DecisionResult] = None

        # Metrics Tracking
        self.metrics: Dict[str, Any] = {
            "distance_travelled": 0,
            "movement_count": 0,
            "charging_time_ticks": 0,
            "route_replanning_count": 0,
            "blocked_movement_attempts": 0,
            "successful_deliveries": 0,
        }

        # Initialize scenario
        self._initialize_scenario()

    def _initialize_scenario(self):
        """Generate initial 10 orders and record startup event."""
        self.orders = self._generate_initial_orders()
        start_event = SimEvent(
            id=str(uuid.uuid4())[:8],
            tick=0,
            event_type=EventType.SIMULATION_START,
            severity=EventSeverity.INFO,
            message="Warehouse simulation initialized. Autonomous robot online.",
            data={"seed": self.seed, "total_shelves": len(self.warehouse_map.shelves)},
        )
        self.event_history.append(start_event)

    def _generate_initial_orders(self) -> List[Order]:
        """Generate exactly 10 initial orders assigned to warehouse shelves."""
        orders: List[Order] = []
        priorities = [
            Priority.URGENT,
            Priority.HIGH,
            Priority.HIGH,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.MEDIUM,
            Priority.MEDIUM,
            Priority.MEDIUM,
            Priority.LOW,
            Priority.LOW,
        ]

        eligible_shelves = [s for s in self.warehouse_map.shelves if s.stock > 0]
        self.rng.shuffle(eligible_shelves)

        for i in range(min(self.config.initial_order_count, len(eligible_shelves))):
            shelf = eligible_shelves[i]
            prio = priorities[i % len(priorities)]
            deadline = None
            if prio == Priority.URGENT:
                deadline = self.rng.randint(35, 60)
            elif prio == Priority.HIGH:
                deadline = self.rng.randint(70, 110)
            elif prio == Priority.MEDIUM and self.rng.random() > 0.4:
                deadline = self.rng.randint(90, 150)

            orders.append(
                Order(
                    order_id=f"ORD-{(i + 1):03d}",
                    product_id=shelf.product_id,
                    product_name=shelf.product_name,
                    quantity=1,
                    priority=prio,
                    shelf_id=shelf.shelf_id,
                    shelf_pos=shelf.pos,
                    created_tick=0,
                    deadline_tick=deadline,
                    status=OrderStatus.PENDING,
                )
            )

        return orders

    def reset(self, new_seed: Optional[int] = None):
        """Reset simulation engine state completely without retaining stale objects."""
        if new_seed is not None:
            self.seed = new_seed
        self.rng = random.Random(self.seed)
        self.event_engine = EventEngine(self.config, seed=self.seed)

        self.tick = 0
        self.elapsed_time_seconds = 0.0
        self.warehouse_map = generate_warehouse_map(
            seed=self.seed,
            config=self.config,
            random_layout=self.random_layout,
        )
        self.robot = Robot(
            robot_id="RB-01",
            row=self.config.robot_start_pos[0],
            col=self.config.robot_start_pos[1],
            state=RobotState.IDLE,
            battery=self.config.initial_battery,
        )
        self.orders = []
        self.event_history = []
        self.last_decision = None
        self.metrics = {
            "distance_travelled": 0,
            "movement_count": 0,
            "charging_time_ticks": 0,
            "route_replanning_count": 0,
            "blocked_movement_attempts": 0,
            "successful_deliveries": 0,
        }
        self._initialize_scenario()

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        for o in self.orders:
            if o.order_id == order_id:
                return o
        return None

    def step(self) -> List[SimEvent]:
        """
        Advance the simulation by exactly one discrete tick:
        1. Process dynamic events (obstacles, new orders, expirations).
        2. Evaluate robot autonomous state machine.
        3. Execute at most 1 grid movement or perform an action (pick/pack/charge).
        4. Update orders, metrics, and event log.
        """
        self.tick += 1
        self.elapsed_time_seconds += 1.0  # 1 tick = 1 virtual second
        tick_events: List[SimEvent] = []

        # ── Step 1: Process Dynamic Environmental Events ──
        env_events = self.event_engine.process_tick(
            current_tick=self.tick,
            warehouse_map=self.warehouse_map,
            robot=self.robot,
            orders=self.orders,
        )
        tick_events.extend(env_events)

        # ── Step 2 & 3: Autonomous Robot Decision & Execution ──
        robot_events = self._execute_robot_tick()
        tick_events.extend(robot_events)

        # Keep event history bounded
        self.event_history.extend(tick_events)
        if len(self.event_history) > 200:
            self.event_history = self.event_history[-200:]

        return tick_events

    def _execute_robot_tick(self) -> List[SimEvent]:
        """Core state machine logic for autonomous robot execution."""
        events: List[SimEvent] = []

        # ── STATE: IDLE ──
        if self.robot.state == RobotState.IDLE:
            # Check critical battery
            if self.battery_manager.is_critical(self.robot):
                ev = self._dispatch_to_charge(is_emergency=True)
                if ev:
                    events.append(ev)
                return events

            # Autonomous order dispatch using Utility Decision Engine
            decision = self.decision_engine.select_best_order(
                robot=self.robot,
                orders=self.orders,
                warehouse_map=self.warehouse_map,
                current_tick=self.tick,
            )
            self.last_decision = decision

            if decision.selected_order:
                order = decision.selected_order
                shelf = self.warehouse_map.get_shelf_by_id(order.shelf_id)

                if shelf and shelf.stock >= order.quantity:
                    route = find_path_to_adjacent(self.warehouse_map, self.robot.pos, shelf.pos)
                    if route and len(route) >= 1:
                        # Order accepted
                        order.status = OrderStatus.ASSIGNED
                        order.assigned_robot_id = self.robot.robot_id
                        order.assigned_tick = self.tick

                        self.robot.current_order_id = order.order_id
                        self.robot.target_pos = route[-1]
                        self.robot.target_type = "SHELF"
                        self.robot.planned_route = route[1:]  # Steps to take
                        self.robot.state = RobotState.NAVIGATING
                        self.robot.current_action = f"Navigating to {shelf.shelf_id} for {order.product_name}"

                        events.append(
                            SimEvent(
                                id=str(uuid.uuid4())[:8],
                                tick=self.tick,
                                event_type=EventType.ORDER_ASSIGNED,
                                severity=EventSeverity.INFO,
                                message=f"Robot {self.robot.robot_id} assigned order {order.order_id} ({order.product_name}). Route: {len(route) - 1} steps.",
                                data={"order_id": order.order_id, "score": decision.winning_score},
                            )
                        )
                        return events
                    else:
                        order.status = OrderStatus.BLOCKED
                        self.metrics["blocked_movement_attempts"] += 1
                        events.append(
                            SimEvent(
                                id=str(uuid.uuid4())[:8],
                                tick=self.tick,
                                event_type=EventType.ROBOT_BLOCKED,
                                severity=EventSeverity.WARNING,
                                message=f"Route to shelf {shelf.shelf_id} is blocked.",
                                data={"order_id": order.order_id},
                            )
                        )
            else:
                # No orders feasible. If battery is moderately low (<50%), head to charger
                if self.robot.battery < 50.0 and self.robot.pos != self.warehouse_map.charging_station:
                    ev = self._dispatch_to_charge(is_emergency=False)
                    if ev:
                        events.append(ev)
                    return events
                else:
                    self.robot.current_action = "Awaiting orders (Queue idle)"

        # ── STATE: NAVIGATING or RETURNING ──
        elif self.robot.state in (RobotState.NAVIGATING, RobotState.RETURNING):
            events.extend(self._handle_navigation())

        # ── STATE: PICKING ──
        elif self.robot.state == RobotState.PICKING:
            events.extend(self._handle_picking())

        # ── STATE: PACKING ──
        elif self.robot.state == RobotState.PACKING:
            events.extend(self._handle_packing())

        # ── STATE: CHARGING ──
        elif self.robot.state == RobotState.CHARGING:
            events.extend(self._handle_charging())

        # ── STATE: BLOCKED ──
        elif self.robot.state == RobotState.BLOCKED:
            events.extend(self._handle_blocked())

        # ── STATE: WAITING ──
        elif self.robot.state == RobotState.WAITING:
            self.robot.state = RobotState.IDLE
            self.robot.current_action = "Standby"

        return events

    def _dispatch_to_charge(self, is_emergency: bool = False) -> Optional[SimEvent]:
        """Dispatch robot to the charging station."""
        charger_pos = self.warehouse_map.charging_station
        if self.robot.pos == charger_pos:
            self.robot.state = RobotState.CHARGING
            self.robot.current_action = "Recharging at charging dock"
            return SimEvent(
                id=str(uuid.uuid4())[:8],
                tick=self.tick,
                event_type=EventType.CHARGING_STARTED,
                severity=EventSeverity.INFO,
                message=f"Robot docked at charging station. Battery at {self.robot.battery:.1f}%.",
                data={"battery": self.robot.battery},
            )

        route = find_path(self.warehouse_map, self.robot.pos, charger_pos)
        if route and len(route) >= 1:
            self.robot.planned_route = route[1:]
            self.robot.target_pos = charger_pos
            self.robot.target_type = "CHARGING"
            self.robot.state = RobotState.NAVIGATING
            self.robot.current_action = (
                f"Returning to charging dock ({'EMERGENCY' if is_emergency else 'maintenance'})"
            )

            severity = EventSeverity.WARNING if is_emergency else EventSeverity.INFO
            return SimEvent(
                id=str(uuid.uuid4())[:8],
                tick=self.tick,
                event_type=EventType.LOW_BATTERY_WARNING,
                severity=severity,
                message=f"Battery low ({self.robot.battery:.1f}%). Heading to charging station.",
                data={"battery": self.robot.battery},
            )
        else:
            self.robot.state = RobotState.BLOCKED
            self.metrics["blocked_movement_attempts"] += 1
            return SimEvent(
                id=str(uuid.uuid4())[:8],
                tick=self.tick,
                event_type=EventType.ROBOT_BLOCKED,
                severity=EventSeverity.ERROR,
                message="Cannot find clear path to charging station!",
            )

    def _handle_navigation(self) -> List[SimEvent]:
        """Advance robot one step along planned route with safety & replanning."""
        events: List[SimEvent] = []

        # Check if already reached destination cell
        if self.robot.target_pos and self.robot.pos == self.robot.target_pos:
            return self._arrive_at_target()

        if not self.robot.planned_route:
            # Replan or check arrival
            if self.robot.target_pos:
                new_route = find_path(self.warehouse_map, self.robot.pos, self.robot.target_pos)
                if new_route and len(new_route) > 1:
                    self.robot.planned_route = new_route[1:]
                else:
                    return self._arrive_at_target()
            else:
                self.robot.state = RobotState.IDLE
                return events

        # Peek next step
        next_step = self.robot.planned_route[0]

        # Route validation: is next step or upcoming path obstructed?
        path_obstructed = not self.warehouse_map.is_walkable(next_step[0], next_step[1]) or any(
            not self.warehouse_map.is_walkable(r, c) for r, c in self.robot.planned_route
        )
        if path_obstructed:
            # Path is obstructed! Attempt recalculation
            self.metrics["route_replanning_count"] += 1
            is_shelf = self.robot.target_type == "SHELF"
            recalculated = recalculate_route(
                warehouse_map=self.warehouse_map,
                current_pos=self.robot.pos,
                target_pos=self.robot.target_pos or self.robot.pos,
                is_shelf_target=is_shelf,
            )

            if recalculated and len(recalculated) > 1:
                self.robot.planned_route = recalculated[1:]
                next_step = self.robot.planned_route[0]
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.ROUTE_REPLANNED,
                        severity=EventSeverity.WARNING,
                        message=f"Obstacle bypassed! Route replanned ({len(recalculated) - 1} steps remaining).",
                    )
                )
            else:
                # Unable to replan around obstacle
                self.robot.state = RobotState.BLOCKED
                self.metrics["blocked_movement_attempts"] += 1
                self.robot.current_action = "Path blocked by obstacle"
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.ROBOT_BLOCKED,
                        severity=EventSeverity.ERROR,
                        message="Planned route blocked and no alternate path available.",
                    )
                )
                return events

        # Execute single grid-cell movement
        self.robot.planned_route.pop(0)
        self.robot.set_pos(next_step)

        # Update paths and distance
        self.robot.traversed_path.append(next_step)
        if len(self.robot.traversed_path) > 60:
            self.robot.traversed_path.pop(0)

        self.robot.total_distance_travelled += 1
        self.robot.completed_movement_count += 1
        self.metrics["distance_travelled"] += 1
        self.metrics["movement_count"] += 1

        # Consume battery
        energy_used = self.battery_manager.consume_movement(self.robot, steps=1)

        # Track energy per order
        if self.robot.current_order_id:
            ord_obj = self.get_order_by_id(self.robot.current_order_id)
            if ord_obj:
                ord_obj.energy_consumed += energy_used

        # Check if destination reached after step
        if self.robot.target_pos and self.robot.pos == self.robot.target_pos:
            events.extend(self._arrive_at_target())

        return events

    def _arrive_at_target(self) -> List[SimEvent]:
        """Handle target destination arrival (Shelf, Packing station, or Charging station)."""
        events: List[SimEvent] = []
        self.robot.planned_route = []

        if self.robot.target_type == "SHELF":
            order = self.get_order_by_id(self.robot.current_order_id or "")
            if not order:
                self.robot.state = RobotState.IDLE
                return events

            shelf = self.warehouse_map.get_shelf_by_id(order.shelf_id)
            # Recheck inventory safety
            if not shelf or shelf.stock < order.quantity:
                order.status = OrderStatus.BLOCKED
                self.robot.state = RobotState.IDLE
                self.robot.current_order_id = None
                self.robot.target_pos = None
                self.robot.target_type = None
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.TASK_REJECTED,
                        severity=EventSeverity.WARNING,
                        message=f"Stock unavailable at {order.shelf_id} on arrival. Order {order.order_id} suspended.",
                    )
                )
                return events

            # Start Picking
            self.robot.state = RobotState.PICKING
            self.robot.action_ticks_remaining = self.config.picking_duration_ticks
            order.status = OrderStatus.PICKING
            self.robot.current_action = f"Picking item from {shelf.shelf_id}"

            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.PICKING_STARTED,
                    severity=EventSeverity.INFO,
                    message=f"Robot arrived at shelf {shelf.shelf_id}. Picking {order.product_name}.",
                    data={"shelf_id": shelf.shelf_id, "order_id": order.order_id},
                )
            )

        elif self.robot.target_type == "PACKING":
            order = self.get_order_by_id(self.robot.current_order_id or "")
            self.robot.state = RobotState.PACKING
            self.robot.action_ticks_remaining = self.config.packing_duration_ticks
            if order:
                order.status = OrderStatus.PACKING
                self.robot.current_action = f"Packing {order.product_name} at packing hub"

            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.PACKING_STARTED,
                    severity=EventSeverity.INFO,
                    message="Robot arrived at packing station. Commencing package processing.",
                )
            )

        elif self.robot.target_type == "CHARGING":
            self.robot.state = RobotState.CHARGING
            self.robot.current_action = "Recharging at charging station"
            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.CHARGING_STARTED,
                    severity=EventSeverity.INFO,
                    message=f"Robot docked at charging dock. Commencing recharge (Current: {self.robot.battery:.1f}%).",
                    data={"battery": self.robot.battery},
                )
            )

        return events

    def _handle_picking(self) -> List[SimEvent]:
        """Perform shelf pick action over multiple ticks."""
        events: List[SimEvent] = []
        self.robot.action_ticks_remaining -= 1

        if self.robot.action_ticks_remaining <= 0:
            order = self.get_order_by_id(self.robot.current_order_id or "")
            if not order:
                self.robot.state = RobotState.IDLE
                return events

            shelf = self.warehouse_map.get_shelf_by_id(order.shelf_id)
            if shelf and shelf.stock >= order.quantity:
                # Deduct inventory stock
                shelf.stock -= order.quantity
            else:
                order.status = OrderStatus.BLOCKED
                self.robot.state = RobotState.IDLE
                return events

            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.PICKING_COMPLETED,
                    severity=EventSeverity.SUCCESS,
                    message=f"Successfully picked {order.product_name} from {shelf.shelf_id}. Remaining stock: {shelf.stock}.",
                    data={"shelf_id": shelf.shelf_id, "stock": shelf.stock},
                )
            )

            # Plan route to packing station
            packing_pos = self.warehouse_map.packing_station
            route = find_path(self.warehouse_map, self.robot.pos, packing_pos)

            if route and len(route) >= 1:
                self.robot.planned_route = route[1:]
                self.robot.target_pos = packing_pos
                self.robot.target_type = "PACKING"
                self.robot.state = RobotState.RETURNING
                order.status = OrderStatus.RETURNING
                self.robot.current_action = f"Returning to packing station with {order.product_name}"

                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.RETURNING_TO_PACKING,
                        severity=EventSeverity.INFO,
                        message=f"Transporting item to packing station ({len(route) - 1} steps).",
                    )
                )
            else:
                self.robot.state = RobotState.BLOCKED
                order.status = OrderStatus.BLOCKED
                self.metrics["blocked_movement_attempts"] += 1

        return events

    def _handle_packing(self) -> List[SimEvent]:
        """Perform item packing action over multiple ticks."""
        events: List[SimEvent] = []
        self.robot.action_ticks_remaining -= 1

        if self.robot.action_ticks_remaining <= 0:
            order = self.get_order_by_id(self.robot.current_order_id or "")
            if order and order.status != OrderStatus.COMPLETED:
                order.status = OrderStatus.COMPLETED
                order.completed_tick = self.tick
                order.completion_time_ticks = self.tick - order.created_tick
                self.metrics["successful_deliveries"] += 1

                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.PACKING_COMPLETED,
                        severity=EventSeverity.SUCCESS,
                        message=f"Order {order.order_id} packaged and verified at shipping dock.",
                    )
                )
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.tick,
                        event_type=EventType.ORDER_COMPLETED,
                        severity=EventSeverity.SUCCESS,
                        message=f"Delivery complete: {order.order_id} fulfilled in {order.completion_time_ticks} ticks.",
                        data={
                            "order_id": order.order_id,
                            "completion_ticks": order.completion_time_ticks,
                            "energy": order.energy_consumed,
                        },
                    )
                )

            # Clear active mission
            self.robot.current_order_id = None
            self.robot.target_pos = None
            self.robot.target_type = None

            # If battery is low after fulfillment, route to charging
            if self.robot.battery < (self.config.min_safety_reserve + 10.0):
                ev = self._dispatch_to_charge(is_emergency=False)
                if ev:
                    events.append(ev)
            else:
                self.robot.state = RobotState.IDLE
                self.robot.current_action = "Delivery complete. Ready for new order."

        return events

    def _handle_charging(self) -> List[SimEvent]:
        """Recharge robot battery at charging dock."""
        events: List[SimEvent] = []
        self.metrics["charging_time_ticks"] += 1

        recharged = self.battery_manager.charge_tick(self.robot)

        if self.battery_manager.is_fully_charged(self.robot) or self.robot.battery >= 98.0:
            self.robot.battery = self.config.battery_capacity
            self.robot.state = RobotState.IDLE
            self.robot.target_pos = None
            self.robot.target_type = None
            self.robot.current_action = "Fully charged (100%). Ready for mission."

            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.CHARGING_COMPLETED,
                    severity=EventSeverity.SUCCESS,
                    message="Robot battery fully recharged to 100%. Resuming active operations.",
                    data={"battery": self.robot.battery},
                )
            )
        else:
            self.robot.current_action = f"Charging battery ({self.robot.battery:.1f}%)"

        return events

    def _handle_blocked(self) -> List[SimEvent]:
        """Attempt to recover from blocked state."""
        events: List[SimEvent] = []
        if not self.robot.target_pos:
            self.robot.state = RobotState.IDLE
            return events

        # Attempt path recalculation
        is_shelf = self.robot.target_type == "SHELF"
        new_route = recalculate_route(
            warehouse_map=self.warehouse_map,
            current_pos=self.robot.pos,
            target_pos=self.robot.target_pos,
            is_shelf_target=is_shelf,
        )

        if new_route and len(new_route) > 1:
            self.robot.planned_route = new_route[1:]
            self.robot.state = (
                RobotState.RETURNING if self.robot.target_type == "PACKING" else RobotState.NAVIGATING
            )
            self.robot.current_action = "Obstacle cleared. Resuming transit."
            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.tick,
                    event_type=EventType.ROUTE_REPLANNED,
                    severity=EventSeverity.SUCCESS,
                    message=f"Path unblocked! Route recovered ({len(new_route) - 1} steps remaining).",
                )
            )
        else:
            self.metrics["blocked_movement_attempts"] += 1

        return events

    # ── Interactive Trigger Methods (for Part 3 API) ──

    def trigger_urgent_order(self) -> Tuple[Optional[Order], Optional[SimEvent]]:
        """Manual trigger: Dispatch an urgent order immediately."""
        order, ev = self.event_engine.trigger_urgent_order(
            current_tick=self.tick,
            warehouse_map=self.warehouse_map,
            orders=self.orders,
        )
        if ev:
            self.event_history.append(ev)
        return order, ev

    def trigger_obstacle(self) -> Optional[SimEvent]:
        """Manual trigger: Place an unexpected obstacle in the warehouse."""
        ev = self.event_engine.place_random_obstacle(
            current_tick=self.tick,
            warehouse_map=self.warehouse_map,
            robot=self.robot,
        )
        if ev:
            self.event_history.append(ev)
        return ev

    def trigger_replenish(self, shelf_id: Optional[str] = None, amount: Optional[int] = None) -> Optional[SimEvent]:
        """Manual trigger: Replenish shelf inventory."""
        ev = self.event_engine.replenish_random_shelf(
            current_tick=self.tick,
            warehouse_map=self.warehouse_map,
            shelf_id=shelf_id,
            amount=amount,
        )
        if ev:
            self.event_history.append(ev)
        return ev

    # ── Metrics and Serialization ──

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Compute live simulation metrics and KPIs."""
        total_orders = len(self.orders)
        pending = sum(1 for o in self.orders if o.status == OrderStatus.PENDING)
        in_progress = sum(
            1
            for o in self.orders
            if o.status in (OrderStatus.ASSIGNED, OrderStatus.PICKING, OrderStatus.RETURNING, OrderStatus.PACKING)
        )
        completed = sum(1 for o in self.orders if o.status == OrderStatus.COMPLETED)
        overdue = sum(1 for o in self.orders if o.is_overdue(self.tick))

        completed_orders = [o for o in self.orders if o.status == OrderStatus.COMPLETED and o.completion_time_ticks]
        avg_completion = (
            round(sum(o.completion_time_ticks for o in completed_orders) / len(completed_orders), 1)
            if completed_orders
            else 0.0
        )

        on_time_count = sum(
            1
            for o in completed_orders
            if o.deadline_tick is None or (o.completed_tick and o.completed_tick <= o.deadline_tick)
        )
        deadline_success_rate = (
            round((on_time_count / len(completed_orders)) * 100.0, 1) if completed_orders else 100.0
        )

        total_energy = sum(o.energy_consumed for o in completed_orders)
        avg_energy = (
            round(total_energy / len(completed_orders), 1) if completed_orders else 0.0
        )

        return {
            "tick": self.tick,
            "elapsed_time_seconds": self.elapsed_time_seconds,
            "total_orders": total_orders,
            "pending_orders": pending,
            "in_progress_orders": in_progress,
            "completed_orders": completed,
            "overdue_orders": overdue,
            "robot_battery": round(self.robot.battery, 1),
            "distance_travelled": self.metrics["distance_travelled"],
            "movement_count": self.metrics["movement_count"],
            "charging_time_ticks": self.metrics["charging_time_ticks"],
            "route_replanning_count": self.metrics["route_replanning_count"],
            "blocked_movement_attempts": self.metrics["blocked_movement_attempts"],
            "successful_deliveries": self.metrics["successful_deliveries"],
            "average_order_completion_ticks": avg_completion,
            "deadline_success_rate_percent": deadline_success_rate,
            "energy_consumed_per_completed_order": avg_energy,
        }
