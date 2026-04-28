import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function OutcomeChart({ before = [], after = [] }) {
  const merged = before.map((b) => ({
    group: b.group,
    before: b.positive_rate,
    after: after.find((a) => a.group === b.group)?.positive_rate ?? 0,
  }));

  if (!merged.length) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-slate-300">Before vs After Group Positive Outcome (%)</div>
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <BarChart data={merged}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
            <XAxis dataKey="group" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Bar dataKey="before" fill="#a855f7" radius={[4, 4, 0, 0]}>
              <LabelList dataKey="before" position="top" formatter={(v) => `${v}%`} />
            </Bar>
            <Bar dataKey="after" fill="#22d3ee" radius={[4, 4, 0, 0]}>
              <LabelList dataKey="after" position="top" formatter={(v) => `${v}%`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
