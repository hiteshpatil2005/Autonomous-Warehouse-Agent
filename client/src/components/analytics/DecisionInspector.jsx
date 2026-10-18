import { Brain, Cpu, Route, Battery, Target, Zap } from 'lucide-react';

function ScoreBar({ action, score }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-mono text-wh-muted w-32 truncate">{action}</span>
      <div className="flex-1 bg-wh-border rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            background: pct > 70 ? '#06b6d4' : pct > 40 ? '#d97706' : '#4b5563',
          }}
        />
      </div>
      <span className="text-[10px] font-mono text-gray-300 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function DecisionInspector({ decision, robotState, battery }) {
  if (!decision) return null;

  const battColor = battery > 50 ? 'text-green-400' : battery > 20 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="panel flex flex-col">
      {/* Header */}
      <div className="panel-header">
        <Brain size={13} className="text-cyan-400" />
        <span className="panel-title">AI Decision Inspector</span>
        <span className="ml-auto badge border border-cyan-800 bg-cyan-950 text-cyan-300 text-[9px]">LIVE AI</span>
      </div>

      <div className="p-3 flex flex-col gap-2.5 text-xs">
        {/* Engine description */}
        <p className="text-[10px] text-wh-muted bg-wh-border/30 rounded px-2 py-1 italic">
          Autonomous multi-factor utility evaluation (Python backend engine).
        </p>

        {/* Current goal */}
        <div>
          <div className="text-[10px] text-wh-muted uppercase tracking-widest mb-1 flex items-center gap-1">
            <Target size={10} />  Goal
          </div>
          <div className="text-gray-200 font-medium">{decision.goal}</div>
        </div>

        {/* Action + reason */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <div className="text-[10px] text-wh-muted uppercase tracking-widest mb-1 flex items-center gap-1">
              <Cpu size={10} /> Action
            </div>
            <div className="font-mono text-cyan-300 text-[11px]">{decision.action}</div>
          </div>
          <div>
            <div className="text-[10px] text-wh-muted uppercase tracking-widest mb-1">Route</div>
            <div className="font-mono text-gray-200 text-[11px]">
              {decision.pathLength > 0 ? `${decision.pathLength} cells` : '—'}
            </div>
          </div>
        </div>

        {/* Reason */}
        <div>
          <div className="text-[10px] text-wh-muted uppercase tracking-widest mb-1 flex items-center gap-1">
            <Zap size={10} /> Reasoning
          </div>
          <div className="text-gray-300 text-[11px] leading-relaxed">{decision.reason}</div>
        </div>

        {/* Battery feasibility */}
        <div className="flex items-center gap-2">
          <Battery size={12} className={battColor} />
          <span className={`text-[11px] ${battColor}`}>{battery.toFixed(0)}% battery</span>
          <span className={`ml-1 text-[10px] ${decision.batteryFeasible ? 'text-green-400' : 'text-red-400'}`}>
            {decision.batteryFeasible ? '✓ Feasible' : '✗ Insufficient'}
          </span>
        </div>

        {/* Candidate scores */}
        {decision.candidates?.length > 0 && (
          <div>
            <div className="text-[10px] text-wh-muted uppercase tracking-widest mb-1.5 flex items-center gap-1">
              <Route size={10} /> Candidate Scores
            </div>
            <div className="flex flex-col gap-1.5">
              {decision.candidates.map((c, i) => (
                <ScoreBar key={i} action={c.action} score={c.score} />
              ))}
            </div>
          </div>
        )}

        {/* Last event */}
        <div className="pt-1 border-t border-wh-border text-[10px] text-wh-muted">
          Last event: <span className="text-gray-300">{decision.lastEvent}</span>
        </div>
      </div>
    </div>
  );
}
