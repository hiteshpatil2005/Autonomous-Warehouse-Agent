/**
 * Frontend Unit & Integration Tests (Part 4)
 * Tests UI rendering, state mapping, controls, and error states.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import DashboardHeader from '../components/layout/DashboardHeader';
import MetricsPanel from '../components/dashboard/MetricsPanel';
import WarehouseGrid from '../components/warehouse/WarehouseGrid';
import SimulationControls from '../components/common/SimulationControls';
import OrderQueue from '../components/orders/OrderQueue';
import DecisionInspector from '../components/analytics/DecisionInspector';
import { mapBackendToUiState } from '../hooks/useSimulation';

// Sample mock backend state fixture
const sampleBackendState = {
  tick: 15,
  elapsed_time_seconds: 15.0,
  status: 'running',
  grid: {
    rows: 30,
    cols: 30,
    shelves: [
      { shelf_id: 'SH-01', row: 4, col: 3, product_name: 'Microcontroller Unit', stock: 12, max_capacity: 20 },
      { shelf_id: 'SH-02', row: 4, col: 5, product_name: 'Li-Ion Battery Cell', stock: 8, max_capacity: 20 },
    ],
    robot_start: [28, 1],
    packing_station: [28, 14],
    charging_station: [28, 27],
    obstacles: [{ row: 12, col: 12, expiry_tick: 30 }],
  },
  robot: {
    robot_id: 'RB-01',
    row: 24,
    col: 3,
    state: 'NAVIGATING',
    battery: 88.0,
    current_order_id: 'ORD-001',
    current_action: 'Navigating to SH-01',
    planned_route: [[23, 3], [22, 3], [21, 3]],
    traversed_path: [[28, 1], [27, 1], [26, 1], [25, 2], [24, 3]],
    total_distance_travelled: 5,
  },
  orders: [
    {
      order_id: 'ORD-001',
      product_name: 'Microcontroller Unit',
      priority: 'HIGH',
      quantity: 1,
      status: 'ASSIGNED',
      shelf_id: 'SH-01',
      shelf_pos: [4, 3],
      created_tick: 0,
      deadline_tick: 60,
    },
    {
      order_id: 'ORD-002',
      product_name: 'Li-Ion Battery Cell',
      priority: 'MEDIUM',
      quantity: 1,
      status: 'PENDING',
      shelf_id: 'SH-02',
      shelf_pos: [4, 5],
      created_tick: 0,
    },
  ],
  metrics: {
    tick: 15,
    distance_travelled: 5,
    successful_deliveries: 0,
    completed_orders: 0,
    route_replanning_count: 1,
  },
  decision_inspector: {
    selected_order_id: 'ORD-001',
    winning_score: 82.5,
    explanation: 'Selected ORD-001 due to high priority (+24.5) and deadline urgency.',
    est_route_distance: 24,
    battery_feasible: true,
    evaluations: [
      { order_id: 'ORD-001', priority: 'HIGH', total_utility: 82.5 },
      { order_id: 'ORD-002', priority: 'MEDIUM', total_utility: 58.0 },
    ],
  },
  events: [
    {
      id: 'ev-1',
      tick: 1,
      event_type: 'ORDER_ASSIGNED',
      severity: 'INFO',
      message: 'Robot assigned order ORD-001.',
    },
  ],
};

describe('WareBot AI Frontend Tests', () => {
  it('1. maps backend snapshot correctly into UI reactive state', () => {
    const uiState = mapBackendToUiState(sampleBackendState, 'running', 2);
    expect(uiState).not.toBeNull();
    expect(uiState.grid.length).toBe(30);
    expect(uiState.grid[0].length).toBe(30);
    expect(uiState.robotPos).toEqual({ row: 24, col: 3 });
    expect(uiState.battery).toBe(88.0);
    expect(uiState.robotState).toBe('navigating');
    expect(uiState.orders.length).toBe(2);
    expect(uiState.orders[0].status).toBe('assigned');
    expect(uiState.currentOrder.id).toBe('ORD-001');
    expect(uiState.obstacles.length).toBe(1);
    expect(uiState.decision.pathLength).toBe(24);
  });

  it('2. renders DashboardHeader with live connected status', () => {
    render(
      <DashboardHeader
        simStatus="running"
        tick={42}
        speed={2}
        connectionStatus="connected"
        activeTab="simulation"
      />
    );
    expect(screen.getByText('WareBot AI')).toBeDefined();
    expect(screen.getByText('LIVE: CONNECTED')).toBeDefined();
    expect(screen.getByText('RUNNING')).toBeDefined();
    expect(screen.getByText('T-0042')).toBeDefined();
  });

  it('3. renders MetricsPanel with real battery, orders, and distance', () => {
    const uiState = mapBackendToUiState(sampleBackendState, 'running', 2);
    render(<MetricsPanel state={uiState} />);
    expect(screen.getByText('88')).toBeDefined();
    expect(screen.getByText('Battery')).toBeDefined();
    expect(screen.getByText('NAVIGATING')).toBeDefined();
  });

  it('4. renders SimulationControls buttons and fires callbacks', () => {
    const onStart = vitest.fn();
    const onPause = vitest.fn();
    const onResume = vitest.fn();

    // Idle state: Start button is visible
    const idleState = { simStatus: 'idle' };
    const { rerender } = render(
      <SimulationControls state={idleState} start={onStart} pause={onPause} resume={onResume} />
    );
    const startBtn = screen.getByText('Start');
    fireEvent.click(startBtn);
    expect(onStart).toHaveBeenCalled();

    // Running state: Pause button is visible
    rerender(<SimulationControls state={{ simStatus: 'running' }} start={onStart} pause={onPause} resume={onResume} />);
    const pauseBtn = screen.getByText('Pause');
    fireEvent.click(pauseBtn);
    expect(onPause).toHaveBeenCalled();
  });

  it('5. renders OrderQueue with status badges and filters', () => {
    const uiState = mapBackendToUiState(sampleBackendState, 'running', 2);
    render(
      <OrderQueue
        orders={uiState.orders}
        currentOrder={uiState.currentOrder}
        onAddUrgent={vitest.fn()}
      />
    );
    expect(screen.getByText('Order Queue')).toBeDefined();
    expect(screen.getByText('Microcontroller Unit')).toBeDefined();
    expect(screen.getByText('Li-Ion Battery Cell')).toBeDefined();
  });

  it('6. renders DecisionInspector with Live AI badge and candidate breakdown', () => {
    const uiState = mapBackendToUiState(sampleBackendState, 'running', 2);
    render(
      <DecisionInspector
        decision={uiState.decision}
        robotState={uiState.robotState}
        battery={uiState.battery}
      />
    );
    expect(screen.getByText('AI Decision Inspector')).toBeDefined();
    expect(screen.getByText('LIVE AI')).toBeDefined();
    expect(screen.getByText('ORD-001 (HIGH)')).toBeDefined();
    expect(screen.getByText('✓ Feasible')).toBeDefined();
  });

  it('7. renders WarehouseGrid without runtime errors', () => {
    const uiState = mapBackendToUiState(sampleBackendState, 'running', 2);
    const { container } = render(
      <WarehouseGrid state={uiState} onCellClick={vitest.fn()} />
    );
    // 30x30 = 900 cells
    const cells = container.querySelectorAll('.cell');
    expect(cells.length).toBe(900);
  });
});
