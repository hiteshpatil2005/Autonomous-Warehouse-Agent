import { Battery, Package, CheckCircle, Route, Clock, Bot } from 'lucide-react';

function MetricCard({ icon: Icon, label, value, unit = '', colorClass = 'text-gray-200', subText, iconColor = 'text-wh-muted' }) {
  return (
    <div className="bg-wh-card border border-wh-border rounded-lg px-3 py-2.5 flex items-center gap-3 min-w-0">
      <div className={`shrink-0 ${iconColor}`}>
        <Icon size={18} />
      </div>
      <div className="min-w-0">
        <div className={`metric-value ${colorClass} truncate`}>{value}<span className="text-sm font-normal text-wh-muted ml-0.5">{unit}</span></div>
        <div className="text-[10px] text-wh-muted mt-0.5 truncate">{label}</div>
        {subText && <div className="text-[9px] text-gray-600 truncate">{subText}</div>}
      </div>
    </div>
  );
}

export default function MetricsPanel({ state }) {
  const {
    battery, ordersCompleted, orders, distanceTravelled,
    tick, robotState,
  } = state;

  const pending = orders?.filter(o => o.status === 'pending').length ?? 0;

  const battColor = battery > 50 ? 'text-green-400' : battery > 20 ? 'text-amber-400' : 'text-red-400';
  const battIcon  = battery > 50 ? 'text-green-500' : battery > 20 ? 'text-amber-500' : 'text-red-500';

  const stateLabel = {
    idle:       'IDLE',
    moving:     'NAVIGATING',
    navigating: 'NAVIGATING',
    picking:    'PICKING',
    returning:  'RETURNING',
    packing:    'PACKING',
    charging:   'CHARGING',
    blocked:    'BLOCKED',
    waiting:    'WAITING',
  }[robotState] || (robotState ? robotState.toUpperCase() : 'IDLE');

  const stateColor = {
    idle:       'text-gray-400',
    moving:     'text-cyan-400',
    navigating: 'text-cyan-400',
    picking:    'text-amber-400',
    returning:  'text-indigo-400',
    packing:    'text-amber-300',
    charging:   'text-green-400',
    blocked:    'text-rose-400',
    waiting:    'text-yellow-400',
  }[robotState] || 'text-gray-400';

  // Sim time as HH:MM:SS from tick count (1 tick ≈ configurable ms, display as sim seconds)
  const simSec = tick;
  const simTime = `${String(Math.floor(simSec / 3600)).padStart(2,'0')}:${String(Math.floor((simSec % 3600) / 60)).padStart(2,'0')}:${String(simSec % 60).padStart(2,'0')}`;

  return (
    <div className="grid grid-cols-6 gap-2 shrink-0">
      <MetricCard
        icon={Battery}
        label="Battery"
        value={battery.toFixed(0)}
        unit="%"
        colorClass={battColor}
        iconColor={battIcon}
        subText={robotState === 'charging' ? 'Charging…' : battery < 20 ? 'Low!' : 'Nominal'}
      />
      <MetricCard
        icon={CheckCircle}
        label="Completed"
        value={ordersCompleted}
        colorClass="text-green-400"
        iconColor="text-green-500"
      />
      <MetricCard
        icon={Package}
        label="Pending Orders"
        value={pending}
        colorClass={pending > 0 ? 'text-amber-400' : 'text-gray-400'}
        iconColor={pending > 0 ? 'text-amber-500' : 'text-wh-muted'}
      />
      <MetricCard
        icon={Route}
        label="Distance"
        value={distanceTravelled}
        unit=" cells"
        colorClass="text-cyan-400"
        iconColor="text-cyan-500"
      />
      <MetricCard
        icon={Clock}
        label="Sim Time"
        value={simTime}
        colorClass="text-gray-200"
        iconColor="text-wh-muted"
        subText={`Tick ${tick}`}
      />
      <MetricCard
        icon={Bot}
        label="Robot Status"
        value={stateLabel}
        colorClass={stateColor}
        iconColor={stateColor}
        subText={`Replans: ${state.routeReplans ?? 0}`}
      />
    </div>
  );
}
