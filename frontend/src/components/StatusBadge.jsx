export default function StatusBadge({ label, tone = "cyan" }) {
  const toneMap = {
    cyan: "border-cyan-400/40 bg-cyan-500/20 text-cyan-100",
    purple: "border-purple-400/40 bg-purple-500/20 text-purple-100",
    green: "border-emerald-400/40 bg-emerald-500/20 text-emerald-100",
    red: "border-rose-400/40 bg-rose-500/20 text-rose-100",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium shadow-[0_0_20px_rgba(34,211,238,0.2)] ${
        toneMap[tone] || toneMap.cyan
      }`}
    >
      {label}
    </span>
  );
}
