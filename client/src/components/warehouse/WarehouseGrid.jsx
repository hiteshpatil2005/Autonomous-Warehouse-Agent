import { useMemo, useState, useCallback } from 'react';
import { Map, ShieldAlert, Info } from 'lucide-react';
import WarehouseCell from './WarehouseCell';
import GridLegend from './GridLegend';

/**
 * WarehouseGrid — renders the 30×30 interactive warehouse map.
 *
 * Maximized grid dimensions with prominent boxes.
 * Clearly defined Starting Point, Robot position, Obstacles, and Goal destination beacon.
 * Allows clicking on any grid box to place or remove obstacles directly at that location.
 */
export default function WarehouseGrid({ state, onCellClick, isObstacleMode = false }) {
  const [hoveredCell, setHoveredCell] = useState({ row: null, col: null, type: null, shelfId: null });

  const {
    grid,
    robotPos,
    startPos = { row: 28, col: 1 },
    plannedPath,
    traversedPath,
    obstacles,
    currentOrder,
    packingPos = { row: 28, col: 14 },
    chargingPos = { row: 28, col: 27 },
    robotState = 'idle',
  } = state;

  // Build fast lookup sets for overlay layers
  const overlayKeys = useMemo(() => {
    const planned   = new Set((plannedPath   || []).map(p => `${p.row},${p.col}`));
    const traversed = new Set((traversedPath || []).map(p => `${p.row},${p.col}`));
    const obsSet    = new Set((obstacles     || []).map(o => `${o.row},${o.col}`));

    // Determine realistic destination Goal coordinate:
    let goalCoord = null;
    const rState = (robotState || '').toLowerCase();

    if (rState === 'navigating' || rState === 'picking' || rState === 'idle') {
      if (currentOrder?.targetShelfPos) {
        goalCoord = `${currentOrder.targetShelfPos.row},${currentOrder.targetShelfPos.col}`;
      } else if (currentOrder?.shelfPos) {
        goalCoord = `${currentOrder.shelfPos.row},${currentOrder.shelfPos.col}`;
      } else if (plannedPath && plannedPath.length > 0) {
        const lastStep = plannedPath[plannedPath.length - 1];
        goalCoord = `${lastStep.row},${lastStep.col}`;
      }
    } else if (rState === 'returning' || rState === 'packing') {
      goalCoord = `${packingPos?.row ?? 28},${packingPos?.col ?? 14}`;
    } else if (rState === 'charging') {
      goalCoord = `${chargingPos?.row ?? 28},${chargingPos?.col ?? 27}`;
    }

    const startCoord = `${startPos?.row ?? 28},${startPos?.col ?? 1}`;

    return { planned, traversed, obsSet, goalCoord, startCoord };
  }, [plannedPath, traversedPath, obstacles, currentOrder, robotState, packingPos, chargingPos, startPos]);

  const robotKey = robotPos ? `${robotPos.row},${robotPos.col}` : '';

  // Flatten grid to 1D for rendering
  const cells = useMemo(() => {
    if (!grid) return [];
    const { planned, traversed, obsSet, goalCoord, startCoord } = overlayKeys;
    const result = [];

    for (let r = 0; r < 30; r++) {
      for (let c = 0; c < 30; c++) {
        const cell = grid[r][c];
        const key  = `${r},${c}`;
        let displayType = cell.type;

        // Hierarchy: obstacle > robot > goal > start > planned path > traversed path > base
        if (obsSet.has(key))       displayType = 'obstacle';
        else if (key === robotKey) displayType = 'robot';
        else if (key === goalCoord) displayType = 'goal';
        else if (key === startCoord) displayType = 'start';
        else if (planned.has(key)) displayType = 'path_planned';
        else if (traversed.has(key)) displayType = 'path_traversed';

        result.push({
          row: r, col: c,
          displayType,
          baseType: cell.type,
          shelfId: cell.shelfId,
          key: `${r}-${c}`,
        });
      }
    }
    return result;
  }, [grid, robotKey, overlayKeys]);

  const handleHover = useCallback((row, col, type, shelfId) => {
    setHoveredCell({ row, col, type, shelfId });
  }, []);

  const handleCellClick = useCallback((row, col, baseType) => {
    // Cannot place obstacles on robot or charging/packing station or shelves
    if (baseType === 'charging' || baseType === 'packing' || baseType === 'shelf') {
      return;
    }
    if (robotPos && robotPos.row === row && robotPos.col === col) {
      return;
    }
    onCellClick && onCellClick(row, col);
  }, [onCellClick, robotPos]);

  if (!grid) {
    return (
      <div className="panel flex items-center justify-center flex-1">
        <span className="text-wh-muted text-sm">Initializing simulation map…</span>
      </div>
    );
  }

  return (
    <div className="panel flex flex-col min-h-0 flex-1 h-full overflow-hidden border border-wh-border shadow-md">
      {/* Header bar */}
      <div className="panel-header py-2 px-3 border-b border-wh-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Map size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wide">
            Autonomous Warehouse Map (30 × 30 Grid)
          </span>
          <span className="hidden sm:inline text-[11px] text-wh-muted font-normal">
            — Click any floor cell to place or remove an obstacle
          </span>
        </div>
        <div className="flex items-center gap-2">
          {obstacles?.length > 0 && (
            <span className="badge border bg-rose-950/80 border-rose-800 text-rose-300 font-mono text-[10px]">
              <ShieldAlert size={10} className="mr-1" />
              {obstacles.length} {obstacles.length === 1 ? 'Obstacle' : 'Obstacles'} Active
            </span>
          )}
          <span className="text-[10px] text-wh-muted font-mono bg-wh-card/80 px-2 py-0.5 rounded border border-wh-border/50">
            {state.shelves?.length ?? 0} Shelves
          </span>
        </div>
      </div>

      {/* Main Grid Viewport - Maximized Sizing */}
      <div className="flex-1 flex items-center justify-center p-2 min-h-0 overflow-hidden bg-wh-bg/60">
        <div
          className={`warehouse-grid ${isObstacleMode ? 'cursor-crosshair ring-1 ring-red-500/50' : ''}`}
          style={{
            width: '100%',
            height: '100%',
            maxHeight: 'calc(100vh - 130px)',
            maxWidth: 'calc(100vh - 130px)',
            aspectRatio: '1/1',
            margin: 'auto',
          }}
          role="grid"
          aria-label="Warehouse floor plan"
        >
          {cells.map(cell => (
            <WarehouseCell
              key={cell.key}
              row={cell.row}
              col={cell.col}
              displayType={cell.displayType}
              baseType={cell.baseType}
              shelfId={cell.shelfId}
              isObstacleMode={isObstacleMode}
              onClick={handleCellClick}
              onHover={handleHover}
            />
          ))}
        </div>
      </div>

      {/* Grid Legend Footer */}
      <div className="px-3 py-2 border-t border-wh-border shrink-0 bg-wh-panel/90">
        <GridLegend hoveredCell={hoveredCell} />
      </div>
    </div>
  );
}
