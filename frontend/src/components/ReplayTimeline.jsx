import { useState } from "react";

export default function ReplayTimeline({ timeline = [] }) {
  const [selected, setSelected] = useState(0);
  if (!timeline.length) return null;
  const current = timeline[selected];

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-slate-300">Replay Analysis Timeline</div>
      <div className="mb-3 flex flex-wrap gap-2">
        {timeline.map((step, idx) => (
          <button
            key={`${step.timestamp}-${idx}`}
            className={`rounded-md border px-2 py-1 text-xs transition ${
              idx === selected
                ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-100"
                : "border-white/10 bg-white/5 text-slate-300 hover:border-cyan-400/40"
            }`}
            onClick={() => setSelected(idx)}
          >
            {idx + 1}. {step.step}
          </button>
        ))}
      </div>
      <div className="text-xs text-slate-200">{current.message}</div>
      <div className="mt-1 text-[11px] text-slate-400">{new Date(current.timestamp).toLocaleString()}</div>
    </div>
  );
}
