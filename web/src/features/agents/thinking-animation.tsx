"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import type { ThinkingStep } from "@/lib/types";
import { AGENT_META } from "@/lib/agents-meta";

export function ThinkingAnimation({ steps }: { steps: ThinkingStep[] }) {
  if (steps.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      <AnimatePresence initial={false}>
        {steps.map((step) => {
          const meta = AGENT_META[step.agent];
          return (
            <motion.li
              key={step.id}
              layout
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 text-sm"
            >
              <span className="grid h-5 w-5 shrink-0 place-items-center">
                {step.done ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="grid h-5 w-5 place-items-center rounded-full bg-leaf-500/15"
                  >
                    <Check className="h-3 w-3 text-leaf-600 dark:text-leaf-400" />
                  </motion.span>
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin" style={{ color: meta.accent }} />
                )}
              </span>
              <span className={step.done ? "text-muted-foreground line-through/0" : "text-foreground/90"}>
                {step.label}
              </span>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}
