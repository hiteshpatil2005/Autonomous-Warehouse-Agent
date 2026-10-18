"""
WareBot AI — Authoritative Simulation Manager & Execution Controller
Coordinates simulation state, concurrency locks, background execution loop,
and WebSocket state broadcasts.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import SimulationConfig, default_config
from app.models.events import EventSeverity, EventType, SimEvent
from app.services.connection_manager import ws_manager
from app.services.serialization import serialize_simulation_state
from app.simulation.engine import WarehouseEngine

logger = logging.getLogger("warebot.simulation_manager")


class SimulationManager:
    """
    Authoritative controller for warehouse simulation lifecycle.
    Prevents duplicate loops, manages async execution, and synchronizes state.
    """

    SPEED_MAP = {
        1: 2.0,   # Slow: 2 ticks / second
        2: 5.0,   # Normal: 5 ticks / second
        3: 8.0,   # Fast: 8 ticks / second
        4: 12.0,  # Rapid: 12 ticks / second
        5: 20.0,  # Max: 20 ticks / second
    }

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or default_config
        self.simulation_id = f"sim-{uuid.uuid4().hex[:8]}"
        self.status = "idle"  # "idle" | "running" | "paused" | "completed"
        self.engine = WarehouseEngine(seed=42, config=self.config)
        self.speed_level = 2
        self.tick_rate_hz = self.SPEED_MAP[2]

        self._lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None
        self._stop_requested = False

    # ── State Accessors ─────────────────────────────────────────────────────

    def get_full_state(self) -> Dict[str, Any]:
        """Produce full JSON-serializable state snapshot."""
        state = serialize_simulation_state(self.engine)
        state["status"] = self.status
        state["simulation_id"] = self.simulation_id
        state["speed"] = self.speed_level
        return state

    def get_status_summary(self) -> Dict[str, Any]:
        """Produce status summary."""
        return {
            "status": self.status,
            "simulation_id": self.simulation_id,
            "tick": self.engine.tick,
            "elapsed_time_seconds": self.engine.elapsed_time_seconds,
            "is_running": self.status == "running",
            "speed": self.speed_level,
        }

    def get_orders(self) -> List[Dict[str, Any]]:
        full = self.get_full_state()
        return full.get("orders", [])

    def get_metrics(self) -> Dict[str, Any]:
        return self.engine.get_metrics_snapshot()

    def get_events(self) -> List[Dict[str, Any]]:
        full = self.get_full_state()
        return full.get("events", [])

    def get_decision(self) -> Optional[Dict[str, Any]]:
        full = self.get_full_state()
        return full.get("decision_inspector")

    # ── Broadcast Helpers ───────────────────────────────────────────────────

    async def _broadcast_state(self, message_type: str = "simulation_state", extra_events: Optional[List[SimEvent]] = None):
        """Broadcast state updates to all connected WebSockets."""
        state = self.get_full_state()
        payload = {
            "type": message_type,
            "simulation_id": self.simulation_id,
            "data": state,
            "events": [e.model_dump() for e in (extra_events or [])],
        }
        await ws_manager.broadcast(payload)

    async def _broadcast_status(self):
        """Broadcast status changes (running, paused, idle, etc.)."""
        payload = {
            "type": "simulation_status",
            "simulation_id": self.simulation_id,
            "status": self.status,
            "tick": self.engine.tick,
            "data": self.get_status_summary(),
        }
        await ws_manager.broadcast(payload)

    # ── Lifecycle Controls ──────────────────────────────────────────────────

    async def create_simulation(
        self,
        seed: Optional[int] = None,
        random_layout: bool = False,
    ) -> Dict[str, Any]:
        """Create a fresh warehouse simulation scenario."""
        async with self._lock:
            await self._stop_background_task()
            self.simulation_id = f"sim-{uuid.uuid4().hex[:8]}"
            self.status = "idle"
            self.engine = WarehouseEngine(
                seed=seed,
                config=self.config,
                random_layout=random_layout,
            )

        await self._broadcast_state("simulation_state")
        return self.get_full_state()

    async def start(self) -> Dict[str, Any]:
        """Start or resume continuous simulation execution."""
        async with self._lock:
            if self.status == "running":
                # Already running - prevent duplicate background loops
                logger.info("Start requested while already running. Ignoring duplicate start.")
                return self.get_status_summary()

            self.status = "running"
            self._stop_requested = False
            self._background_task = asyncio.create_task(self._execution_loop())

        await self._broadcast_status()
        return self.get_status_summary()

    async def pause(self) -> Dict[str, Any]:
        """Pause continuous execution without losing state."""
        async with self._lock:
            if self.status != "running":
                return self.get_status_summary()

            self.status = "paused"
            await self._stop_background_task()

        await self._broadcast_status()
        return self.get_status_summary()

    async def resume(self) -> Dict[str, Any]:
        """Resume execution from paused or idle state."""
        return await self.start()

    async def reset(self, new_seed: Optional[int] = None) -> Dict[str, Any]:
        """Reset simulation engine state completely."""
        async with self._lock:
            await self._stop_background_task()
            self.status = "idle"
            self.engine.reset(new_seed=new_seed)

        await self._broadcast_state("simulation_state")
        return self.get_full_state()

    async def step(self, steps: int = 1) -> Dict[str, Any]:
        """
        Advance the simulation by exactly `steps` ticks while paused or idle.
        Refuses stepping if the simulation is actively running.
        """
        async with self._lock:
            if self.status == "running":
                raise ValueError("Cannot perform manual step while simulation is actively running. Pause first.")

            all_events: List[SimEvent] = []
            for _ in range(steps):
                events = self.engine.step()
                all_events.extend(events)

        await self._broadcast_state("simulation_state", extra_events=all_events)
        return self.get_full_state()

    def set_speed(self, speed_level: int):
        """Update execution speed level (1 to 5)."""
        if speed_level in self.SPEED_MAP:
            self.speed_level = speed_level
            self.tick_rate_hz = self.SPEED_MAP[speed_level]

    # ── Background Execution Loop ───────────────────────────────────────────

    async def _execution_loop(self):
        """Asynchronous execution loop advancing discrete ticks at configured rate."""
        logger.info(f"Simulation execution loop started for {self.simulation_id}")
        try:
            while self.status == "running" and not self._stop_requested:
                loop_start = asyncio.get_event_loop().time()

                async with self._lock:
                    tick_events = self.engine.step()
                    # Check if all orders completed and robot is idle
                    if self.engine.robot.state.value == "IDLE":
                        pending = [o for o in self.engine.orders if o.status.value in ("PENDING", "ASSIGNED", "PICKING", "RETURNING", "PACKING")]
                        if not pending:
                            logger.info("All warehouse orders fulfilled.")

                # Broadcast tick state
                await self._broadcast_state("simulation_state", extra_events=tick_events)

                # Maintain target frequency
                elapsed = asyncio.get_event_loop().time() - loop_start
                sleep_duration = max(0.01, (1.0 / self.tick_rate_hz) - elapsed)
                await asyncio.sleep(sleep_duration)

        except asyncio.CancelledError:
            logger.debug(f"Execution loop cancelled for {self.simulation_id}")
        except Exception as exc:
            logger.error(f"Error in execution loop: {exc}", exc_info=True)
            self.status = "paused"
            await ws_manager.broadcast({
                "type": "error",
                "simulation_id": self.simulation_id,
                "message": f"Execution loop encountered an error: {str(exc)}",
            })
        finally:
            logger.info(f"Execution loop ended for {self.simulation_id}")

    async def _stop_background_task(self):
        """Safely cancel and await background loop."""
        self._stop_requested = True
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        self._background_task = None

    # ── Dynamic Scenario Triggers ───────────────────────────────────────────

    async def add_obstacle(
        self,
        row: Optional[int] = None,
        col: Optional[int] = None,
        duration_ticks: int = 15,
    ) -> Dict[str, Any]:
        """
        Add a temporary obstacle. Validates target cell:
        Cannot be placed on robot, packing station, charging station, or shelves.
        """
        async with self._lock:
            w_map = self.engine.warehouse_map
            robot = self.engine.robot

            forbidden = {
                robot.pos,
                w_map.packing_station,
                w_map.charging_station,
            }

            if row is not None and col is not None:
                # Validate coordinates
                if not (0 <= row < w_map.rows and 0 <= col < w_map.cols):
                    raise ValueError(f"Obstacle coordinate ({row}, {col}) is out of grid bounds.")

                target_coord = (row, col)
                if target_coord in forbidden:
                    raise ValueError(f"Cannot place obstacle on station or robot cell at {target_coord}.")

                if w_map.is_shelf(row, col):
                    raise ValueError(f"Cannot place obstacle on shelf at {target_coord}.")

                # Toggle: if already an obstacle, remove it
                key = f"{row},{col}"
                if key in w_map.obstacles:
                    del w_map.obstacles[key]
                    event = SimEvent(
                        id=str(uuid.uuid4())[:8],
                        tick=self.engine.tick,
                        event_type=EventType.OBSTACLE_CLEARED,
                        severity=EventSeverity.INFO,
                        message=f"Obstacle cleared at ({row}, {col}).",
                        data={"coord": [row, col], "action": "cleared"},
                    )
                    self.engine.event_history.append(event)
                    # If robot was blocked, see if route can resume
                    if self.engine.robot.state == RobotState.BLOCKED and self.engine.robot.target_pos:
                        is_shelf = self.engine.robot.target_type == "SHELF"
                        new_route = recalculate_route(
                            warehouse_map=w_map,
                            current_pos=self.engine.robot.pos,
                            target_pos=self.engine.robot.target_pos,
                            is_shelf_target=is_shelf,
                        )
                        if new_route and len(new_route) > 1:
                            self.engine.robot.planned_route = new_route[1:]
                            self.engine.robot.state = RobotState.NAVIGATING
                            self.engine.robot.current_action = f"Obstacle cleared! Resuming path."
                    await self._broadcast_state("simulation_state", extra_events=[event])
                    return {
                        "status": "success",
                        "message": f"Obstacle removed at ({row}, {col}).",
                        "data": {"row": row, "col": col, "action": "removed"},
                    }

                # Add to map (default to 120 ticks so obstacle remains visible for testing)
                active_duration = max(duration_ticks, 120) if duration_ticks == 15 else duration_ticks
                w_map.obstacles[key] = self.engine.tick + active_duration

                event = SimEvent(
                    id=str(uuid.uuid4())[:8],
                    tick=self.engine.tick,
                    event_type=EventType.OBSTACLE_DETECTED,
                    severity=EventSeverity.WARNING,
                    message=f"Obstacle placed at ({row}, {col}) for {active_duration} ticks.",
                    data={"coord": [row, col], "duration": active_duration},
                )
                self.engine.event_history.append(event)

                # Check if robot's planned route is obstructed by this new obstacle
                extra_events = [event]
                if self.engine.robot.planned_route and (row, col) in self.engine.robot.planned_route:
                    is_shelf = self.engine.robot.target_type == "SHELF"
                    recalculated = recalculate_route(
                        warehouse_map=w_map,
                        current_pos=self.engine.robot.pos,
                        target_pos=self.engine.robot.target_pos or self.engine.robot.pos,
                        is_shelf_target=is_shelf,
                    )
                    if recalculated and len(recalculated) > 1:
                        self.engine.robot.planned_route = recalculated[1:]
                        self.engine.metrics["route_replanning_count"] += 1
                        replan_ev = SimEvent(
                            id=str(uuid.uuid4())[:8],
                            tick=self.engine.tick,
                            event_type=EventType.ROUTE_REPLANNED,
                            severity=EventSeverity.WARNING,
                            message=f"Obstacle detected at ({row}, {col}) on route! Path replanned ({len(recalculated) - 1} steps).",
                            data={"obstacle": [row, col], "steps": len(recalculated) - 1},
                        )
                        self.engine.event_history.append(replan_ev)
                        extra_events.append(replan_ev)
                    else:
                        self.engine.robot.state = RobotState.BLOCKED
                        self.engine.metrics["blocked_movement_attempts"] += 1
                        self.engine.robot.current_action = f"Blocked by obstacle at ({row}, {col})"
                        blocked_ev = SimEvent(
                            id=str(uuid.uuid4())[:8],
                            tick=self.engine.tick,
                            event_type=EventType.ROBOT_BLOCKED,
                            severity=EventSeverity.ERROR,
                            message=f"Route blocked by obstacle at ({row}, {col})! No alternative path found.",
                            data={"obstacle": [row, col]},
                        )
                        self.engine.event_history.append(blocked_ev)
                        extra_events.append(blocked_ev)
            else:
                # Random placement using event engine
                event = self.engine.trigger_obstacle()
                if not event:
                    raise RuntimeError("Unable to find a valid location for random obstacle.")
                extra_events = [event]

        await self._broadcast_state("simulation_state", extra_events=extra_events)
        return {
            "status": "success",
            "message": event.message,
            "data": event.data,
        }

    async def add_urgent_order(self) -> Dict[str, Any]:
        """Inject an urgent priority order into the warehouse queue."""
        async with self._lock:
            order, event = self.engine.trigger_urgent_order()
            if not order:
                raise RuntimeError("Cannot create urgent order: all warehouse shelves are empty.")

        await self._broadcast_state("simulation_state", extra_events=[event] if event else [])
        return {
            "status": "success",
            "message": f"Urgent order {order.order_id} created for {order.product_name}.",
            "order_id": order.order_id,
        }

    async def replenish_inventory(
        self,
        shelf_id: Optional[str] = None,
        amount: int = 5,
    ) -> Dict[str, Any]:
        """Replenish stock for a specific or random shelf."""
        async with self._lock:
            event = self.engine.trigger_replenish(shelf_id=shelf_id, amount=amount)
            if not event:
                raise RuntimeError("Failed to replenish stock.")

        await self._broadcast_state("simulation_state", extra_events=[event])
        return {
            "status": "success",
            "message": event.message,
            "data": event.data,
        }


# Global authoritative simulation manager singleton
sim_manager = SimulationManager()
