"""
WareBot AI — Dynamic Event Engine
Generates stochastic warehouse events and handles manual trigger actions.
"""

import random
import uuid
from typing import List, Optional, Tuple

from app.core.config import SimulationConfig, default_config
from app.models.events import EventSeverity, EventType, SimEvent
from app.models.order import Order, OrderStatus, Priority
from app.models.robot import Robot
from app.models.warehouse import Shelf, WarehouseMap
from app.simulation.map_generator import WAREHOUSE_PRODUCTS


class EventEngine:
    """
    Simulates dynamic environmental conditions:
    - New order arrival (standard & urgent)
    - Temporary obstacle creation and expiration
    - Stock replenishments
    - Deadline warnings
    """

    def __init__(self, config: Optional[SimulationConfig] = None, seed: Optional[int] = None):
        self.config = config or default_config
        self.rng = random.Random(seed)
        self._order_counter = 11  # Starts after initial 10 orders

    def set_seed(self, seed: Optional[int]):
        self.rng = random.Random(seed)

    def process_tick(
        self,
        current_tick: int,
        warehouse_map: WarehouseMap,
        robot: Robot,
        orders: List[Order],
    ) -> List[SimEvent]:
        """
        Advance dynamic event state for one tick:
        1. Expire outdated obstacles.
        2. Check for deadline violations.
        3. Stochastically generate new orders, obstacles, or replenishments.
        """
        events: List[SimEvent] = []

        # 1. Expire temporary obstacles
        expired_keys = [
            k for k, exp_tick in warehouse_map.obstacles.items() if current_tick >= exp_tick
        ]
        for key in expired_keys:
            del warehouse_map.obstacles[key]
            r, c = map(int, key.split(","))
            events.append(
                SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=current_tick,
                    event_type=EventType.OBSTACLE_EXPIRED,
                    severity=EventSeverity.INFO,
                    message=f"Temporary obstacle at ({r}, {c}) has cleared.",
                    data={"coord": (r, c)},
                )
            )

        # 2. Check for overdue orders
        for order in orders:
            if (
                order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
                and order.deadline_tick is not None
                and current_tick == order.deadline_tick + 1
            ):
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=current_tick,
                        event_type=EventType.DEADLINE_MISSED,
                        severity=EventSeverity.WARNING,
                        message=f"Order {order.order_id} missed its delivery deadline!",
                        data={"order_id": order.order_id},
                    )
                )

        # 3. Dynamic order arrival (regular)
        if self.rng.random() < self.config.order_arrival_prob:
            new_order = self._create_random_order(
                current_tick=current_tick,
                warehouse_map=warehouse_map,
                is_urgent=False,
            )
            if new_order:
                orders.append(new_order)
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=current_tick,
                        event_type=EventType.ORDER_CREATED,
                        severity=EventSeverity.INFO,
                        message=f"New order {new_order.order_id} received: {new_order.product_name} (Priority: {new_order.priority.value}).",
                        data={"order_id": new_order.order_id},
                    )
                )

        # 4. Dynamic urgent order arrival
        if self.rng.random() < self.config.urgent_order_prob:
            urgent_order = self._create_random_order(
                current_tick=current_tick,
                warehouse_map=warehouse_map,
                is_urgent=True,
            )
            if urgent_order:
                orders.append(urgent_order)
                events.append(
                    SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=current_tick,
                        event_type=EventType.ORDER_CREATED,
                        severity=EventSeverity.WARNING,
                        message=f"URGENT order {urgent_order.order_id} incoming! Immediate dispatch requested.",
                        data={"order_id": urgent_order.order_id, "priority": "URGENT"},
                    )
                )

        # 5. Stochastic obstacle placement
        if self.rng.random() < self.config.obstacle_prob:
            obs_event = self.place_random_obstacle(current_tick, warehouse_map, robot)
            if obs_event:
                events.append(obs_event)

        # 6. Stochastic inventory replenishment
        if self.rng.random() < self.config.replenish_prob:
            rep_event = self.replenish_random_shelf(current_tick, warehouse_map)
            if rep_event:
                events.append(rep_event)

        return events

    def _create_random_order(
        self,
        current_tick: int,
        warehouse_map: WarehouseMap,
        is_urgent: bool = False,
    ) -> Optional[Order]:
        """Generate a valid order mapped to an existing shelf with available stock."""
        eligible_shelves = [s for s in warehouse_map.shelves if s.stock > 0]
        if not eligible_shelves:
            return None

        shelf = self.rng.choice(eligible_shelves)
        order_num = self._order_counter
        self._order_counter += 1

        order_id = f"ORD-{order_num:03d}"
        if is_urgent:
            priority = Priority.URGENT
            deadline = current_tick + self.rng.randint(25, 45)
        else:
            priority = self.rng.choice([Priority.LOW, Priority.MEDIUM, Priority.HIGH])
            deadline = current_tick + self.rng.randint(50, 110) if self.rng.random() > 0.3 else None

        return Order(
            order_id=order_id,
            product_id=shelf.product_id,
            product_name=shelf.product_name,
            quantity=1,
            priority=priority,
            shelf_id=shelf.shelf_id,
            shelf_pos=shelf.pos,
            created_tick=current_tick,
            deadline_tick=deadline,
            status=OrderStatus.PENDING,
        )

    def trigger_urgent_order(
        self,
        current_tick: int,
        warehouse_map: WarehouseMap,
        orders: List[Order],
    ) -> Tuple[Optional[Order], Optional[SimEvent]]:
        """Manual API trigger for urgent order dispatch."""
        order = self._create_random_order(current_tick, warehouse_map, is_urgent=True)
        if not order:
            return None, None

        orders.append(order)
        event = SimEvent(
            id=str(uuid.uuid4())[:8],
            tick=current_tick,
            event_type=EventType.ORDER_CREATED,
            severity=EventSeverity.WARNING,
            message=f"Manual flash dispatch: Urgent order {order.order_id} ({order.product_name}) placed!",
            data={"order_id": order.order_id, "priority": "URGENT"},
        )
        return order, event

    def place_random_obstacle(
        self,
        current_tick: int,
        warehouse_map: WarehouseMap,
        robot: Robot,
    ) -> Optional[SimEvent]:
        """
        Spawn a temporary obstacle on a walkable cell.
        Guarantees obstacle is never placed on the robot, packing station, or charging station.
        """
        forbidden = {
            robot.pos,
            warehouse_map.packing_station,
            warehouse_map.charging_station,
        }

        # Check existing planned route of robot to create meaningful challenge if possible
        candidate_coords: List[Tuple[int, int]] = []
        if robot.planned_route and len(robot.planned_route) > 2:
            # Maybe place near upcoming path
            for step in robot.planned_route[1:-1]:
                if step not in forbidden and warehouse_map.is_walkable(step[0], step[1]):
                    candidate_coords.append(step)

        if not candidate_coords or self.rng.random() > 0.5:
            # Pick a random floor aisle
            candidates = [
                (r, c)
                for r in range(1, warehouse_map.rows - 1)
                for c in range(1, warehouse_map.cols - 1)
                if (r, c) not in forbidden and warehouse_map.is_walkable(r, c)
            ]
            if candidates:
                candidate_coords = [self.rng.choice(candidates)]

        if not candidate_coords:
            return None

        chosen = self.rng.choice(candidate_coords)
        r, c = chosen
        key = f"{r},{c}"
        duration = self.config.obstacle_duration_ticks
        warehouse_map.obstacles[key] = current_tick + duration

        return SimEvent(
            id=str(uuid.uuid4())[:8],
            tick=current_tick,
            event_type=EventType.OBSTACLE_DETECTED,
            severity=EventSeverity.WARNING,
            message=f"Temporary obstacle detected at ({r}, {c})! Clearance in ~{duration} ticks.",
            data={"coord": (r, c), "duration": duration},
        )

    def replenish_random_shelf(
        self,
        current_tick: int,
        warehouse_map: WarehouseMap,
        shelf_id: Optional[str] = None,
        amount: Optional[int] = None,
    ) -> Optional[SimEvent]:
        """Replenish stock for a shelf."""
        replenish_qty = amount or self.config.replenish_amount

        target_shelf: Optional[Shelf] = None
        if shelf_id:
            target_shelf = warehouse_map.get_shelf_by_id(shelf_id)
        else:
            # Choose a low stock shelf first
            low_stock_shelves = [s for s in warehouse_map.shelves if s.stock < 8]
            if low_stock_shelves:
                target_shelf = self.rng.choice(low_stock_shelves)
            elif warehouse_map.shelves:
                target_shelf = self.rng.choice(warehouse_map.shelves)

        if not target_shelf:
            return None

        old_stock = target_shelf.stock
        target_shelf.stock = min(target_shelf.max_capacity, target_shelf.stock + replenish_qty)
        actual_added = target_shelf.stock - old_stock

        return SimEvent(
            id=str(uuid.uuid4())[:8],
            tick=current_tick,
            event_type=EventType.STOCK_REPLENISHED,
            severity=EventSeverity.SUCCESS,
            message=f"Stock replenished for {target_shelf.product_name} at {target_shelf.shelf_id} (+{actual_added} units).",
            data={
                "shelf_id": target_shelf.shelf_id,
                "product_name": target_shelf.product_name,
                "new_stock": target_shelf.stock,
            },
        )
