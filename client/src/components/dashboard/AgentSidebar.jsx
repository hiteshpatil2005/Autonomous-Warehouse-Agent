import { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Flag, 
  Target, 
  Battery, 
  BatteryCharging, 
  BatteryWarning, 
  Zap, 
  MapPin, 
  Package, 
  ShieldAlert, 
  CheckCircle2, 
  ScrollText, 
  Layers,
  ArrowRight
} from 'lucide-react';

const STATE_CONFIG = {
  idle:        { label: 'STANDBY / IDLE',  bg: 'bg-gray-800 text-gray-300 border-gray-600', dot: 'bg-gray-400' },
  navigating:  { label: 'NAVIGATING (A*)', bg: 'bg-blue-950 text-blue-300 border-blue-700',   dot: 'bg-blue-400 animate-pulse' },
  picking:     { label: 'PICKING ITEM',    bg: 'bg-amber-950 text-amber-300 border-amber-700', dot: 'bg-amber-400 animate-ping' },
  returning:   { label: 'RETURNING',       bg: 'bg-indigo-950 text-indigo-300 border-indigo-700', dot: 'bg-indigo-400 animate-pulse' },
  packing:     { label: 'PACKING ORDER',   bg: 'bg-emerald-950 text-emerald-300 border-emerald-700', dot: 'bg-emerald-400' },
  charging:    { label: 'RECHARGING DOCK', bg: 'bg-teal-950 text-teal-300 border-teal-700', dot: 'bg-teal-400' },
  blocked:     { label: 'OBSTACLE BLOCKED',bg: 'bg-rose-950 text-rose-300 border-rose-700', dot: 'bg-rose-400 animate-bounce' },
  waiting:     { label: 'WAITING',         bg: 'bg-purple-950 text-purple-300 border-purple-700', dot: 'bg-purple-400' },
};

const CATEGORY_STYLE = {
  robot:   { dot: 'bg-cyan-400',   text: 'text-cyan-300',   badge: 'bg-cyan-950/70 border-cyan-800 text-cyan-300' },
  orders:  { dot: 'bg-emerald-400', text: 'text-emerald-300', badge: 'bg-emerald-950/70 border-emerald-800 text-emerald-300' },
  system:  { dot: 'bg-slate-400',  text: 'text-slate-300',  badge: 'bg-slate-900 border-slate-700 text-slate-300' },
  warning: { dot: 'bg-amber-400',  text: 'text-amber-300',  badge: 'bg-amber-950/70 border-amber-800 text-amber-300' },
  danger:  { dot: 'bg-rose-500',   text: 'text-rose-300',   badge: 'bg-rose-950/70 border-rose-800 text-rose-300' },
};

