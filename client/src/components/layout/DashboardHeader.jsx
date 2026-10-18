import { 
  Bot, 
  Wifi, 
  WifiOff, 
  Clock, 
  Zap, 
  RefreshCw, 
  Play, 
  Pause, 
  RotateCcw, 
  SkipForward, 
  Square,
  ShieldAlert,
  BarChart3
} from 'lucide-react';

const STATUS_CONFIG = {
  idle:      { label: 'STANDBY',   cls: 'bg-gray-800 text-gray-300 border-gray-600', dot: 'bg-gray-400' },
  running:   { label: 'RUNNING',   cls: 'bg-emerald-950 text-emerald-300 border-emerald-700', dot: 'bg-emerald-400' },
  paused:    { label: 'PAUSED',    cls: 'bg-amber-950 text-amber-300 border-amber-700', dot: 'bg-amber-400' },
  completed: { label: 'COMPLETED', cls: 'bg-blue-950 text-blue-300 border-blue-700', dot: 'bg-blue-400' },
};

const CONNECTION_BADGES = {
  connected:    { label: 'LIVE: CONNECTED', cls: 'bg-emerald-950 text-emerald-300 border-emerald-700', icon: Wifi },
  connecting:   { label: 'CONNECTING...',   cls: 'bg-cyan-950 text-cyan-300 border-cyan-700',       icon: Wifi },
  reconnecting: { label: 'RECONNECTING...', cls: 'bg-amber-950 text-amber-300 border-amber-700',     icon: Wifi },
  offline:      { label: 'OFFLINE',         cls: 'bg-rose-950 text-rose-300 border-rose-800',       icon: WifiOff },
  mock:         { label: 'MOCK MODE',       cls: 'bg-indigo-950 text-indigo-300 border-indigo-800',  icon: WifiOff },
};

