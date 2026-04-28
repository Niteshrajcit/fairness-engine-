export default function RiskScoreCard({ score, level, explanation }) {
  const tone =
    level === "High"
      ? "text-rose-300 border-rose-400/40"
      : level === "Medium"
      ? "text-amber-300 border-amber-400/40"
      : "text-emerald-300 border-emerald-400/40";
  return (
    <div className={`rounded-xl border bg-white/5 p-3 text-xs ${tone}`}>
      <div className="text-sm font-semibold">Bias Risk Score: {score}/100 ({level})</div>
      <div className="mt-1 text-slate-300">{explanation}</div>
    </div>
  );
}
