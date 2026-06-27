"use client";

import { motion } from "framer-motion";
import { LogoMark } from "@/components/brand/logo";

/** Three-dot typing indicator shown before the first token arrives. */
export function TypingBubble() {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <LogoMark size={32} />
      <div className="glass flex items-center gap-1.5 rounded-3xl rounded-tl-lg px-4 py-3.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-2 w-2 rounded-full bg-brand-500"
            animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </motion.div>
  );
}