export default function DashboardHeader({
  simStatus = 'idle',
  tick = 0,
  speed = 2,
  activeTab = 'simulation',
  onSelectTab,
  connectionStatus = 'connected',
  onNewSimulation,
  onSetSpeed,
  onRetry,
  // Primary top simulation controls:
  onStart,
  onPause,
  onResume,
  onReset,
  onStep,
  // Obstacle toggle mode:
  isObstacleMode = false,
  onToggleObstacleMode,
}) {
  const status = STATUS_CONFIG[simStatus] || STATUS_CONFIG.idle;
  const connBadge = CONNECTION_BADGES[connectionStatus] || CONNECTION_BADGES.offline;
  const ConnIcon = connBadge.icon;

  const isRunning = simStatus === 'running';
  const isPaused  = simStatus === 'paused';
  const isIdle    = simStatus === 'idle' || simStatus === 'completed';

  return (
    <header className="flex items-center justify-between gap-3 px-4 py-2 border-b border-wh-border bg-wh-panel shrink-0 shadow-sm">
      {/* ── Brand Logo ────────────────────────────────────────── */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-600 flex items-center justify-center shadow-sm">
          <Bot size={18} className="text-cyan-400" />
        </div>
        <div>
          <div className="text-sm font-bold text-white leading-tight flex items-center gap-2">
            WareBot AI
            <span className={`badge border text-[9px] px-1.5 py-0 font-mono ${status.cls}`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-1 ${status.dot}`} />
              {status.label}
            </span>
          </div>
          <div className="text-[10px] text-wh-muted leading-tight font-mono">
            Autonomous Warehouse AGV Simulation
          </div>
        </div>
      </div>

      {/* ── Top Simulation Action Controls ───────────────────────── */}
      <div className="flex items-center gap-2 bg-wh-bg/80 px-2.5 py-1 rounded-lg border border-wh-border">
        {/* Play / Start Button */}
        {isIdle && (
          <button
            id="btn-start"
            onClick={onStart}
            className="btn btn-success text-xs py-1 px-3 shadow-sm font-semibold flex items-center gap-1.5"
            aria-label="Start simulation"
            title="Start warehouse agent simulation"
          >
            <Play size={13} className="fill-current" />
            Start / Play
          </button>
        )}

        {/* Resume Button */}
        {isPaused && (
          <button
            id="btn-resume"
            onClick={onResume}
            className="btn btn-success text-xs py-1 px-3 shadow-sm font-semibold flex items-center gap-1.5"
            aria-label="Resume simulation"
            title="Resume running simulation"
          >
            <Play size={13} className="fill-current" />
            Resume
          </button>
        )}

        {/* Pause Button */}
        {isRunning && (
          <button
            id="btn-pause"
            onClick={onPause}
            className="btn btn-warning text-xs py-1 px-3 shadow-sm font-semibold flex items-center gap-1.5"
            aria-label="Pause simulation"
            title="Pause simulation"
          >
            <Pause size={13} className="fill-current" />
            Pause
          </button>
        )}

        {/* Stop / Reset Button */}
        <button
          id="btn-reset"
          onClick={onReset}
          className="btn btn-danger text-xs py-1 px-2.5 shadow-sm font-semibold flex items-center gap-1.5"
          aria-label="Reset simulation to initial state"
          title="Stop and reset robot to Dock Alpha [28, 1]"
        >
          <RotateCcw size={12} />
          Stop / Reset
        </button>

        {/* Step Button */}
        <button
          id="btn-step"
          onClick={onStep}
          className="btn btn-ghost text-xs py-1 px-2 flex items-center gap-1"
          aria-label="Advance one simulation step"
          title="Advance exactly 1 simulation tick"
        >
          <SkipForward size={12} />
          Step
        </button>

        <div className="w-px h-5 bg-wh-border mx-0.5" />

        {/* + Add Obstacle Toggle Button */}
        <button
          id="btn-add-obstacle"
          onClick={onToggleObstacleMode}
          className={`text-xs py-1 px-3 rounded-md font-semibold transition-all border flex items-center gap-1.5 shadow-sm ${
            isObstacleMode
              ? 'bg-rose-600 text-white border-rose-400 ring-2 ring-rose-400/50 animate-pulse'
              : 'bg-rose-950/60 border-rose-800 text-rose-300 hover:bg-rose-900/80'
          }`}
          aria-label="Toggle obstacle placement mode"
          title="Click to toggle obstacle placement mode on any grid cell"
        >
          <ShieldAlert size={13} />
          {isObstacleMode ? '✕ Obstacle Active' : '+ Add Obstacle'}
        </button>
      </div>

      {/* ── Status, Speed & Live Telemetry ────────────────────── */}
      <div className="flex items-center gap-2.5">
        {/* Tick counter */}
        <div className="flex items-center gap-1 text-xs text-wh-muted bg-wh-card/80 px-2 py-1 rounded border border-wh-border/60">
          <Clock size={11} className="text-cyan-400" />
          <span className="font-mono text-gray-200 text-xs font-semibold">T-{String(tick).padStart(4, '0')}</span>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1.5 text-xs text-wh-muted">
          <Zap size={12} className="text-amber-400" />
          <select
            value={speed}
            onChange={e => onSetSpeed && onSetSpeed(Number(e.target.value))}
            aria-label="Simulation speed"
            className="bg-wh-card border border-wh-border text-xs rounded px-2 py-1 text-gray-200 font-mono focus:outline-none focus:border-cyan-500"
          >
            <option value={1}>1x (2Hz)</option>
            <option value={2}>2x (5Hz)</option>
            <option value={3}>3x (8Hz)</option>
            <option value={4}>4x (12Hz)</option>
            <option value={5}>5x (20Hz)</option>
          </select>
        </div>

        {/* Connection status badge */}
        <div
          className={`badge border text-[10px] font-mono px-2 py-1 flex items-center gap-1 ${connBadge.cls}`}
          title={`Backend status: ${connectionStatus}`}
        >
          <ConnIcon size={11} className={connectionStatus === 'connecting' || connectionStatus === 'reconnecting' ? 'animate-pulse' : ''} />
          {connBadge.label}
        </div>

        {connectionStatus === 'offline' && onRetry && (
          <button
            onClick={onRetry}
            className="btn btn-ghost text-[10px] py-1 px-2 border border-wh-border"
            title="Attempt to reconnect to backend"
          >
            <RefreshCw size={10} className="mr-1" /> Retry
          </button>
        )}

        {/* View Switcher: Simulation vs Benchmark */}
        <div className="flex items-center bg-wh-card rounded-md p-0.5 border border-wh-border">
          <button
            onClick={() => onSelectTab && onSelectTab('simulation')}
            className={`px-2 py-0.5 text-xs rounded font-medium transition-all ${
              activeTab === 'simulation'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-sm'
                : 'text-wh-muted hover:text-gray-200'
            }`}
            title="Interactive Simulation View"
          >
            Simulation
          </button>
          <button
            onClick={() => onSelectTab && onSelectTab('benchmark')}
            className={`px-2 py-0.5 text-xs rounded font-medium transition-all ${
              activeTab === 'benchmark'
                ? 'bg-amber-950 text-amber-300 border border-amber-700/60 shadow-sm'
                : 'text-wh-muted hover:text-gray-200'
            }`}
            title="A* vs Nearest Benchmark View"
          >
            Analytics
          </button>
        </div>
      </div>
    </header>
  );
}
