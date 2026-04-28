import { useState } from "react";

export default function WhatIfPanel({ onRun }) {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [pending, setPending] = useState({});

  const addField = () => {
    if (!key.trim()) return;
    setPending((prev) => ({ ...prev, [key.trim()]: value }));
    setKey("");
    setValue("");
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-slate-300">Interactive What-If Simulation</div>
      <div className="flex gap-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="feature"
          className="w-1/2 rounded border border-white/10 bg-black/20 px-2 py-1 text-xs"
        />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="value"
          className="w-1/2 rounded border border-white/10 bg-black/20 px-2 py-1 text-xs"
        />
      </div>
      <div className="mt-2 flex gap-2">
        <button onClick={addField} className="rounded border border-white/10 px-2 py-1 text-xs">
          Add
        </button>
        <button
          onClick={() => onRun(pending)}
          className="rounded border border-cyan-400/50 bg-cyan-500/20 px-2 py-1 text-xs text-cyan-100"
        >
          Run What-If
        </button>
      </div>
      <div className="mt-2 text-[11px] text-slate-400">{JSON.stringify(pending)}</div>
    </div>
  );
}
