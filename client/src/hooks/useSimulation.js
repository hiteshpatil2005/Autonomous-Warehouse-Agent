/**
 * useSimulation — Unified Simulation State Hook for WareBot AI.
 *
 * Connects directly to the authoritative FastAPI backend via REST and WebSockets.
 * Receives live simulation state, synchronizes robot movement, order lifecycles,
 * battery levels, and AI decision inspector metrics in real time.
 *
 * If backend is unreachable, gracefully falls back to local mock mode with full UI interactivity.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { simulationApi } from '../services/simulationApi';
import { simulationSocket } from '../services/simulationSocket';
import { generateMap, validateMap } from '../data/mapGenerator';
import { generateOrders, createUrgentOrder as createMockUrgentOrder } from '../data/ordersGenerator';

// ── State Mapper from Backend Snapshot to UI Reactive Model ────────────────

export function mapBackendToUiState(backendState, currentStatus = 'idle', speed = 2) {
  if (!backendState) return null;

  const { grid: bGrid, robot: bRobot, orders: bOrders, metrics: bMetrics, decision_inspector: bDecision, events: bEvents } = backendState;

  // 1. Build 30x30 Grid
  const grid = [];
  const shelfLookup = new Map();
  (bGrid?.shelves || []).forEach(s => {
    shelfLookup.set(`${s.row},${s.col}`, s);
  });

  const packingCoord = bGrid?.packing_station || [28, 14];
  const chargingCoord = bGrid?.charging_station || [28, 27];
  const startCoord = bGrid?.robot_start || [28, 1];

  for (let r = 0; r < 30; r++) {
    const row = [];
    for (let c = 0; c < 30; c++) {
      const key = `${r},${c}`;
      if (shelfLookup.has(key)) {
        const s = shelfLookup.get(key);
        row.push({ row: r, col: c, type: 'shelf', shelfId: s.shelf_id });
      } else if (r === packingCoord[0] && c === packingCoord[1]) {
        row.push({ row: r, col: c, type: 'packing', shelfId: null });
      } else if (r === chargingCoord[0] && c === chargingCoord[1]) {
        row.push({ row: r, col: c, type: 'charging', shelfId: null });
      } else {
        row.push({ row: r, col: c, type: 'floor', shelfId: null });
      }
    }
    grid.push(row);
  }

  // 2. Robot & Paths
  const robotPos = { row: bRobot?.row ?? 28, col: bRobot?.col ?? 1 };
  const plannedPath = (bRobot?.planned_route || []).map(p => ({ row: p[0], col: p[1] }));
  const traversedPath = (bRobot?.traversed_path || []).map(p => ({ row: p[0], col: p[1] }));
  const obstacles = (bGrid?.obstacles || []).map(o => ({ row: o.row, col: o.col }));

  // 3. Orders
  const orders = (bOrders || []).map(o => ({
    id: o.order_id,
    product: o.product_name,
    priority: o.priority,
    quantity: o.quantity,
    status: (o.status || 'pending').toLowerCase(),
    shelfId: o.shelf_id,
    shelfPos: { row: o.shelf_pos[0], col: o.shelf_pos[1] },
    targetShelfPos: { row: o.shelf_pos[0], col: o.shelf_pos[1] },
    createdTick: o.created_tick,
    deadlineTick: o.deadline_tick,
    completedTick: o.completed_tick,
    energyConsumed: o.energy_consumed,
    isOverdue: Boolean(o.is_overdue),
  }));

  const activeOrderId = bRobot?.current_order_id;
  const currentOrder = orders.find(o => o.id === activeOrderId) || null;

  // 4. Decision Inspector
  let decision = {
    goal: currentOrder ? `Deliver ${currentOrder.id} (${currentOrder.product})` : 'Awaiting order assignment',
    action: bRobot?.current_action || (bRobot?.state ? bRobot.state.toUpperCase() : 'STANDBY'),
    reason: 'Autonomous utility evaluation active.',
    candidates: [],
    pathLength: plannedPath.length,
    batteryFeasible: (bRobot?.battery ?? 100) > 15,
    lastEvent: 'System operational',
  };

  if (bDecision) {
    const rawScores = bDecision.evaluations || [];
    const maxScore = Math.max(...rawScores.map(e => e.total_utility || 1), 50.0);

    decision = {
      goal: bDecision.selected_order_id
        ? `Deliver ${bDecision.selected_order_id}`
        : (bRobot?.state === 'CHARGING' ? 'Recharging at dock' : 'Queue Idle / Searching'),
      action: bRobot?.current_action || bRobot?.state?.toUpperCase() || 'STANDBY',
      reason: bDecision.explanation || 'Evaluated pending orders against utility weights.',
      pathLength: bDecision.est_route_distance || plannedPath.length,
      batteryFeasible: bDecision.battery_feasible !== false,
      candidates: rawScores.slice(0, 5).map(e => ({
        action: `${e.order_id} (${e.priority})`,
        score: Math.max(0.05, Math.min(1.0, (e.total_utility || 0) / maxScore)),
      })),
      lastEvent: bEvents?.length ? bEvents[bEvents.length - 1].message : 'Decision computed',
    };
  }

  // 5. Activity Log
  const activityLog = (bEvents || [])
    .slice()
    .reverse()
    .slice(0, 100)
    .map(ev => {
      let category = 'system';
      const sev = (ev.severity || '').toUpperCase();
      const type = (ev.event_type || '').toUpperCase();
      if (sev === 'WARNING' || sev === 'ERROR') category = 'warning';
      else if (type.includes('ORDER')) category = 'orders';
      else if (type.includes('ROBOT') || type.includes('PICK') || type.includes('PACK') || type.includes('CHARG')) category = 'robot';

      return {
        id: ev.id,
        time: `T-${String(ev.tick).padStart(4, '0')}`,
        tick: ev.tick,
        message: ev.message,
        category,
      };
    });

  return {
    grid,
    shelves: bGrid?.shelves || [],
    robotPos,
    packingPos: { row: packingCoord[0], col: packingCoord[1] },
    chargingPos: { row: chargingCoord[0], col: chargingCoord[1] },
    startPos: { row: startCoord[0], col: startCoord[1] },
    robotState: (bRobot?.state || 'idle').toLowerCase(),
    battery: bRobot?.battery ?? 100,
    distanceTravelled: bMetrics?.distance_travelled ?? bRobot?.total_distance_travelled ?? 0,
    plannedPath,
    traversedPath,
    obstacles,
    orders,
    currentOrder,
    tick: backendState.tick ?? 0,
    ordersCompleted: bMetrics?.successful_deliveries ?? bMetrics?.completed_orders ?? 0,
    routeReplans: bMetrics?.route_replanning_count ?? 0,
    simStatus: backendState.status || currentStatus,
    speed,
    activityLog,
    decision,
    metrics: bMetrics || {},
  };
}

// ── Mock Initial State Factory (Fallback) ──────────────────────────────────

function buildMockInitialState(seed = 42) {
  const mapData = generateMap(seed);
  const { valid, errors } = validateMap(mapData);
  if (!valid) console.warn('[WareBot] Map validation errors:', errors);

  const orders = generateOrders(mapData.shelves, seed);

  return {
    grid: mapData.grid,
    shelves: mapData.shelves,
    robotPos: { ...mapData.robotPos },
    packingPos: { ...mapData.packingPos },
    chargingPos: { ...mapData.chargingPos },
    startPos: { ...mapData.robotPos },
    robotState: 'idle',
    battery: 100,
    distanceTravelled: 0,
    plannedPath: [],
    traversedPath: [],
    obstacles: [],
    orders,
    currentOrder: null,
    phase: 'idle',
    actionTicks: 0,
    tick: 0,
    ordersCompleted: 0,
    routeReplans: 0,
    simStatus: 'idle',
    speed: 2,
    activityLog: [
      { id: 1, time: 'T-0000', tick: 0, message: 'WareBot AI — local fallback mock initialized.', category: 'system' },
      { id: 2, time: 'T-0000', tick: 0, message: `Map: ${mapData.shelves.length} shelves, ${orders.length} orders queued.`, category: 'system' },
    ],
    decision: {
      goal: 'Awaiting simulation start',
      action: 'STANDBY',
      reason: 'Simulation ready.',
      candidates: [],
      pathLength: 0,
      batteryFeasible: true,
      lastEvent: 'System initialized',
    },
    metrics: {},
    currentSeed: seed,
  };
}

// ── Main Simulation Hook ───────────────────────────────────────────────────

export function useSimulation() {
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'mock'
  const [isLiveMode, setIsLiveMode] = useState(import.meta.env.VITE_MOCK_MODE !== 'true');
  const [state, setState] = useState(() => buildMockInitialState(42));
  const [speed, setSpeedState] = useState(2);
  const lastTickRef = useRef(-1);

  // ── Establish Real-Time Backend Connection ───────────────────────────────
  const initBackendConnection = useCallback(async () => {
    if (!isLiveMode) {
      setConnectionStatus('mock');
      return;
    }

    setConnectionStatus('connecting');
    try {
      // 1. Fetch initial state via REST
      const backendState = await simulationApi.getState();
      lastTickRef.current = backendState.tick;
      setState(mapBackendToUiState(backendState, backendState.status || 'idle', speed));
      setConnectionStatus('connected');

      // 2. Connect WebSocket stream
      simulationSocket.connect();
    } catch (err) {
      console.warn('[useSimulation] Backend not reachable. Operating in offline/mock mode:', err.message);
      setConnectionStatus('offline');
    }
  }, [isLiveMode, speed]);

  useEffect(() => {
    initBackendConnection();

    // Subscribe to WebSocket messages
    const unsubMessage = simulationSocket.onMessage(payload => {
      if (payload.type === 'simulation_state' && payload.data) {
        const bState = payload.data;
        // Accept new state or state updates
        lastTickRef.current = bState.tick;
        setState(prev => mapBackendToUiState(bState, bState.status || prev.simStatus, speed));
      } else if (payload.type === 'simulation_status') {
        setState(prev => ({
          ...prev,
          simStatus: payload.status,
          tick: payload.tick ?? prev.tick,
        }));
      }
    });

    // Subscribe to socket status
    const unsubStatus = simulationSocket.onStatusChange(socketStatus => {
      if (isLiveMode) {
        setConnectionStatus(socketStatus);
      }
    });

    return () => {
      unsubMessage();
      unsubStatus();
      simulationSocket.disconnect();
    };
  }, [initBackendConnection, isLiveMode, speed]);

  // ── User Control Actions ─────────────────────────────────────────────────

  const start = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const res = await simulationApi.startSimulation();
        setState(prev => ({ ...prev, simStatus: res.status }));
      } catch (err) {
        console.error('[useSimulation] Start failed:', err);
      }
    } else {
      // Mock fallback
      setState(prev => ({ ...prev, simStatus: 'running' }));
    }
  }, [connectionStatus]);

  const pause = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const res = await simulationApi.pauseSimulation();
        setState(prev => ({ ...prev, simStatus: res.status }));
      } catch (err) {
        console.error('[useSimulation] Pause failed:', err);
      }
    } else {
      // Mock fallback
      setState(prev => ({ ...prev, simStatus: 'paused' }));
    }
  }, [connectionStatus]);

  const resume = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const res = await simulationApi.resumeSimulation();
        setState(prev => ({ ...prev, simStatus: res.status }));
      } catch (err) {
        console.error('[useSimulation] Resume failed:', err);
      }
    } else {
      // Mock fallback
      setState(prev => ({ ...prev, simStatus: 'running' }));
    }
  }, [connectionStatus]);

  const reset = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const bState = await simulationApi.resetSimulation();
        setState(mapBackendToUiState(bState, 'idle', speed));
      } catch (err) {
        console.error('[useSimulation] Reset failed:', err);
      }
    } else {
      // Mock fallback
      setState(buildMockInitialState(42));
    }
  }, [connectionStatus, speed]);

  const step = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const bState = await simulationApi.stepSimulation(1);
        setState(mapBackendToUiState(bState, 'paused', speed));
      } catch (err) {
        console.error('[useSimulation] Step failed:', err);
      }
    } else {
      // Mock fallback: advance 1 tick locally
      setState(prev => ({ ...prev, tick: prev.tick + 1, simStatus: 'paused' }));
    }
  }, [connectionStatus, speed]);

  const newSimulation = useCallback(async () => {
    const freshSeed = Math.floor(Math.random() * 10000);
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        const bState = await simulationApi.createSimulation({ seed: freshSeed });
        setState(mapBackendToUiState(bState, 'idle', speed));
      } catch (err) {
        console.error('[useSimulation] New simulation creation failed:', err);
      }
    } else {
      // Mock fallback
      setState(buildMockInitialState(freshSeed));
    }
  }, [connectionStatus, speed]);

  const addObstacle = useCallback(async (coordOrRow = null, maybeCol = null) => {
    let r = null;
    let c = null;
    if (typeof coordOrRow === 'object' && coordOrRow !== null) {
      r = coordOrRow.row;
      c = coordOrRow.col;
    } else if (typeof coordOrRow === 'number' && typeof maybeCol === 'number') {
      r = coordOrRow;
      c = maybeCol;
    }

    // Do not place random obstacles; require specific grid cell coordinates
    if (r === null || c === null) {
      return;
    }

    const payload = { row: r, col: c, duration_ticks: 120 };

    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        await simulationApi.addObstacle(payload);
      } catch (err) {
        console.warn('[useSimulation] Add obstacle rejected by backend:', err.message);
      }
    } else {
      // Mock fallback: toggle obstacle at exact coordinate
      setState(prev => {
        const exists = prev.obstacles.some(o => o.row === r && o.col === c);
        const updatedObs = exists
          ? prev.obstacles.filter(o => !(o.row === r && o.col === c))
          : [...prev.obstacles, { row: r, col: c }];

        const eventMsg = exists
          ? `Obstacle removed at [${r}, ${c}].`
          : `Obstacle placed at [${r}, ${c}].`;

        return {
          ...prev,
          obstacles: updatedObs,
          activityLog: [
            {
              id: Date.now(),
              time: `T-${String(prev.tick).padStart(4, '0')}`,
              tick: prev.tick,
              message: eventMsg,
              category: exists ? 'system' : 'warning',
            },
            ...prev.activityLog,
          ],
        };
      });
    }
  }, [connectionStatus]);

  const addUrgentOrder = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        await simulationApi.createUrgentOrder();
      } catch (err) {
        console.error('[useSimulation] Add urgent order failed:', err);
      }
    } else {
      // Mock fallback
      setState(prev => {
        const urgent = createMockUrgentOrder(prev.shelves, prev.orders.length);
        return {
          ...prev,
          orders: [urgent, ...prev.orders],
        };
      });
    }
  }, [connectionStatus]);

  const replenishStock = useCallback(async () => {
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        await simulationApi.replenishInventory({ amount: 5 });
      } catch (err) {
        console.error('[useSimulation] Replenish stock failed:', err);
      }
    } else {
      // Mock fallback
      setState(prev => ({
        ...prev,
        activityLog: [
          { id: Date.now(), time: `T-${String(prev.tick).padStart(4, '0')}`, tick: prev.tick, message: 'Stock replenished (+5 units).', category: 'system' },
          ...prev.activityLog,
        ],
      }));
    }
  }, [connectionStatus]);

  const setSpeed = useCallback(async (newSpeed) => {
    setSpeedState(newSpeed);
    if (connectionStatus === 'connected' || connectionStatus === 'connecting') {
      try {
        await simulationApi.setSpeed(newSpeed);
      } catch (err) {
        console.warn('[useSimulation] Set speed error:', err);
      }
    }
    setState(prev => ({ ...prev, speed: newSpeed }));
  }, [connectionStatus]);

  const switchMode = useCallback((mode) => {
    if (mode === 'live') {
      setIsLiveMode(true);
      initBackendConnection();
    } else {
      setIsLiveMode(false);
      simulationSocket.disconnect();
      setConnectionStatus('mock');
    }
  }, [initBackendConnection]);

  const retryConnection = useCallback(() => {
    initBackendConnection();
  }, [initBackendConnection]);

  return {
    state,
    connectionStatus,
    isLiveMode,
    start,
    pause,
    resume,
    reset,
    step,
    newSimulation,
    addObstacle,
    addUrgentOrder,
    replenishStock,
    setSpeed,
    switchMode,
    retryConnection,
  };
}
