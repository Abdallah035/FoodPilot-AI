"use client";

import { motion } from "framer-motion";
import { ArrowUpLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

/** Related follow-up suggestions shown beneath answers. */
export function PromptSuggestions({
  suggestions = [...t.followUps],
  onPick,
  className,
}: {
  suggestions?: string[];
  onPick: (text: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {suggestions.map((s, i) => (
        <motion.button
          key={s}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          whileHover={{ y: -2 }}
          onClick={() => onPick(s)}
          className="group glass-subtle inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-foreground/80 transition-colors hover:text-brand-600 focus-ring dark:hover:text-brand-300"
        >
          {s}
          <ArrowUpLeft className="h-3.5 w-3.5 opacity-50 transition-transform group-hover:-translate-x-0.5 group-hover:-translate-y-0.5" />
        </motion.button>
      ))}
    </div>
  );
}
