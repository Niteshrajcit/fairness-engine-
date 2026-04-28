import { motion } from "framer-motion";

export default function MessageBubble({ role, text }) {
  const isSystem = role === "system";
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`max-w-[85%] rounded-2xl border p-3 text-sm shadow-lg ${
        isSystem
          ? "self-start border-cyan-400/30 bg-cyan-500/10 text-cyan-100"
          : "self-end border-purple-400/30 bg-purple-500/10 text-purple-100"
      }`}
    >
      {text}
    </motion.div>
  );
}
