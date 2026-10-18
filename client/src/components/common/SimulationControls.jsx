import { Play, Pause, RotateCcw, SkipForward, Square } from 'lucide-react';

export default function SimulationControls({
  state,
  start, pause, resume, reset, step,
}) {
  const { simStatus } = state;
  const isRunning = simStatus === 'running';
  const isPaused  = simStatus === 'paused';
  const isIdle    = simStatus === 'idle';

  return (
    <div className="panel flex items-center gap-2 px-3 py-2 shrink-0">
      <span className="panel-title mr-1">Simulation</span>

      {/* Start / Pause / Resume */}
      {isIdle && (
        <button
          id="btn-start"
          className="btn btn-success"
          onClick={start}
          aria-label="Start simulation"
        >
          <Play size={13} /> Start
        </button>
      )}
      {isRunning && (
        <button
          id="btn-pause"
          className="btn btn-warning"
          onClick={pause}
          aria-label="Pause simulation"
        >
          <Pause size={13} /> Pause
        </button>
      )}
      {isPaused && (
        <>
          <button
            id="btn-resume"
            className="btn btn-success"
            onClick={resume}
            aria-label="Resume simulation"
          >
            <Play size={13} /> Resume
          </button>
          <button
            id="btn-step"
            className="btn btn-ghost"
            onClick={step}
            aria-label="Step one simulation tick"
            title="Advance one tick"
          >
            <SkipForward size={13} /> Step
          </button>
        </>
      )}

      {/* Stop (pause + go to idle) */}
      {isRunning && (
        <button
          id="btn-stop"
          className="btn btn-ghost"
          onClick={pause}
          aria-label="Stop simulation"
          title="Pause simulation"
        >
          <Square size={12} />
        </button>
      )}

      {/* Step when idle */}
      {isIdle && (
        <button
          id="btn-step-idle"
          className="btn btn-ghost"
          onClick={() => { start(); setTimeout(pause, 100); }}
          aria-label="Single step from idle"
          title="Start then immediately pause for one tick"
        >
          <SkipForward size={13} /> Step
        </button>
      )}

      {/* Reset */}
      <button
        id="btn-reset"
        className="btn btn-danger ml-1"
        onClick={reset}
        aria-label="Reset simulation to initial state"
        title="Reset to seed-42 initial state"
      >
        <RotateCcw size={13} /> Reset
      </button>

      {/* Status info */}
      <div className="ml-auto flex items-center gap-3 text-[11px] text-wh-muted">
        <span>
          Tick: <span className="font-mono text-gray-300">{state.tick}</span>
        </span>
        <span>
          Phase: <span className="font-mono text-cyan-400">{state.phase?.replace('_', ' ') || 'idle'}</span>
        </span>
      </div>
    </div>
  );
}
