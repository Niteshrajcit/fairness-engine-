export default function TypingDots() {
  return (
    <div className="inline-flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300 [animation-delay:-0.25s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300 [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300" />
      <span>System is thinking...</span>
    </div>
  );
}
