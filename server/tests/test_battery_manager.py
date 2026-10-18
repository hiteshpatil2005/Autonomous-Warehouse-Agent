"""
Tests for Battery Management Logic (Requirements 8, 9, 15).
"""

from app.core.config import SimulationConfig
from app.models.robot import Robot
from app.simulation.battery_manager import BatteryManager


def test_movement_consumes_correct_battery(default_cfg):
    """Requirement 8: Every movement consumes the correct battery amount."""
    bm = BatteryManager(default_cfg)
    robot = Robot(row=10, col=10, battery=100.0)

    # 1 step movement
    used = bm.consume_movement(robot, steps=1)
    assert used == default_cfg.movement_cost
    assert robot.battery == 99.0

    # 5 steps movement
    bm.consume_movement(robot, steps=5)
    assert robot.battery == 94.0


def test_battery_remains_within_valid_limits(default_cfg):
    """Requirement 9: Battery remains within valid limits [0.0, capacity]."""
    bm = BatteryManager(default_cfg)
    robot = Robot(row=10, col=10, battery=5.0)

    # Excessive consumption clamps at 0.0
    bm.consume_movement(robot, steps=20)
    assert robot.battery == 0.0
    assert robot.battery >= 0.0

    # Overcharging clamps at battery_capacity (100.0)
    robot.battery = 98.0
    bm.charge_tick(robot)  # default rate is 7.0
    assert robot.battery == default_cfg.battery_capacity
    assert robot.battery <= default_cfg.battery_capacity


def test_charging_increases_battery_correctly(default_cfg):
    """Requirement 15: Charging increases battery correctly."""
    bm = BatteryManager(default_cfg)
    robot = Robot(row=28, col=27, battery=40.0)

    gained = bm.charge_tick(robot)
    assert gained == default_cfg.charging_rate
    assert robot.battery == 40.0 + default_cfg.charging_rate

    # Second tick
    gained2 = bm.charge_tick(robot)
    assert gained2 == default_cfg.charging_rate
    assert robot.battery == 40.0 + (2 * default_cfg.charging_rate)
