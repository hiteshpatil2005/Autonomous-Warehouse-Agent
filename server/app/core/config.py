"""
WareBot AI — Simulation Configuration & Settings
"""

from typing import Tuple
from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """Central configuration for warehouse simulation parameters and weights."""

    # Grid Dimensions
    grid_rows: int = Field(default=30, description="Warehouse grid row count")
    grid_cols: int = Field(default=30, description="Warehouse grid column count")
    num_shelves: int = Field(default=50, description="Exact number of shelf cells")

    # Static Stations and Spawn Positions (row, col)
    robot_start_pos: Tuple[int, int] = Field(default=(28, 1), description="Initial robot coordinate")
    packing_station_pos: Tuple[int, int] = Field(default=(28, 14), description="Packing station coordinate")
    charging_station_pos: Tuple[int, int] = Field(default=(28, 27), description="Charging station coordinate")

    # Battery Parameters
    battery_capacity: float = Field(default=100.0, description="Maximum robot battery capacity")
    initial_battery: float = Field(default=100.0, description="Starting battery level")
    movement_cost: float = Field(default=1.0, description="Battery consumption per 1 grid movement step")
    charging_rate: float = Field(default=7.0, description="Battery recharged per tick at charging station")
    min_safety_reserve: float = Field(default=15.0, description="Minimum battery buffer required for any mission")
    critical_battery_threshold: float = Field(default=20.0, description="Threshold triggering emergency return to charger")

    # Action Durations (in simulation ticks)
    picking_duration_ticks: int = Field(default=2, description="Ticks required to pick item at shelf")
    packing_duration_ticks: int = Field(default=2, description="Ticks required to pack item at station")

    # Utility Engine Weights (must sum to ~100 for normalization)
    urgency_weight: float = Field(default=25.0, description="Weight for order priority")
    deadline_weight: float = Field(default=30.0, description="Weight for deadline urgency")
    distance_shelf_weight: float = Field(default=20.0, description="Weight for robot-to-shelf proximity")
    distance_packing_weight: float = Field(default=15.0, description="Weight for shelf-to-packing proximity")
    inventory_weight: float = Field(default=10.0, description="Weight for stock availability")

    # Dynamic Event Probabilities per Tick
    order_arrival_prob: float = Field(default=0.08, description="Probability of new regular order arriving")
    urgent_order_prob: float = Field(default=0.03, description="Probability of new urgent order arriving")
    obstacle_prob: float = Field(default=0.04, description="Probability of temporary obstacle appearing")
    obstacle_duration_ticks: int = Field(default=15, description="Duration before obstacle expires")
    replenish_prob: float = Field(default=0.03, description="Probability of stock replenishment")
    replenish_amount: int = Field(default=5, description="Items added during replenishment")

    # Initial order count
    initial_order_count: int = Field(default=10, description="Orders generated at simulation start")


# Default global settings instance
default_config = SimulationConfig()
