import { useState, useRef, useEffect } from 'react';
import { ScrollText } from 'lucide-react';

const CATEGORY_STYLE = {
  robot:   { dot: 'bg-cyan-500',   text: 'text-cyan-400'  },
  orders:  { dot: 'bg-amber-500',  text: 'text-amber-400' },
  system:  { dot: 'bg-gray-500',   text: 'text-gray-400'  },
  warning: { dot: 'bg-red-500',    text: 'text-red-400'   },
};

const FILTERS = ['All', 'Robot', 'Orders', 'System'];

export default function ActivityLog({ log }) {
  const [filter, setFilter] = useState('All');
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef(null);
  const prevLen = useRef(log?.length ?? 0);

  // Auto-scroll to top when new entries arrive (log is prepended)
  useEffect(() => {
    if (autoScroll && listRef.current && (log?.length ?? 0) > prevLen.current) {
      listRef.current.scrollTop = 0;
    }
    prevLen.current = log?.length ?? 0;
  }, [log, autoScroll]);

  const filterMap = {
    All:    null,
    Robot:  ['robot'],
    Orders: ['orders'],
    System: ['system', 'warning'],
  };
  const allowed  = filterMap[filter];
  const visible  = allowed ? (log || []).filter(e => allowed.includes(e.category)) : (log || []);

  return (
    <div className="panel flex flex-col min-h-0 flex-1">
      {/* Header */}
      <div className="panel-header">
        <ScrollText size={13} className="text-gray-400" />
        <span className="panel-title">Activity Log</span>
        <span className="ml-auto text-[10px] text-wh-muted">{log?.length ?? 0} events</span>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 px-2 pt-1.5 pb-1.5 border-b border-wh-border">
        {FILTERS.map(f => (
          <button
            key={f}
            className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
              filter === f ? 'bg-wh-border text-white' : 'text-wh-muted hover:text-gray-300'
            }`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
        <button
          className={`ml-auto text-[10px] px-1.5 py-0.5 rounded transition-colors ${autoScroll ? 'text-cyan-400' : 'text-wh-muted'}`}
          onClick={() => setAutoScroll(v => !v)}
          title="Toggle auto-scroll"
        >
          {autoScroll ? '⇑ Live' : '⇑ Paused'}
        </button>
      </div>

      {/* Log entries */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-0.5 font-mono"
      >
        {visible.length === 0 ? (
          <div className="text-center text-wh-muted text-[11px] pt-4">No events yet</div>
        ) : (
          visible.map(entry => {
            const cs = CATEGORY_STYLE[entry.category] || CATEGORY_STYLE.system;
            return (
              <div key={entry.id} className="flex gap-1.5 items-start log-entry-new px-1 py-0.5 rounded hover:bg-wh-card transition-colors">
                <span className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${cs.dot}`} />
                <div className="min-w-0 flex-1">
                  <span className="text-[9px] text-wh-muted mr-1">{entry.time}</span>
                  <span className={`text-[10px] ${cs.text}`}>{entry.message}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
