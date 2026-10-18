import { memo } from 'react';

// Cell type → visual config
const CELL_STYLE = {
  floor:          { bg: '#0d131f', border: '#151f32' },
  shelf:          { bg: '#1e1b4b', border: '#3730a3' },
  robot:          { bg: '#0891b2', border: '#22d3ee' },
  packing:        { bg: '#78350f', border: '#d97706' },
  charging:       { bg: '#14532d', border: '#22c55e' },
  obstacle:       { bg: '#7f1d1d', border: '#ef4444' },
  path_planned:   { bg: '#1e3a8a', border: '#3b82f6' },
  path_traversed: { bg: '#172554', border: '#1e3a8a' },
  target:         { bg: '#78350f', border: '#f59e0b' },
  goal:           { bg: '#78350f', border: '#f59e0b' },
  start:          { bg: '#064e3b', border: '#10b981' },
};

const CELL_ICONS = {
  robot:    '🤖',
  packing:  '📦',
  charging: '⚡',
  obstacle: '✕',
  goal:     '🎯',
  target:   '🎯',
  start:    '🏁',
  shelf:    null,
};

/**
 * Single warehouse cell.
 * Memoized — only re-renders when displayType, shelfId, or handlers change.
 */
const WarehouseCell = memo(function WarehouseCell({
  row, col,
  displayType,
  baseType,
  shelfId,
  isObstacleMode,
  onClick,
  onHover,
}) {
  const style = CELL_STYLE[displayType] || CELL_STYLE.floor;
  const icon  = CELL_ICONS[displayType];

  const isClickable = baseType === 'floor' || displayType === 'obstacle';

  const cls = [
    'cell',
    displayType === 'robot' ? 'cell-robot' : '',
    displayType === 'path_planned' ? 'cell-planned' : '',
    displayType === 'goal' || displayType === 'target' ? 'cell-goal' : '',
    displayType === 'start' ? 'cell-start' : '',
    displayType === 'obstacle' ? 'cell-obstacle' : '',
    isClickable ? 'clickable' : '',
    isObstacleMode && isClickable ? 'hover:border-red-500 hover:bg-red-950/40' : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={cls}
      style={{
        background:  style.bg,
        borderColor: style.border,
        borderWidth: displayType === 'floor' ? '1px' : '1px',
        borderStyle: 'solid',
      }}
      onClick={() => onClick && onClick(row, col, baseType, displayType)}
      onMouseEnter={() => onHover && onHover(row, col, displayType, shelfId)}
      onMouseLeave={() => onHover && onHover(null, null, null, null)}
      title={
        displayType === 'start'
          ? `[${row}, ${col}] Starting Point (Dock Alpha)`
          : displayType === 'goal'
          ? `[${row}, ${col}] Current Goal Target`
          : displayType === 'obstacle'
          ? `[${row}, ${col}] Obstacle (Click to remove)`
          : shelfId
          ? `Shelf ${shelfId} [${row}, ${col}]`
          : `[${row}, ${col}] ${displayType}`
      }
      role={isClickable ? 'button' : undefined}
      aria-label={
        displayType === 'robot'
          ? `Robot at [${row},${col}]`
          : displayType === 'start'
          ? `Starting Point [${row},${col}]`
          : displayType === 'goal'
          ? `Goal [${row},${col}]`
          : shelfId
          ? `Shelf ${shelfId}`
          : `Cell [${row},${col}]`
      }
    >
      {icon ? (
        <span
          style={{
            fontSize: displayType === 'robot' ? '14px' : displayType === 'goal' || displayType === 'start' ? '13px' : '11px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: '100%',
            userSelect: 'none',
          }}
        >
          {icon}
        </span>
      ) : displayType === 'path_planned' ? (
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: '100%',
            color: '#60a5fa',
            fontSize: '9px',
            lineHeight: 1,
            userSelect: 'none',
          }}
        >
          •
        </span>
      ) : null}
    </div>
  );
});

export default WarehouseCell;