export default function AgentSidebar({ state, isObstacleMode, onToggleObstacleMode }) {
  const [filter, setFilter] = useState('All');
  const [autoScroll, setAutoScroll] = useState(true);
  const logRef = useRef(null);

  const {
    robotPos,
    startPos = { row: 28, col: 1 },
    robotState = 'idle',
    battery = 100,
    currentOrder,
    plannedPath = [],
    obstacles = [],
    activityLog = [],
    distanceTravelled = 0,
    ordersCompleted = 0,
    routeReplans = 0,
    decision,
  } = state;

  const rStateKey = (robotState || 'idle').toLowerCase();
  const stateBadge = STATE_CONFIG[rStateKey] || STATE_CONFIG.idle;

  // Determine realistic Goal target definition
  let goalTitle = 'Awaiting Mission Assignment';
  let goalSubtitle = 'Robot ready at dock';
  let goalCoords = null;
  let goalType = 'standby';

  if (rStateKey === 'navigating' || rStateKey === 'picking') {
    if (currentOrder) {
      goalTitle = `Shelf ${currentOrder.shelfId} — ${currentOrder.product}`;
      goalSubtitle = `Order #${currentOrder.id} (${currentOrder.priority} Priority, Qty: ${currentOrder.quantity})`;
      goalCoords = currentOrder.targetShelfPos || currentOrder.shelfPos;
      goalType = 'shelf';
    } else {
      goalTitle = 'Navigating to Designated Waypoint';
      goalSubtitle = 'A* Autonomous Pathfinding';
      goalCoords = plannedPath.length > 0 ? plannedPath[plannedPath.length - 1] : null;
      goalType = 'waypoint';
    }
  } else if (rStateKey === 'returning' || rStateKey === 'packing') {
    goalTitle = 'Packing Station Bay [28, 14]';
    goalSubtitle = currentOrder ? `Fulfilling Order #${currentOrder.id}` : 'Order Finalization & Dispatch';
    goalCoords = { row: 28, col: 14 };
    goalType = 'packing';
  } else if (rStateKey === 'charging') {
    goalTitle = 'Charging Station Dock [28, 27]';
    goalSubtitle = 'Automated Rapid Recharge Dock';
    goalCoords = { row: 28, col: 27 };
    goalType = 'charging';
  } else if (rStateKey === 'blocked') {
    goalTitle = 'Path Obstructed by Obstacle';
    goalSubtitle = 'Autonomous A* replanning or waiting for clearance';
    goalType = 'blocked';
  }

  // Auto-scroll to top when new events appear
  const prevLen = useRef(activityLog?.length ?? 0);
  useEffect(() => {
    if (autoScroll && logRef.current && (activityLog?.length ?? 0) > prevLen.current) {
      logRef.current.scrollTop = 0;
    }
    prevLen.current = activityLog?.length ?? 0;
  }, [activityLog, autoScroll]);

  const filteredLog = (activityLog || []).filter(entry => {
    if (filter === 'All') return true;
    if (filter === 'Robot') return entry.category === 'robot';
    if (filter === 'Orders') return entry.category === 'orders';
    if (filter === 'Obstacles') return entry.category === 'warning' || entry.message?.toLowerCase().includes('obstacle');
    return true;
  });

  return (
    <aside className="w-80 md:w-96 flex flex-col gap-2.5 h-full overflow-hidden shrink-0">
      {/* ── Realistic Agent Mission & Location Card ─────────────────── */}
      <div className="panel p-3 flex flex-col gap-2.5 shrink-0 bg-wh-panel/90 border border-wh-border shadow-md">
        {/* Header & Agent State */}
        <div className="flex items-center justify-between pb-2 border-b border-wh-border/60">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-cyan-950 border border-cyan-600/70 flex items-center justify-center shadow-sm">
              <Bot size={16} className="text-cyan-400" />
            </div>
            <div>
              <div className="text-xs font-bold text-white flex items-center gap-1.5">
                WareBot RB-01
                <span className="text-[10px] text-cyan-400 font-mono font-normal">
                  [{robotPos?.row ?? 28}, {robotPos?.col ?? 1}]
                </span>
              </div>
              <div className="text-[10px] text-wh-muted">Autonomous AGV Agent</div>
            </div>
          </div>

          <div className={`badge border text-[10px] px-2 py-0.5 font-mono ${stateBadge.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${stateBadge.dot}`} />
            {stateBadge.label}
          </div>
        </div>

        {/* Realistic Origin and Goal Definition */}
        <div className="flex flex-col gap-2 bg-wh-bg/70 p-2.5 rounded-lg border border-wh-border/60">
          {/* Starting Point */}
          <div className="flex items-start gap-2 text-xs">
            <div className="w-5 h-5 rounded bg-emerald-950 border border-emerald-600/80 flex items-center justify-center shrink-0 mt-0.5">
              <Flag size={11} className="text-emerald-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400">Starting Point</span>
                <span className="text-[10px] font-mono text-emerald-300 bg-emerald-950/60 px-1 rounded">
                  [{startPos.row}, {startPos.col}]
                </span>
              </div>
              <div className="text-[11px] text-gray-200 font-medium truncate">
                Base Dock Alpha (Dispatch Origin)
              </div>
            </div>
          </div>

          {/* Path vector icon */}
          <div className="flex items-center gap-1.5 px-2 text-[10px] text-wh-muted font-mono">
            <div className="w-px h-3 bg-wh-border ml-2" />
            <span className="text-cyan-400/80">
              {plannedPath.length > 0 ? `A* Route: ${plannedPath.length} steps remaining` : 'At location'}
            </span>
          </div>

          {/* Current Goal */}
          <div className="flex items-start gap-2 text-xs">
            <div className="w-5 h-5 rounded bg-amber-950 border border-amber-600/80 flex items-center justify-center shrink-0 mt-0.5">
              <Target size={11} className="text-amber-400 animate-pulse" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400">Current Goal</span>
                {goalCoords && (
                  <span className="text-[10px] font-mono text-amber-300 bg-amber-950/60 px-1 rounded">
                    [{goalCoords.row}, {goalCoords.col}]
                  </span>
                )}
              </div>
              <div className="text-[11px] text-white font-semibold truncate">
                {goalTitle}
              </div>
              <div className="text-[10px] text-wh-muted truncate">
                {goalSubtitle}
              </div>
            </div>
          </div>
        </div>

        {/* Battery & Quick Telemetry */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-[11px] text-wh-muted">
              {battery > 50 ? (
                <Battery size={13} className="text-emerald-400" />
              ) : battery > 20 ? (
                <BatteryCharging size={13} className="text-amber-400" />
              ) : (
                <BatteryWarning size={13} className="text-rose-400 animate-bounce" />
              )}
              Battery Level
            </span>
            <span className="font-mono text-xs font-bold text-gray-200">{Math.round(battery)}%</span>
          </div>

          {/* Battery progress bar */}
          <div className="w-full bg-wh-bg h-2 rounded-full overflow-hidden border border-wh-border/50">
            <div
              className={`h-full transition-all duration-300 ${
                battery > 50 ? 'bg-emerald-500' : battery > 20 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${Math.max(0, Math.min(100, battery))}%` }}
            />
          </div>

          {/* Bottom Telemetry Pills */}
          <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
            <div className="bg-wh-card/60 p-1.5 rounded border border-wh-border/50">
              <div className="text-[9px] text-wh-muted">Travelled</div>
              <div className="font-mono text-xs font-bold text-cyan-300">{distanceTravelled}m</div>
            </div>
            <div className="bg-wh-card/60 p-1.5 rounded border border-wh-border/50">
              <div className="text-[9px] text-wh-muted">Delivered</div>
              <div className="font-mono text-xs font-bold text-emerald-300">{ordersCompleted}</div>
            </div>
            <div className="bg-wh-card/60 p-1.5 rounded border border-wh-border/50">
              <div className="text-[9px] text-wh-muted">Replans</div>
              <div className="font-mono text-xs font-bold text-amber-300">{routeReplans}</div>
            </div>
          </div>
        </div>

        {/* Obstacle Mode Active Banner if toggled */}
        {isObstacleMode && (
          <div className="p-2 rounded bg-rose-950/80 border border-rose-700/80 flex items-center justify-between animate-pulse text-[11px] text-rose-200">
            <span className="flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-rose-400" />
              Click any box on grid to place/remove barrier
            </span>
            <button
              onClick={onToggleObstacleMode}
              className="text-[10px] underline font-bold hover:text-white"
            >
              Done
            </button>
          </div>
        )}
      </div>

      {/* ── Live Agent Activity Log (Takes remaining height) ───────── */}
      <div className="panel flex flex-col flex-1 min-h-0 bg-wh-panel/90 border border-wh-border shadow-md">
        {/* Header */}
        <div className="panel-header py-2 px-3 border-b border-wh-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ScrollText size={13} className="text-cyan-400" />
            <span className="text-xs font-bold text-white">Agent Activity Log</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-wh-muted">
              {activityLog?.length ?? 0} events
            </span>
            <button
              onClick={() => setAutoScroll(v => !v)}
              className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
                autoScroll
                  ? 'border-cyan-700/60 text-cyan-300 bg-cyan-950/50'
                  : 'border-wh-border text-wh-muted hover:text-gray-300'
              }`}
              title="Toggle auto-scroll to latest"
            >
              {autoScroll ? '● Auto' : '○ Paused'}
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 px-2.5 py-1.5 border-b border-wh-border/60 bg-wh-bg/40 text-[10px]">
          {['All', 'Robot', 'Obstacles', 'Orders'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded transition-all font-medium ${
                filter === f
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-sm'
                  : 'text-wh-muted hover:text-gray-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Log Entries Container */}
        <div
          ref={logRef}
          className="flex-1 overflow-y-auto p-2 flex flex-col gap-1 font-mono text-xs"
        >
          {filteredLog.length === 0 ? (
            <div className="text-center text-wh-muted text-xs py-8">
              No activity logged yet
            </div>
          ) : (
            filteredLog.map(entry => {
              const cat = CATEGORY_STYLE[entry.category] || CATEGORY_STYLE.system;
              return (
                <div
                  key={entry.id}
                  className="flex items-start gap-2 p-1.5 rounded bg-wh-bg/40 hover:bg-wh-card/80 border border-wh-border/30 transition-colors log-entry-new"
                >
                  <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${cat.dot}`} />
                  <div className="min-w-0 flex-1 leading-snug">
                    <div className="flex items-center justify-between text-[9px] text-wh-muted mb-0.5">
                      <span>{entry.time}</span>
                      <span className={`px-1 rounded text-[8px] border uppercase ${cat.badge}`}>
                        {entry.category}
                      </span>
                    </div>
                    <div className={`text-[11px] font-sans ${cat.text} break-words`}>
                      {entry.message}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}
