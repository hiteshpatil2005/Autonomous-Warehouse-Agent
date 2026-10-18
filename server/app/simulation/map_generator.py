"""
WareBot AI — Warehouse Map Generator and Connectivity Validator
"""

import random
from collections import deque
from typing import List, Optional, Set, Tuple

from app.core.config import SimulationConfig, default_config
from app.models.warehouse import Shelf, WarehouseMap

# Realistic warehouse catalogue
WAREHOUSE_PRODUCTS = [
    {"id": "PRD-001", "name": "Microcontroller Unit", "category": "Electronics"},
    {"id": "PRD-002", "name": "Li-Ion Battery Cell", "category": "Power"},
    {"id": "PRD-003", "name": "Stepper Motor 12V", "category": "Robotics"},
    {"id": "PRD-004", "name": "Ultrasonic Distance Sensor", "category": "Sensors"},
    {"id": "PRD-005", "name": "Optical Camera Module", "category": "Vision"},
    {"id": "PRD-006", "name": "Aluminum Extrusion Bar", "category": "Hardware"},
    {"id": "PRD-007", "name": "Motor Driver Shield", "category": "Electronics"},
    {"id": "PRD-008", "name": "LiDAR Range Finder", "category": "Sensors"},
    {"id": "PRD-009", "name": "Digital Servo Pro", "category": "Robotics"},
    {"id": "PRD-010", "name": "Industrial Terminal Block", "category": "Hardware"},
]

# Standard structured grid rows and columns for clean warehouse aisles
STRUCTURED_ROW_BANDS = [4, 9, 14, 19, 24]
STRUCTURED_COL_SLOTS = [3, 5, 8, 10, 13, 15, 18, 20, 23, 26]


def validate_map_integrity(warehouse_map: WarehouseMap) -> Tuple[bool, List[str]]:
    """
    Validate that:
    1. Grid dimensions match 30x30.
    2. Exactly 50 shelves exist.
    3. Robot start, packing station, and charging station are in bounds and distinct.
    4. No shelves overlap robot start or stations.
    """
    errors: List[str] = []

    if warehouse_map.rows != 30 or warehouse_map.cols != 30:
        errors.append(f"Invalid grid dimensions: {warehouse_map.rows}x{warehouse_map.cols}")

    if len(warehouse_map.shelves) != 50:
        errors.append(f"Expected 50 shelves, found {len(warehouse_map.shelves)}")

    stations = [
        warehouse_map.robot_start,
        warehouse_map.packing_station,
        warehouse_map.charging_station,
    ]
    if len(set(stations)) != 3:
        errors.append(f"Robot and stations do not occupy distinct cells: {stations}")

    for r, c in stations:
        if not (0 <= r < warehouse_map.rows and 0 <= c < warehouse_map.cols):
            errors.append(f"Station coordinate out of bounds: ({r}, {c})")

    shelf_positions = {s.pos for s in warehouse_map.shelves}
    if len(shelf_positions) != 50:
        errors.append("Duplicate shelf coordinates detected")

    station_overlaps = shelf_positions.intersection(set(stations))
    if station_overlaps:
        errors.append(f"Shelves overlap stations: {station_overlaps}")

    return len(errors) == 0, errors


def validate_connectivity(warehouse_map: WarehouseMap) -> Tuple[bool, str]:
    """
    Flood-fill (BFS) from robot start through walkable cells to ensure:
    - Packing station is reachable.
    - Charging station is reachable.
    - Every shelf has at least one adjacent walkable cell reachable from robot.
    """
    start = warehouse_map.robot_start
    if not warehouse_map.is_walkable(start[0], start[1]):
        return False, "Robot start cell is impassable"

    visited: Set[Tuple[int, int]] = set()
    queue: deque = deque([start])
    visited.add(start)

    while queue:
        r, c = queue.popleft()
        for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
            if (nr, nc) not in visited and warehouse_map.is_walkable(nr, nc):
                visited.add((nr, nc))
                queue.append((nr, nc))

    if warehouse_map.packing_station not in visited:
        return False, f"Packing station at {warehouse_map.packing_station} is unreachable"

    if warehouse_map.charging_station not in visited:
        return False, f"Charging station at {warehouse_map.charging_station} is unreachable"

    # Verify access to all shelves
    for shelf in warehouse_map.shelves:
        adjacents = [
            (shelf.row - 1, shelf.col),
            (shelf.row + 1, shelf.col),
            (shelf.row, shelf.col - 1),
            (shelf.row, shelf.col + 1),
        ]
        has_reachable_access = any(pos in visited and warehouse_map.is_walkable(pos[0], pos[1]) for pos in adjacents)
        if not has_reachable_access:
            return False, f"Shelf {shelf.shelf_id} at {shelf.pos} has no reachable access point"

    return True, "Fully connected"


def generate_warehouse_map(
    seed: Optional[int] = None,
    config: Optional[SimulationConfig] = None,
    random_layout: bool = False,
) -> WarehouseMap:
    """
    Generate a 30x30 warehouse map with exactly 50 shelves and validated connectivity.
    Supports fixed seeds for reproducible scenarios and random layouts with automatic repair.
    """
    cfg = config or default_config
    rng = random.Random(seed)

    max_attempts = 100
    for attempt in range(max_attempts):
        shelves: List[Shelf] = []
        forbidden_cells = {
            cfg.robot_start_pos,
            cfg.packing_station_pos,
            cfg.charging_station_pos,
        }

        if not random_layout:
            # Structured deterministic layout with wide aisles (5 rows x 10 cols = 50 shelves)
            count = 1
            for r in STRUCTURED_ROW_BANDS:
                for c in STRUCTURED_COL_SLOTS:
                    pos = (r, c)
                    if pos in forbidden_cells:
                        continue
                    prod = WAREHOUSE_PRODUCTS[(count - 1) % len(WAREHOUSE_PRODUCTS)]
                    stock = rng.randint(6, 18)
                    shelves.append(
                        Shelf(
                            shelf_id=f"SH-{count:02d}",
                            row=r,
                            col=c,
                            product_id=prod["id"],
                            product_name=prod["name"],
                            stock=stock,
                            max_capacity=20,
                        )
                    )
                    count += 1
        else:
            # Randomized placement with connectivity validation and repair
            possible_coords = [
                (r, c)
                for r in range(2, cfg.grid_rows - 3)
                for c in range(2, cfg.grid_cols - 2)
                if (r, c) not in forbidden_cells
            ]
            chosen_coords = rng.sample(possible_coords, cfg.num_shelves)
            for idx, (r, c) in enumerate(chosen_coords, start=1):
                prod = WAREHOUSE_PRODUCTS[(idx - 1) % len(WAREHOUSE_PRODUCTS)]
                stock = rng.randint(6, 18)
                shelves.append(
                    Shelf(
                        shelf_id=f"SH-{idx:02d}",
                        row=r,
                        col=c,
                        product_id=prod["id"],
                        product_name=prod["name"],
                        stock=stock,
                        max_capacity=20,
                    )
                )

        w_map = WarehouseMap(
            rows=cfg.grid_rows,
            cols=cfg.grid_cols,
            shelves=shelves,
            robot_start=cfg.robot_start_pos,
            packing_station=cfg.packing_station_pos,
            charging_station=cfg.charging_station_pos,
            obstacles={},
        )

        valid_integrity, errors = validate_map_integrity(w_map)
        if not valid_integrity:
            continue

        valid_connected, reason = validate_connectivity(w_map)
        if valid_connected:
            return w_map

    # Fallback to guaranteed structured layout if random failed
    return generate_warehouse_map(seed=seed, config=config, random_layout=False)
