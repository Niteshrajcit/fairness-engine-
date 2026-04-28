export default function SessionHistoryPanel({ sessions = [], activeSessionId, onResume }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3 backdrop-blur-md">
      <div className="mb-2 text-sm font-semibold text-slate-100">Session History</div>
      <div className="max-h-48 space-y-2 overflow-y-auto">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onResume(session.id)}
            className={`w-full rounded-lg border p-2 text-left text-xs transition ${
              activeSessionId === session.id
                ? "border-cyan-400/50 bg-cyan-500/10 text-cyan-100"
                : "border-white/10 bg-white/5 text-slate-300 hover:border-cyan-400/40"
            }`}
          >
            <div className="font-medium">{session.dataset_name}</div>
            <div>{session.status}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
