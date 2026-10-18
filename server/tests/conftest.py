"""
Pytest configuration and shared fixtures for WareBot AI tests.
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure server directory is on sys.path so 'app' imports work seamlessly
server_dir = Path(__file__).resolve().parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from app.core.config import SimulationConfig
from app.simulation.engine import WarehouseEngine
from app.simulation.map_generator import generate_warehouse_map


@pytest.fixture
def default_cfg():
    return SimulationConfig()


@pytest.fixture
def seeded_map(default_cfg):
    return generate_warehouse_map(seed=42, config=default_cfg)


@pytest.fixture
def seeded_engine(default_cfg):
    return WarehouseEngine(seed=42, config=default_cfg)
