import { motion } from "framer-motion";

export default function StrategyCard({ strategy, onSelect }) {
  return (
    <motion.button
      whileHover={{ scale: 1.01 }}
      onClick={() => onSelect(strategy.name)}
      className="w-full rounded-xl border border-white/10 bg-white/5 p-4 text-left transition hover:border-cyan-400/50 hover:shadow-[0_0_20px_rgba(34,211,238,0.2)]"
    >
      <div className="text-sm font-semibold text-cyan-200">{strategy.name}</div>
      <div className="mt-2 text-xs text-slate-300">
        Accuracy: {strategy.accuracy} | DI: {strategy.di} | Bias Reduction: {strategy.bias_reduction} |
        Accuracy Loss: {strategy.accuracy_loss}
      </div>
    </motion.button>
  );
}
